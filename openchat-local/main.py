"""
OpenChat Local — Main Server
A cross-platform, open-source local RAG chatbot.
"""
import os
import uuid
import json
import base64
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings, PROFILE, ACTIVE_PROFILE
from utils.ollama_client import ollama_client
from utils.rag_engine import rag_engine
from utils.document_loader import load_youtube_transcript
from utils.web_search import web_search
from utils.folder_watcher import folder_watcher
from utils.chat_history import chat_history
from utils.doc_generator import detect_and_generate, generate_docx, generate_pdf, generate_xlsx
from utils.voice_input import transcribe_audio, is_available as whisper_available
from utils.template_engine import (
    save_template, list_templates, get_template, delete_template,
    build_fill_prompt, generate_from_template
)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("data/generated", exist_ok=True)
app.mount("/files", StaticFiles(directory="data/generated"), name="files")
templates = Jinja2Templates(directory="templates")


# ── Pages ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# ── API: System ────────────────────────────────────────

@app.get("/api/health")
async def health():
    ollama_ok = await ollama_client.check_health()
    rag_stats = rag_engine.get_stats()
    return {
        "status": "ok",
        "ollama_connected": ollama_ok,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "rag": rag_stats,
        "profile": PROFILE,
        "recommended_models": ACTIVE_PROFILE["recommended_models"],
        "web_search_enabled": settings.WEB_SEARCH_ENABLED,
        "searxng_configured": bool(settings.SEARXNG_URL),
        "voice_available": whisper_available(),
        "doc_generation": True,
    }


@app.get("/api/models")
async def list_models():
    models = await ollama_client.list_models()
    return {"models": models, "default": settings.DEFAULT_MODEL}


# ── API: Chat ──────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    model = body.get("model", None)
    mode = body.get("mode", "docs")
    history = body.get("history", [])
    conv_id = body.get("conversation_id", None)
    images_b64 = body.get("images", [])  # list of base64 image strings
    persona_id = body.get("persona_id", "default")

    if not message.strip():
        return JSONResponse({"error": "Empty message"}, status_code=400)

    # Resolve persona system prompt
    system_prompt = None
    persona = chat_history.get_persona(persona_id)
    if persona:
        system_prompt = persona["prompt"]

    # Create or reuse conversation
    if not conv_id:
        conv_id = uuid.uuid4().hex[:12]
        chat_history.create_conversation(conv_id, model=model or settings.DEFAULT_MODEL, persona_id=persona_id)

    # Save user message
    chat_history.add_message(conv_id, "user", message, images=",".join(images_b64[:1]) if images_b64 else "")

    context = ""
    sources = []

    if mode == "docs":
        retrieved = rag_engine.query(message)
        if retrieved:
            context = rag_engine.build_context(message)
            sources = [{"source": r["source"], "score": r["score"], "type": "document"} for r in retrieved]

    elif mode == "web" and settings.WEB_SEARCH_ENABLED:
        search_results = await web_search.search(message, settings.WEB_SEARCH_MAX_RESULTS)
        if search_results:
            web_context_parts = []
            for r in search_results[:3]:
                page_text = await web_search.fetch_page(r["url"], settings.WEB_FETCH_MAX_CHARS)
                if page_text:
                    web_context_parts.append(f"[Source: {r['title']}]\nURL: {r['url']}\n{page_text[:1500]}")
                else:
                    web_context_parts.append(f"[Source: {r['title']}]\nURL: {r['url']}\n{r['snippet']}")
                sources.append({"source": r["title"], "url": r["url"], "type": "web"})
            context = "\n\n---\n\n".join(web_context_parts)

    async def generate():
        full_text = ""
        async for token in ollama_client.stream_chat(
            message=message,
            model=model,
            context=context,
            history=history,
            images=images_b64 if images_b64 else None,
            system_prompt=system_prompt,
        ):
            full_text += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save AI response
        chat_history.add_message(conv_id, "assistant", full_text, sources=sources)

        # Auto-generate title for new conversations
        if len(history) == 0:
            title = message[:50].strip()
            chat_history.update_title(conv_id, title)

        # Check if user asked to create a document
        doc_result = detect_and_generate(full_text, message)
        file_info = None
        if doc_result and doc_result.get("status") == "ok":
            file_info = {
                "filename": doc_result["filename"],
                "url": f"/files/{doc_result['filename']}",
                "type": doc_result["type"],
            }

        yield f"data: {json.dumps({'done': True, 'sources': sources, 'conversation_id': conv_id, 'file': file_info})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── API: Web Search ────────────────────────────────────

@app.post("/api/search")
async def search_web(request: Request):
    body = await request.json()
    query = body.get("query", "")
    if not query.strip():
        return JSONResponse({"error": "Empty query"}, status_code=400)

    results = await web_search.search(query, settings.WEB_SEARCH_MAX_RESULTS)
    return {"results": results, "query": query}


