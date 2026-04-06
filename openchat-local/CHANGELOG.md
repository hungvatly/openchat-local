# Changelog

All notable changes to OpenChat Local are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.4.0] - 2026-04-06

### Added
- **Chat History Persistence** — All conversations are now saved to a local SQLite database automatically. Conversations survive app restarts.
- **Conversation Sidebar** — Clock icon in the sidebar opens a panel to browse, resume, and delete past conversations.
- **Conversation Export** — Export any conversation as Markdown (.md) or PDF from the history panel.
- **Document Generation (Word)** — Ask the AI to "create a Word document about..." and it generates a downloadable .docx file with proper formatting (headings, lists, paragraphs).
- **Document Generation (PDF)** — Ask "make a PDF report..." to generate a formatted PDF with auto-layout.
- **Document Generation (Excel)** — Ask "create a spreadsheet..." to generate a .xlsx file with headers, column widths, and styling. Supports markdown tables, CSV, and plain text input.
- **Auto-Detection** — Document generation triggers automatically when the AI detects creation intent in your message (e.g., "create a report", "make a spreadsheet").
- **Download Links** — Generated files appear as clickable download links below the AI's response.
- **Image Understanding** — New "Image" button in the input bar lets you attach photos. Works with Ollama vision models (moondream, llava, llama3.2-vision). Base64 images are sent via the Ollama API.
- **Voice Input** — New microphone button records audio in-browser, sends to server, and transcribes locally using faster-whisper. Transcribed text populates the input box.
- **Whisper Model Selection** — Set `WHISPER_MODEL=tiny|base|small|medium` via environment variable. Default is `tiny` for fastest CPU performance.
- **Voice Auto-Language Detection** — Whisper automatically detects the spoken language (90+ languages supported).
- **New dependencies** — `fpdf2` (PDF generation), `openpyxl` (Excel generation). Optional: `faster-whisper` (voice input).
- **New API endpoints** — `/api/conversations/*`, `/api/generate/*`, `/api/upload/image`, `/api/voice/*`.
- **New files** — `utils/chat_history.py`, `utils/doc_generator.py`, `utils/voice_input.py`.

### Changed
- **Chat endpoint** now accepts `conversation_id` (for history persistence) and `images` (list of base64 strings for vision models).
- **Chat endpoint** now auto-detects document creation requests and returns a `file` object with download URL in the stream response.
- **Ollama client** `stream_chat()` now accepts an optional `images` parameter for multimodal/vision model support.
- **Health endpoint** now reports `voice_available` and `doc_generation` status.
- **Frontend state** now tracks `conversationId`, `pendingImages`, `isRecording`, and `mediaRecorder`.
- **Input bar** now includes Image and Mic buttons alongside the existing Docs and mode selector.
- **Sidebar** now includes a History button (clock icon).

---

## [1.3.0] - 2026-04-06

### Added
- **Watch Folder Auto-Scan Interval** — Changed default scan interval from 10 seconds to 60 minutes (3600 seconds) to reduce CPU usage on low-end hardware.
- **Force Scan Button** — "Scan now" button in the Documents panel triggers an immediate folder scan without waiting for the timer.

### Changed
- **Default `WATCH_INTERVAL`** changed from `10` to `3600` (seconds).
- **Watcher status display** now shows interval in minutes instead of seconds.

---

## [1.2.0] - 2026-04-06

### Added
- **Watch Folder** — Set a local folder to be automatically monitored for new or changed documents. New files are auto-indexed into the RAG pipeline.
- **Persistent Watch State** — The watcher remembers which files it has already indexed (via file hashes stored to disk). No re-processing after app restart.
- **Watch Folder UI** — Documents panel now includes a "Watch folder" section at the top where you can add/remove watched folders and see tracking stats.
- **`WATCH_FOLDER` environment variable** — Set in `.env` to auto-start watching on launch.
- **`WATCH_INTERVAL` environment variable** — Configure scan frequency.
- **New file** — `utils/folder_watcher.py`.
- **New API endpoints** — `/api/watcher/status`, `/api/watcher/add`, `/api/watcher/remove`, `/api/watcher/scan`.

