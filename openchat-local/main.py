"""
OpenChat Local — Main Server
A cross-platform, open-source local RAG chatbot.
"""
import os
import uuid
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings, PROFILE, ACTIVE_PROFILE
from utils.ollama_client import ollama_client
from utils.rag_engine import rag_engine
from utils.document_loader import load_youtube_transcript
from utils.web_search import web_search
from utils.folder_watcher import folder_watcher

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")
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
    mode = body.get("mode", "docs")  # "docs" (RAG), "web", or "plain"
    history = body.get("history", [])

    if not message.strip():
        return JSONResponse({"error": "Empty message"}, status_code=400)

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
        async for token in ollama_client.stream_chat(
            message=message,
            model=model,
            context=context,
            history=history,
        ):
            yield f"data: {json.dumps({'token': token})}\n\n"

        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

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
    """Trigger an immediate scan."""
    result = folder_watcher.scan_and_index()
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
