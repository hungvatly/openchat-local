# OpenChat Local

> An open-source, cross-platform alternative to NVIDIA's Chat with RTX.
> Chat privately with your documents using local LLMs — no cloud, no API keys, no NVIDIA lock-in.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## What Is This?

OpenChat Local lets you chat with your own documents (PDFs, Word docs, text files, CSVs, and more) using AI that runs **entirely on your computer**. No data is sent to the cloud. No subscriptions. No GPU requirements.

Think of it as your own private ChatGPT that knows the contents of your files.

### Why Use This Over Chat with RTX?

| Feature | NVIDIA Chat with RTX | OpenChat Local |
|---------|---------------------|----------------|
| Operating System | Windows only | **Windows, macOS, Linux** |
| GPU Required | NVIDIA RTX 30-series+ (8GB+ VRAM) | **Any GPU or CPU-only** |
| Minimum VRAM | 8 GB | **0 GB (runs on CPU)** |
| Supported File Types | txt, pdf, docx, xml | **txt, pdf, docx, md, csv, xml** |
| YouTube Transcripts | Yes | **Yes** |
| Web Search | No | **Yes (DuckDuckGo + SearXNG)** |
| Watch Folder (auto-index) | No | **Yes** |
| Choose Any Model | Limited selection | **Any Ollama model** |
| Open Source | Partial (reference project) | **Fully open source (MIT)** |
| Install Size | ~40 GB | **~2 GB + model size** |
| Customizable | Limited | **Fully customizable** |

---

## Features

### Core

- **100% Local & Private** — All processing happens on your machine. Your documents never leave your device.
- **Cross-Platform** — Works on Windows, macOS (Intel + Apple Silicon), and Linux.
- **Any Hardware** — Runs on NVIDIA (CUDA), AMD (ROCm), Intel Arc (Vulkan), Apple Silicon (Metal), or CPU-only.
- **Multiple LLM Models** — Switch between any Ollama-compatible model via a dropdown in the UI.
- **Streaming Responses** — See AI responses appear token-by-token in real time.

### Document Intelligence (RAG)

- **Chat With Your Documents** — Ask questions about your PDFs, Word documents, text files, CSVs, and more using retrieval-augmented generation (RAG).
- **Supported Formats** — `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.xml`
- **YouTube Transcripts** — Paste a YouTube URL to extract and index the video's transcript.
- **Folder Indexing** — Point to any folder on your computer to index all supported files at once.
- **Watch Folder** — Set a folder to be automatically monitored. New or changed files are indexed without any manual action.
- **Force Scan** — A "Scan now" button lets you trigger an immediate re-index whenever you want.
- **Persistent Index** — Your document index is saved to disk and survives app restarts. No need to re-add files.

### Web Search

- **Built-in Web Search** — Search the web and feed results to the AI as context. The AI reads the actual page content, not just snippets.
- **No API Key Needed** — Uses DuckDuckGo by default (zero setup required).
- **SearXNG Support** — Optionally connect to a self-hosted SearXNG instance for privacy-focused, multi-engine search (aggregates Google, Bing, Brave, DuckDuckGo, and more).
- **Three Chat Modes** — Switch between "My Docs" (RAG), "Web Search", or "No Context" (plain chat) via a dropdown.

### Performance

- **Auto-Tuning** — Automatically detects your system RAM and adjusts chunk sizes, retrieval limits, and web fetch settings for optimal performance.
- **Three Performance Profiles** — `low` (CPU-only, ≤20GB RAM), `medium` (6-8GB VRAM), `high` (16GB+ VRAM). Set manually or let the app auto-detect.
- **Optimized for Low-End Hardware** — Tested and tuned for systems as modest as an Intel i3-6100 with 20GB DDR4 RAM and no GPU.

---

## Architecture

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│    Browser     │────▶│    FastAPI     │────▶│     Ollama     │
│  (Dark UI)     │◀────│    Server      │◀────│   (LLM Host)   │
└────────────────┘     └───────┬────────┘     └────────────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
              ┌─────▼──┐ ┌────▼───┐ ┌────▼────┐
              │ChromaDB│ │ Web    │ │ Folder  │
              │(Vector │ │ Search │ │ Watcher │
              │  DB)   │ │(DDG /  │ │(Auto-   │
              │        │ │SearXNG)│ │ Index)  │
              └────────┘ └────────┘ └─────────┘
