# OpenChat Local

> An open-source, cross-platform alternative to NVIDIA's Chat with RTX.
> Chat privately with your documents, search the web, understand images, dictate with your voice, and generate Word/PDF/Excel files — all running locally on your machine.

---

## What Is This?

OpenChat Local is a fully local AI chatbot that can:

- **Chat with your documents** — Ask questions about your PDFs, Word docs, text files, and more
- **Search the web** — Fetch live information from the internet and use it as context
- **Understand images** — Attach photos and ask questions about them using vision models
- **Listen to your voice** — Dictate messages using local Whisper speech-to-text
- **Generate documents** — Create Word (.docx), PDF, and Excel (.xlsx) files from chat
- **Auto-index folders** — Watch a folder and automatically index new files
- **Remember conversations** — Full chat history with search, resume, and export

Everything runs on your computer. No cloud. No API keys. No subscriptions.

---

## Features

### Core Chat
- **100% Local & Private** — All processing on your machine. Documents never leave your device.
- **Cross-Platform** — Windows, macOS (Intel + Apple Silicon), Linux.
- **Any Hardware** — NVIDIA (CUDA), AMD (ROCm), Intel Arc (Vulkan), Apple Silicon (Metal), or CPU-only.
- **Multiple LLM Models** — Switch between any Ollama model via dropdown.
- **Streaming Responses** — Token-by-token real-time output.

### Document Intelligence (RAG)
- **Chat With Your Documents** — RAG pipeline with ChromaDB vector store.
- **Supported Formats** — `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.xml`
- **YouTube Transcripts** — Paste a URL to index video transcripts.
- **Folder Indexing** — Index an entire folder in one click.
- **Watch Folder** — Automatically monitor a folder for new/changed files. Configurable scan interval (default: 60 min) with a manual "Scan now" button.
- **Persistent Index** — Document index survives app restarts.

### Web Search
- **Built-in Web Search** — Fetches and reads actual page content, not just snippets.
- **Zero Setup** — Uses DuckDuckGo by default (no API key).
- **SearXNG Support** — Connect a self-hosted SearXNG instance for multi-engine privacy search.
- **Three Chat Modes** — "My Docs" (RAG), "Web Search", or "No Context" (plain chat).

### Image Understanding (Vision)
- **Attach Images in Chat** — Upload a photo and ask questions about it.
- **Vision Models** — Works with moondream (1.8B, great for CPU), llava (7B), llama3.2-vision (11B).
- **Uses Ollama API** — No extra dependencies. Just pull a vision model.

### Voice Input
- **Microphone Button** — Click to record, click again to stop. Transcribed text appears in the input box.
- **Local Whisper** — Uses faster-whisper for CPU-optimized transcription.
- **Auto Language Detection** — Works with English, Vietnamese, Chinese, and 90+ other languages.
- **Multiple Model Sizes** — `tiny` (fastest, default), `base`, `small`, `medium` for better accuracy.

### Document Generation
- **Word Documents** — Ask "create a Word document about..." and get a downloadable .docx.
- **PDF Files** — "Make a PDF report..." generates a formatted PDF.
- **Excel Spreadsheets** — "Create a spreadsheet with..." generates a .xlsx with headers and formatting.
- **Auto-Detection** — The AI detects document creation intent from your message.
- **Download Links** — Files appear as download links below the AI's response.

### Chat History
- **Persistent Storage** — All conversations saved to SQLite automatically.
- **Sidebar History** — Browse and resume past conversations.
- **Export** — Download any conversation as Markdown (.md) or PDF.
- **Delete** — Remove individual conversations.

### Performance
- **Auto-Tuning** — Detects system RAM and adjusts settings automatically.
- **Three Profiles** — `low` (CPU-only), `medium` (mid GPU), `high` (power GPU).
- **Tested on Low-End Hardware** — Works on Intel i3-6100 with 20GB DDR4, no GPU.

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
| Models | 1.5B - 3B (qwen2.5:1.5b, phi3:mini, llama3.2:3b) |
| Speed | ~5-12 tokens/sec |

### Recommended (GPU)

| Component | Requirement |
|-----------|-------------|
| RAM | 16 - 32 GB |
| GPU | 6 - 8 GB VRAM (any vendor) |
| Models | 7B - 8B (llama3.1:8b, mistral:7b) |
| Speed | ~25-45 tokens/sec |

### Optimal (Power User)