---

## [1.1.0] - 2026-04-06

### Added
- **Web Search** — New "Web Search" chat mode that searches the internet (DuckDuckGo or SearXNG) and feeds page content to the LLM as context.
- **SearXNG Integration** — Optional self-hosted SearXNG support for privacy-focused multi-engine search. Set `SEARXNG_URL` in `.env`.
- **DuckDuckGo Fallback** — Web search works out of the box with zero setup using DuckDuckGo Lite.
- **Three Chat Modes** — Mode selector in input bar: "My Docs" (RAG), "Web Search", "No Context" (plain).
- **Clickable Source Links** — Web search results show as clickable source tags with URLs.
- **Performance Auto-Tuning** — App detects system RAM on startup and auto-selects optimal settings (chunk size, retrieval count, web fetch limits).
- **Three Performance Profiles** — `low` (CPU, ≤20GB RAM), `medium` (mid GPU), `high` (power GPU). Set `PERFORMANCE_PROFILE` in `.env` or let auto-detect.
- **`psutil` dependency** — For system RAM detection.
- **New file** — `utils/web_search.py`.
- **New API endpoints** — `/api/search`, `/api/search/fetch`.

### Changed
- **Chat endpoint** now accepts `mode` parameter instead of `use_rag` boolean.
- **Config** now includes `SEARXNG_URL`, `WEB_SEARCH_ENABLED`, `WEB_SEARCH_MAX_RESULTS`, `WEB_FETCH_MAX_CHARS`, `PERFORMANCE_PROFILE`.
- **Health endpoint** now reports `profile`, `recommended_models`, `web_search_enabled`, `searxng_configured`.

---

## [1.0.0] - 2026-04-06

### Added
- **Initial release** of OpenChat Local.
- **RAG Pipeline** — Chat with local documents using retrieval-augmented generation powered by ChromaDB.
- **Document Support** — `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.xml` file ingestion.
- **YouTube Transcripts** — Extract and index YouTube video transcripts via yt-dlp.
- **Folder Indexing** — Index all supported files in a folder with one click.
- **Streaming Chat** — Real-time token-by-token streaming from Ollama.
- **Multiple Models** — Switch between any Ollama-compatible model via UI dropdown.
- **Dark Theme UI** — Clean, modern dark-themed chat interface.
- **Prompt Cards** — Suggested prompts on the welcome screen with refresh.
- **File Upload** — Upload documents directly via the UI.
- **Docker Support** — Dockerfile and docker-compose.yml for containerized deployment.
- **Cross-Platform** — Windows, macOS, Linux support.
- **Any GPU** — NVIDIA (CUDA), AMD (ROCm), Intel Arc (Vulkan), Apple Silicon (Metal), CPU-only.

### Technical
- **Backend** — FastAPI + Uvicorn.
- **Vector Store** — ChromaDB with cosine similarity.
- **LLM Client** — Async Ollama API client with SSE streaming.
- **Frontend** — Vanilla HTML/CSS/JS, DM Sans typography.
- **Document Parsers** — PyPDF2 (PDF), python-docx (DOCX), csv module, yt-dlp (YouTube).

---

## Bugfixes Applied

### Pydantic Compatibility
- **Issue**: `pydantic-core` fails to build on Python 3.13+ (requires Rust compilation).
- **Fix**: Removed strict version pins from `requirements.txt`. Pip now selects compatible pre-built wheels.

### Jinja2 / Starlette Compatibility
- **Issue**: `TemplateResponse("index.html", {"request": request})` raises `TypeError: cannot use 'tuple' as a dict key` on newer Starlette versions.
- **Fix**: Changed to `TemplateResponse(request, "index.html")`.

### Pydantic Extra Fields
- **Issue**: `WATCH_FOLDER` and `WATCH_INTERVAL` in `.env` cause `ValidationError: Extra inputs are not permitted`.
- **Fix**: Added `extra = "ignore"` to the Pydantic Settings `Config` class.

### System Prompt
- **Issue**: AI responses were too short and overly summarized.
- **Fix**: Rewrote the system prompt to instruct detailed, comprehensive answers instead of concise summaries.