```

---

## Quick Start

### Prerequisites

1. **Python 3.10 - 3.12** (3.12 recommended — [download](https://www.python.org/downloads/))
   > ⚠️ Python 3.13+ may have compatibility issues with some dependencies. Use 3.12 for the smoothest experience.

2. **Ollama** (the LLM engine):
   - **Windows**: Download from [ollama.com/download](https://ollama.com/download)
   - **macOS / Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

3. **Pull a model** (choose based on your hardware):

   ```bash
   # Low-end (i3/i5, no GPU, 8-20GB RAM) — fast, ~1GB download
   ollama pull qwen2.5:1.5b

   # Mid-range (6-8GB VRAM or 16-32GB RAM) — good balance
   ollama pull llama3.1:8b

   # High-end (16GB+ VRAM) — best quality
   ollama pull qwen2.5:14b
   ```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows (PowerShell)

# Install dependencies
pip install -r requirements.txt

# Create your config file
cp .env.example .env
```

### Configuration

Edit `.env` with any text editor and set your preferences:

```env
# Required — must match a model you've pulled in Ollama
DEFAULT_MODEL=qwen2.5:1.5b

# Optional — auto-index files from this folder
WATCH_FOLDER=C:\Users\YourName\Documents
# WATCH_FOLDER=/home/yourname/Documents     # Linux / macOS

# Optional — performance tuning (auto, low, medium, high)
PERFORMANCE_PROFILE=auto
```

### Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser. That's it.

```
  🚀 OpenChat Local v1.0.0
  → http://localhost:8000
  → Ollama: http://localhost:11434
  → Profile: low
  [Watcher] Auto-watching 1 folder(s)
```

---

## Docker Deployment

For a containerized setup with Ollama + SearXNG included:

```bash
# Clone the repository
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

# Start all services
docker compose up -d --build

# The model will be pulled automatically on first start
```

Open **http://localhost:8000**. SearXNG search is available at **http://localhost:8888**.

### Docker Environment Variables

Set these in your shell or in Portainer before deploying:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | `qwen2.5:1.5b` | Model to pull and use |
| `WATCH_FOLDER_HOST` | `./_watch` | Host folder to mount for auto-indexing |
| `PERFORMANCE_PROFILE` | `low` | Performance profile |
| `APP_PORT` | `8000` | Port for the web UI |
| `SEARXNG_PORT` | `8888` | Port for SearXNG |

### GPU Support in Docker

**NVIDIA GPU** — Uncomment the GPU section in `docker-compose.yml` and install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

**AMD GPU** — Uncomment the AMD section in `docker-compose.yml` (requires ROCm drivers).

**Apple Silicon** — Run Ollama natively on macOS for Metal acceleration. Don't use the Ollama Docker container on Mac.

---

## Usage Guide

### Chat Modes

The input bar has a mode selector dropdown with three options:

| Mode | What It Does |
|------|-------------|
| **My Docs** | Searches your indexed documents and provides answers based on their content. Source files are shown as tags below the response. |
| **Web Search** | Searches the web (DuckDuckGo or SearXNG), reads the top results, and uses them as context. Source links are clickable. |
| **No Context** | Plain chat with the LLM — no document or web retrieval. |

### Adding Documents

Click the **Documents** icon in the sidebar to open the document manager:

1. **Watch Folder** (recommended) — Enter a folder path and click "Watch". The app monitors this folder and auto-indexes new or changed files every 60 minutes. Click "Scan now" to trigger an immediate scan.

2. **Upload Files** — Click "Choose Files" to upload individual documents.

3. **Index Folder Once** — Enter a folder path and click "Index" to do a one-time import.

4. **YouTube** — Paste a YouTube URL to extract and index the transcript.

Supported formats: `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.xml`

### Switching Models

Use the model dropdown in the top-right of the input bar. It automatically shows all models you've pulled in Ollama. To add a new model:

```bash
ollama pull mistral:7b
```