| Component | Requirement |
|-----------|-------------|
| RAM | 32 - 64 GB |
| GPU | 16 - 24 GB VRAM |
| Models | 14B - 70B (qwen2.5:14b, llama3.1:70b) |
| Speed | ~30-80 tokens/sec |

### Compatible GPUs

| Vendor | Examples | VRAM | Acceleration |
|--------|----------|------|--------------|
| NVIDIA | GTX 1660, RTX 3060, RTX 4090 | 6-24 GB | CUDA |
| AMD | RX 6700 XT, RX 7900 XTX | 12-24 GB | ROCm |
| Intel | Arc A750, Arc A770 | 8-16 GB | Vulkan |
| Apple | M1, M2, M3, M4 | 8-192 GB | Metal |

---

## Architecture

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│    Browser     │────▶│    FastAPI     │────▶│     Ollama     │
│  (Dark UI)     │◀────│    Server      │◀────│   (LLM Host)   │
└────────────────┘     └───────┬────────┘     └────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼──┐      ┌─────▼──┐      ┌──────▼─────┐
        │ChromaDB│      │ SQLite │      │  Whisper   │
        │(Docs)  │      │(Chats) │      │ (Voice)    │
        └────────┘      └────────┘      └────────────┘
              │                │                │
        ┌─────▼──┐      ┌─────▼──┐      ┌──────▼─────┐
        │ Web    │      │  Doc   │      │  Folder    │
        │ Search │      │  Gen   │      │  Watcher   │
        └────────┘      └────────┘      └────────────┘
```

---

## Quick Start

### Prerequisites

1. **Python 3.10-3.12** ([download](https://www.python.org/downloads/))
   > Python 3.13+ may have issues with some dependencies. Use 3.12 for the smoothest experience.

2. **Ollama** (the LLM engine):
   - **Windows**: [ollama.com/download](https://ollama.com/download)
   - **macOS / Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

3. **Pull a model** (choose based on your hardware):
   ```bash
   # Low-end (i3/i5, no GPU, 8-20GB RAM)
   ollama pull qwen2.5:1.5b

   # Mid-range (6-8GB VRAM, 16-32GB RAM)
   ollama pull llama3.1:8b

   # High-end (16GB+ VRAM)
   ollama pull qwen2.5:14b
   ```

4. **Optional** for extra features:
   ```bash
   # Image understanding
   ollama pull moondream        # 1.8B, best for CPU

   # Voice input
   pip install faster-whisper
   ```

### Installation

```bash
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows (PowerShell)