@app.post("/api/search/fetch")
async def fetch_url(request: Request):
    body = await request.json()
    url = body.get("url", "")
    if not url.startswith("http"):
        return JSONResponse({"error": "Invalid URL"}, status_code=400)

    text = await web_search.fetch_page(url, settings.WEB_FETCH_MAX_CHARS)
    if text:
        return {"text": text, "url": url}
    return JSONResponse({"error": "Could not fetch page"}, status_code=400)


# ── API: Documents ─────────────────────────────────────

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".txt", ".pdf", ".docx", ".md", ".csv", ".xml"}
    if ext not in allowed:
        return JSONResponse(
            {"error": f"Unsupported file type: {ext}. Supported: {', '.join(allowed)}"},
            status_code=400,
        )

    filepath = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        return JSONResponse({"error": f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB"}, status_code=400)

    with open(filepath, "wb") as f:
        f.write(content)

    result = rag_engine.ingest_file(filepath)
    return result


@app.post("/api/documents/folder")
async def ingest_folder(request: Request):
    body = await request.json()
    folder = body.get("folder_path", "")
    if not os.path.isdir(folder):
        return JSONResponse({"error": "Invalid folder path"}, status_code=400)

    results = rag_engine.ingest_folder(folder)
    return {"status": "ok", "files_processed": len(results), "details": results}


@app.post("/api/documents/youtube")
async def ingest_youtube(request: Request):
    body = await request.json()
    url = body.get("url", "")
    if "youtube.com" not in url and "youtu.be" not in url:
        return JSONResponse({"error": "Not a valid YouTube URL"}, status_code=400)

    transcript = load_youtube_transcript(url)
    if not transcript:
        return JSONResponse({"error": "Could not extract transcript"}, status_code=400)

    result = rag_engine.ingest_text(transcript, source_name=f"youtube:{url}")
    return result


@app.get("/api/documents/stats")
async def document_stats():
    return rag_engine.get_stats()


@app.post("/api/documents/clear")
async def clear_documents():
    return rag_engine.clear()


# ── API: Folder Watcher ────────────────────────────────

@app.get("/api/watcher/status")
async def watcher_status():
    return folder_watcher.get_status()


@app.post("/api/watcher/add")
async def watcher_add(request: Request):
    body = await request.json()
    folder = body.get("folder", "")
    if not folder:
        return JSONResponse({"error": "No folder specified"}, status_code=400)
    return folder_watcher.add_folder(folder)


@app.post("/api/watcher/remove")
async def watcher_remove(request: Request):
    body = await request.json()
    folder = body.get("folder", "")
    return folder_watcher.remove_folder(folder)


@app.post("/api/watcher/scan")
async def watcher_scan_now():
    result = folder_watcher.scan_and_index()
    return result


# ── API: Chat History ─────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(folder: str = None, tag: str = None):
    convs = chat_history.list_conversations(limit=50, folder=folder, tag=tag)
    return {"conversations": convs}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = chat_history.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return conv


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    chat_history.delete_conversation(conv_id)
    return {"status": "ok"}


@app.patch("/api/conversations/{conv_id}")
async def rename_conversation(conv_id: str, request: Request):
    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        return JSONResponse({"error": "Empty title"}, status_code=400)
    chat_history.update_title(conv_id, title)
    return {"status": "ok", "title": title}


@app.get("/api/conversations/{conv_id}/export")
async def export_conversation(conv_id: str, format: str = "md"):
    if format == "md":
        md = chat_history.export_markdown(conv_id)
        if not md:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"markdown": md, "conversation_id": conv_id})
    elif format == "pdf":
        md = chat_history.export_markdown(conv_id)
        if not md:
            return JSONResponse({"error": "Not found"}, status_code=404)
        conv = chat_history.get_conversation(conv_id)
        result = generate_pdf(conv["title"], md)
        if result.get("status") == "ok":
            return FileResponse(result["path"], filename=result["filename"], media_type="application/pdf")
        return JSONResponse(result, status_code=500)
    return JSONResponse({"error": "Unsupported format. Use 'md' or 'pdf'"}, status_code=400)


# ── API: Search ───────────────────────────────────────

@app.get("/api/conversations/search/{query}")
async def search_conversations(query: str):
    results = chat_history.search(query)
    return {"results": results, "query": query}


# ── API: Conversation Metadata ────────────────────────

@app.patch("/api/conversations/{conv_id}/meta")
async def update_conversation_meta(conv_id: str, request: Request):
    """Update folder, tags, or persona for a conversation."""
    body = await request.json()
    chat_history.update_conversation(conv_id, **body)
    return {"status": "ok"}


@app.get("/api/folders")
async def list_folders():
    return {"folders": chat_history.get_folders()}


@app.get("/api/tags")
async def list_tags():
    return {"tags": chat_history.get_all_tags()}


# ── API: Personas ─────────────────────────────────────

@app.get("/api/personas")
async def api_list_personas():
    return {"personas": chat_history.list_personas()}


@app.get("/api/personas/{persona_id}")
async def api_get_persona(persona_id: str):
    p = chat_history.get_persona(persona_id)
    if not p:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return p