Refresh the page and it will appear in the dropdown.

---

## System Requirements

### Minimum (CPU-only)

| Component | Requirement |
|-----------|-------------|
| CPU | Any x86_64 with AVX2 (Intel 4th gen+ / AMD Zen+) |
| RAM | 8 GB (16 GB recommended) |
| GPU | Not required |
| Storage | ~5 GB free (SSD preferred) |
| OS | Windows 10+, macOS 14+, Ubuntu 20.04+ |
| Models | 1.5B - 3B parameter (qwen2.5:1.5b, phi3:mini, llama3.2:3b) |
| Speed | ~5-12 tokens/sec |

### Recommended (GPU)

| Component | Requirement |
|-----------|-------------|
| CPU | 6+ cores |
| RAM | 16 - 32 GB |
| GPU | 6 - 8 GB VRAM (any vendor) |
| Storage | ~20 GB free SSD |
| Models | 7B - 8B parameter (llama3.1:8b, mistral:7b) |
| Speed | ~25-45 tokens/sec |

### Optimal (Power User)

| Component | Requirement |
|-----------|-------------|
| CPU | 8+ cores |
| RAM | 32 - 64 GB |
| GPU | 16 - 24 GB VRAM |
| Storage | ~50 GB+ SSD |
| Models | 14B - 70B parameter (qwen2.5:14b, llama3.1:70b) |
| Speed | ~30-80 tokens/sec |

### Compatible GPUs

| Vendor | Examples | VRAM | Acceleration |
|--------|----------|------|--------------|
| NVIDIA | GTX 1660, RTX 3060, RTX 4060, RTX 4090 | 6-24 GB | CUDA |
| AMD | RX 6700 XT, RX 7800 XT, RX 7900 XTX | 12-24 GB | ROCm |
| Intel | Arc A750, Arc A770 | 8-16 GB | Vulkan |
| Apple | M1, M2, M3, M4 (unified memory) | 8-192 GB | Metal |

---

## Configuration Reference

All settings are configured via the `.env` file or system environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL of the Ollama server |
| `DEFAULT_MODEL` | `llama3.1:8b` | Default LLM model |
| `CHROMA_PERSIST_DIR` | `./data/chromadb` | Where the vector database is stored |
| `UPLOAD_DIR` | `./data/uploads` | Where uploaded files are saved |
| `MAX_FILE_SIZE_MB` | `50` | Maximum file upload size |
| `SEARXNG_URL` | _(empty)_ | SearXNG instance URL (leave empty for DuckDuckGo) |
| `PERFORMANCE_PROFILE` | `auto` | `auto`, `low`, `medium`, or `high` |
| `WATCH_FOLDER` | _(empty)_ | Folder path to auto-monitor for new documents |
| `WATCH_INTERVAL` | `3600` | How often to auto-scan the watch folder (seconds) |

### Performance Profiles

| Profile | Chunk Size | Top-K Results | Best For |
|---------|-----------|---------------|----------|
| `low` | 256 | 3 | CPU-only, ≤20GB RAM, i3/i5 |
| `medium` | 512 | 5 | 6-8GB VRAM, 16-32GB RAM |
| `high` | 768 | 8 | 16GB+ VRAM, 32GB+ RAM |

---

## Project Structure

```
openchat-local/
├── main.py                   # FastAPI server, API routes, startup logic
├── config.py                 # Settings, performance profiles, auto-detection
├── requirements.txt          # Python dependencies (no strict version pins)
├── .env.example              # Environment configuration template
├── Dockerfile                # Container build for the app
├── docker-compose.yml        # Full stack: Ollama + App + SearXNG
├── setup.bat                 # One-click Docker setup (Windows)
├── setup.sh                  # One-click Docker setup (Linux/macOS)
├── LICENSE                   # MIT License
│
├── utils/
│   ├── ollama_client.py      # Async Ollama API client with streaming
│   ├── rag_engine.py         # ChromaDB vector store & RAG pipeline
│   ├── document_loader.py    # File parsers (PDF, DOCX, TXT, CSV, XML, YouTube)
│   ├── web_search.py         # Web search (DuckDuckGo + SearXNG)
│   └── folder_watcher.py     # Background folder monitor & auto-indexer
│
├── templates/
│   └── index.html            # Main HTML template (dark-themed UI)
│
└── static/
    ├── css/style.css          # Dark theme stylesheet
    └── js/app.js              # Frontend logic (chat, uploads, watcher)
```