pip install -r requirements.txt
cp .env.example .env
```

### Configuration

Edit `.env`:
```env
DEFAULT_MODEL=qwen2.5:1.5b
WATCH_FOLDER=C:\Users\YourName\Documents
PERFORMANCE_PROFILE=auto
```

### Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

---

## Docker Deployment

```bash
git clone https://github.com/your-username/openchat-local.git
cd openchat-local
docker compose up -d --build
```

Open **http://localhost:8000**. SearXNG at **http://localhost:8888**.

### Docker Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | `qwen2.5:1.5b` | Model to use |
| `WATCH_FOLDER_HOST` | `./_watch` | Host folder for auto-indexing |
| `PERFORMANCE_PROFILE` | `low` | Performance profile |
| `APP_PORT` | `8000` | Web UI port |

---

## Usage Guide

### Chat Modes

| Mode | Description |
|------|-------------|
| **My Docs** | Searches your indexed documents for context |
| **Web Search** | Searches the web and reads top results |
| **No Context** | Plain LLM chat without retrieval |

### Adding Documents
Click **Documents** icon in sidebar. Options: Watch Folder (auto-monitors), Upload Files, Index Folder (one-time), YouTube URL.

### Image Understanding
Click **Image** button, attach photo, type question, send. Use a vision model (moondream, llava).

### Voice Input
Click **mic** button to record, click again to stop. Text appears in input box. Requires `pip install faster-whisper`.

### Document Generation
Ask naturally: *"Create a Word document about..."*, *"Make a PDF report..."*, *"Create a spreadsheet..."*. Download link appears below response.

### Chat History
Click **clock** icon in sidebar. Browse, resume, export (Markdown/PDF), or delete past conversations.

---

## System Requirements

| Tier | RAM | GPU | Models | Speed |
|------|-----|-----|--------|-------|
| Minimum | 8 GB | None (CPU) | 1.5B-3B | ~5-12 tok/s |
| Recommended | 16-32 GB | 6-8 GB VRAM | 7B-8B | ~25-45 tok/s |
| Optimal | 32-64 GB | 16-24 GB VRAM | 14B-70B | ~30-80 tok/s |

**Compatible GPUs:** NVIDIA (GTX 10-series+), AMD (RX 5000+), Intel Arc, Apple Silicon (M1+)

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `DEFAULT_MODEL` | `llama3.1:8b` | Default LLM model |
| `CHROMA_PERSIST_DIR` | `./data/chromadb` | Vector DB storage |
| `SEARXNG_URL` | _(empty)_ | SearXNG URL (empty = DuckDuckGo) |
| `PERFORMANCE_PROFILE` | `auto` | `auto`, `low`, `medium`, `high` |
| `WATCH_FOLDER` | _(empty)_ | Folder to auto-monitor |
| `WATCH_INTERVAL` | `3600` | Auto-scan interval (seconds) |
| `WHISPER_MODEL` | `tiny` | Whisper model size |

---

## API Reference

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Status, features, profile |
| `GET` | `/api/models` | Available Ollama models |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send message (supports `mode`, `images`, `conversation_id`) |

### Chat History
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation + messages |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `GET` | `/api/conversations/{id}/export?format=md\|pdf` | Export conversation |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload and index file |
| `POST` | `/api/documents/folder` | Index folder |
| `POST` | `/api/documents/youtube` | Index YouTube transcript |
| `GET` | `/api/documents/stats` | Index stats |
| `POST` | `/api/documents/clear` | Clear all documents |

### Web Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Search the web |
| `POST` | `/api/search/fetch` | Fetch URL content |

### Folder Watcher
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watcher/status` | Watcher status |
| `POST` | `/api/watcher/add` | Add watch folder |
| `POST` | `/api/watcher/remove` | Remove watch folder |
| `POST` | `/api/watcher/scan` | Force immediate scan |

### Document Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/docx` | Generate Word document |
| `POST` | `/api/generate/pdf` | Generate PDF |
| `POST` | `/api/generate/xlsx` | Generate Excel file |

### Image & Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/image` | Upload image for vision |
| `POST` | `/api/voice/transcribe` | Transcribe audio |
| `GET` | `/api/voice/status` | Whisper availability |

---

## Project Structure

```
openchat-local/
├── main.py                   # FastAPI server, all API routes
├── config.py                 # Settings, profiles, auto-detection
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── Dockerfile                # Container build
├── docker-compose.yml        # Full stack deployment
├── setup.bat / setup.sh      # One-click setup scripts
├── LICENSE
│
├── utils/
│   ├── ollama_client.py      # Ollama API (streaming, vision)
│   ├── rag_engine.py         # ChromaDB RAG pipeline
│   ├── document_loader.py    # File parsers (PDF, DOCX, TXT, YouTube)
│   ├── web_search.py         # Web search (DuckDuckGo + SearXNG)
│   ├── folder_watcher.py     # Background folder monitor
│   ├── chat_history.py       # SQLite conversation persistence
│   ├── doc_generator.py      # Word, PDF, Excel generation
│   └── voice_input.py        # Whisper speech-to-text
│
├── templates/
│   └── index.html            # Main UI template
└── static/
    ├── css/style.css          # Dark theme
    └── js/app.js              # Frontend logic
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Ollama" | Run `ollama list` to check. Windows: check system tray. Linux: `ollama serve` |
| Rust compilation error on pip install | Use Python 3.12, not 3.13+ |
| "Extra inputs are not permitted" | Update `config.py` (needs `extra = "ignore"`) |
| Slow responses | Use smaller model (`qwen2.5:1.5b`), set `PERFORMANCE_PROFILE=low` |
| Voice button does nothing | `pip install faster-whisper`, allow mic permission in browser |
| Images not understood | Pull a vision model: `ollama pull moondream` |
| Web search empty results | Set up SearXNG: `docker run -d -p 8888:8080 searxng/searxng:latest` |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## Acknowledgments

- [Ollama](https://ollama.com/) — Local LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [SearXNG](https://github.com/searxng/searxng) — Privacy metasearch
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Speech-to-text
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube transcripts

---

## License

MIT License — see [LICENSE](LICENSE).

## 🚀 Made by Hung Nguyen 🚀