@app.post("/api/personas")
async def api_save_persona(request: Request):
    body = await request.json()
    pid = body.get("id", uuid.uuid4().hex[:8])
    name = body.get("name", "").strip()
    prompt = body.get("prompt", "").strip()
    if not name or not prompt:
        return JSONResponse({"error": "Name and prompt required"}, status_code=400)
    result = chat_history.save_persona(pid, name, prompt)
    return {"status": "ok", **result}


@app.delete("/api/personas/{persona_id}")
async def api_delete_persona(persona_id: str):
    chat_history.delete_persona(persona_id)
    return {"status": "ok"}


# ── API: Document Generation ──────────────────────────

@app.post("/api/generate/docx")
async def gen_docx(request: Request):
    body = await request.json()
    result = generate_docx(body.get("title", "Document"), body.get("content", ""))
    if result.get("status") == "ok":
        result["url"] = f"/files/{result['filename']}"
    return result


@app.post("/api/generate/pdf")
async def gen_pdf(request: Request):
    body = await request.json()
    result = generate_pdf(body.get("title", "Document"), body.get("content", ""))
    if result.get("status") == "ok":
        result["url"] = f"/files/{result['filename']}"
    return result


@app.post("/api/generate/xlsx")
async def gen_xlsx(request: Request):
    body = await request.json()
    result = generate_xlsx(body.get("title", "Spreadsheet"), body.get("content", ""))
    if result.get("status") == "ok":
        result["url"] = f"/files/{result['filename']}"
    return result


# ── API: Image Upload (for vision models) ─────────────

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        return JSONResponse({"error": f"Unsupported image type: {ext}"}, status_code=400)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return JSONResponse({"error": "Image too large. Max 10MB"}, status_code=400)

    b64 = base64.b64encode(content).decode("utf-8")
    return {"status": "ok", "base64": b64, "filename": file.filename, "size": len(content)}


# ── API: Voice Input ──────────────────────────────────

@app.post("/api/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        return JSONResponse({"error": "Audio too large. Max 25MB"}, status_code=400)

    result = transcribe_audio(content, file.filename)
    return result


@app.get("/api/voice/status")
async def voice_status():
    return {"available": whisper_available()}


# ── API: Templates ────────────────────────────────────

@app.post("/api/templates/upload")
async def upload_template(file: UploadFile = File(...)):
    """Upload a form/template document for reuse."""
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".txt", ".pdf", ".docx", ".md"}
    if ext not in allowed:
        return JSONResponse(
            {"error": f"Unsupported template type: {ext}. Use: {', '.join(allowed)}"},
            status_code=400,
        )

    # Save to temp then register as template
    tmp_path = os.path.join(settings.UPLOAD_DIR, f"tmp_{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    result = save_template(tmp_path, file.filename)
    os.remove(tmp_path)

    return {
        "status": "ok",
        "template_id": result["id"],
        "name": result["name"],
        "fields": len(result.get("structure", {}).get("fields", [])),
        "structure": result.get("structure", {}),
    }


@app.get("/api/templates")
async def api_list_templates():
    return {"templates": list_templates()}


@app.get("/api/templates/{template_id}")
async def api_get_template(template_id: str):
    t = get_template(template_id)
    if not t:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    return t


@app.delete("/api/templates/{template_id}")
async def api_delete_template(template_id: str):
    delete_template(template_id)
    return {"status": "ok"}


@app.post("/api/templates/{template_id}/fill")
async def fill_template(template_id: str, request: Request):
    """Fill a template with AI using user instructions.
    The AI generates content matching the template structure,
    then a document is created from that content.
    """
    body = await request.json()
    instructions = body.get("instructions", "")
    model = body.get("model", None)
    output_format = body.get("output_format", None)  # ".docx", ".pdf", or None (auto)

    if not instructions.strip():
        return JSONResponse({"error": "No instructions provided"}, status_code=400)

    template = get_template(template_id)
    if not template:
        return JSONResponse({"error": "Template not found"}, status_code=404)

    # Build the prompt
    fill_prompt = build_fill_prompt(template, instructions)

    # Get AI to fill the template
    full_response = ""
    async for token in ollama_client.stream_chat(
        message=fill_prompt,
        model=model,
        context="",
        history=[],
    ):
        full_response += token

    # Generate the document
    result = generate_from_template(template_id, full_response, output_format)
    if result.get("status") == "ok":
        result["url"] = f"/files/{result['filename']}"

    return result


# ── Startup ────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    """Auto-start the folder watcher if watch dirs are configured."""
    if folder_watcher.watch_dirs:
        folder_watcher.start()
        print(f"  [Watcher] Auto-watching {len(folder_watcher.watch_dirs)} folder(s)")
    else:
        print("  [Watcher] No watch folders configured. Set WATCH_FOLDER in .env or add via UI.")


# ── Run ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"\n  🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  → http://localhost:{settings.PORT}")
    print(f"  → Ollama: {settings.OLLAMA_BASE_URL}")
    print(f"  → Profile: {PROFILE}\n")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