---

## API Reference

The app exposes a REST API at `http://localhost:8000/api/`. Useful if you want to build your own frontend or integrate with other tools.

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System status, Ollama connection, RAG stats, profile info |
| `GET` | `/api/models` | List all available Ollama models |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message and stream the response (SSE) |

**Request body:**
```json
{
  "message": "What does my report say about Q3 revenue?",
  "model": "qwen2.5:1.5b",
  "mode": "docs",
  "history": []
}
```

`mode` options: `"docs"` (RAG), `"web"` (web search), `"plain"` (no context)

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload and index a file (multipart form) |
| `POST` | `/api/documents/folder` | Index all files in a folder path |
| `POST` | `/api/documents/youtube` | Extract and index a YouTube transcript |
| `GET` | `/api/documents/stats` | Number of indexed chunks |
| `POST` | `/api/documents/clear` | Delete all indexed documents |

### Web Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Search the web and return results |
| `POST` | `/api/search/fetch` | Fetch and extract text from a URL |

### Folder Watcher

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watcher/status` | Current watcher state and stats |
| `POST` | `/api/watcher/add` | Add a folder to the watch list |
| `POST` | `/api/watcher/remove` | Remove a folder from the watch list |
| `POST` | `/api/watcher/scan` | Trigger an immediate scan |

---

## Troubleshooting

### "Cannot connect to Ollama"

Make sure Ollama is running:
```bash
ollama list    # Should show your pulled models
```
If it's not running, start it:
- **Windows**: Ollama runs as a system tray app. Check if it's in the tray.
- **Linux**: `ollama serve`
- **macOS**: Open the Ollama app.

### "pydantic-core" Rust compilation error during pip install

You're likely on Python 3.13+. Either:
- Install **Python 3.12** instead (recommended), or
- Run `pip install` without the requirements file: `pip install fastapi uvicorn[standard] python-multipart jinja2 aiohttp chromadb sentence-transformers pypdf2 python-docx beautifulsoup4 yt-dlp pydantic pydantic-settings aiofiles psutil`

### "Extra inputs are not permitted" (WATCH_FOLDER / WATCH_INTERVAL)

Your `.env` file has variables that Pydantic doesn't recognize. Make sure you're using the latest `config.py` which includes `extra = "ignore"` in the Config class.

### Slow responses on CPU

This is expected on CPU-only systems. Tips to improve speed:
- Use a smaller model: `ollama pull qwen2.5:1.5b` (~8-12 tok/s on CPU)
- Set `PERFORMANCE_PROFILE=low` in your `.env`
- Close other memory-heavy applications

### Web search not returning results

DuckDuckGo Lite may occasionally rate-limit or block requests. For more reliable search, set up SearXNG:
```bash
docker run -d -p 8888:8080 searxng/searxng:latest
```
Then add `SEARXNG_URL=http://localhost:8888` to your `.env`.

---

## Roadmap

- [ ] Chat history persistence (SQLite)
- [ ] Conversation export (Markdown / PDF)
- [ ] Image understanding via multimodal models
- [ ] Voice input (whisper.cpp)
- [ ] Plugin system for custom tools
- [ ] Electron / Tauri desktop app wrapper
- [ ] Mobile-responsive UI improvements

---

## Contributing

Contributions are welcome! Here's how:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please open an issue first if you want to discuss a major change.

---

## Acknowledgments

Built with these open-source projects:

- [Ollama](https://ollama.com/) — Local LLM inference engine
- [FastAPI](https://fastapi.tiangolo.com/) — Python web framework
- [ChromaDB](https://www.trychroma.com/) — Vector database for RAG
- [SearXNG](https://github.com/searxng/searxng) — Privacy-focused metasearch engine
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube transcript extraction

---

## License

MIT License — use it however you want. See [LICENSE](LICENSE) for details.
