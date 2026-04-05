# OpenChat Local

An open-source, cross-platform alternative to NVIDIA's Chat with RTX. Chat privately with your documents using local LLMs — no cloud, no NVIDIA lock-in.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## Features

- **Cross-platform** — Works on Windows, macOS (Intel + Apple Silicon), and Linux
- **Any GPU** — NVIDIA (CUDA), AMD (ROCm), Intel Arc (Vulkan), Apple Silicon (Metal), or CPU-only
- **Local & Private** — Everything runs on your machine. No data leaves your device
- **RAG Pipeline** — Chat with your documents using retrieval-augmented generation
- **Multiple Formats** — Supports .txt, .pdf, .docx, .md, .csv, .xml files
- **YouTube Transcripts** — Add YouTube videos to your knowledge base
- **Folder Indexing** — Point to a folder and index everything at once
- **Streaming Responses** — Real-time token-by-token streaming
- **Multiple Models** — Switch between any Ollama-compatible model
- **Beautiful UI** — Clean, dark-themed chat interface

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Browser    │───▶│   FastAPI    │───▶│    Ollama    │
│   (Dark UI)  │◀───│   Server     │◀───│  (LLM host)  │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                    ┌──────▼───────┐
                    │   ChromaDB   │
                    │ (Vector DB)  │
                    └──────────────┘
```

## Quick Start

### Prerequisites

1. **Install Ollama** (the LLM engine):
   - macOS / Linux: `curl -fsSL https://ollama.com/install.sh | sh`
   - Windows: Download from [ollama.com](https://ollama.com/download)

2. **Pull a model:**
   ```bash
   ollama pull llama3.1:8b     # Recommended (needs ~5GB VRAM)
   # OR for low-end hardware:
   ollama pull phi3:mini        # Smaller, runs on 4GB VRAM / CPU
   # OR for best quality:
   ollama pull qwen2.5:14b     # Needs ~10GB VRAM
   ```

3. **Python 3.10+** installed on your system

### Option A: Run Directly

```bash
# Clone the repo
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start the server
python main.py
```

Open **http://localhost:8000** in your browser.

### Option B: Docker Compose (Recommended)

```bash
# Clone the repo
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

# Start everything (Ollama + OpenChat)
docker compose up -d

# Pull a model inside the Ollama container
docker exec ollama ollama pull llama3.1:8b
```

Open **http://localhost:8000** in your browser.

#### Enable GPU in Docker

**NVIDIA GPU:**
Uncomment the GPU section in `docker-compose.yml` and ensure you have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed.

**AMD GPU:**
```yaml
devices:
  - /dev/kfd
  - /dev/dri
```

**Apple Silicon:**
Ollama on macOS uses Metal automatically — run Ollama natively (not in Docker) for best performance.

## Usage

### Adding Documents

1. Click the **Documents** button (file icon) in the sidebar
2. Choose one of:
   - **Upload files** — Select .txt, .pdf, .docx, .md, .csv, or .xml files
   - **Index folder** — Enter a local folder path to index all supported files
   - **YouTube** — Paste a YouTube URL to extract and index the transcript
3. Toggle **RAG** on/off in the input bar to control whether documents are used

### Chatting

- Type your question and press Enter (or click send)
- When RAG is enabled, relevant document chunks are automatically retrieved
- Source files are shown as tags below the AI's response
- Switch models using the dropdown in the input bar

## System Requirements

| Tier | RAM | GPU | Models | Speed |
|------|-----|-----|--------|-------|
| Minimum | 8 GB | None (CPU) | 3B | ~5-12 tok/s |
| Recommended | 16 GB | 6-8 GB VRAM | 7B-8B | ~25-45 tok/s |
| Optimal | 32 GB | 16-24 GB VRAM | 14B-70B | ~30-80 tok/s |

**Supported GPUs:** NVIDIA (GTX 10-series+), AMD (RX 5000+), Intel Arc, Apple Silicon (M1+)

## Configuration

Edit `.env` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `DEFAULT_MODEL` | `llama3.1:8b` | Default model to use |
| `CHROMA_PERSIST_DIR` | `./data/chromadb` | Vector DB storage path |
| `MAX_FILE_SIZE_MB` | `50` | Max upload file size |

## Project Structure

```
openchat-local/
├── main.py                 # FastAPI server & API routes
├── config.py               # Configuration & settings
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Full stack deployment
├── .env.example            # Environment template
├── utils/
│   ├── ollama_client.py    # Ollama API client (streaming)
│   ├── rag_engine.py       # ChromaDB RAG pipeline
│   └── document_loader.py  # File parsers (PDF, DOCX, TXT, YouTube)
├── templates/
│   └── index.html          # Main UI template
└── static/
    ├── css/style.css       # Dark theme styles
    └── js/app.js           # Frontend logic
```

## Comparison: OpenChat Local vs Chat with RTX

| Feature | Chat with RTX | OpenChat Local |
|---------|--------------|----------------|
| OS Support | Windows only | Windows, macOS, Linux |
| GPU Required | NVIDIA RTX 30+ | Any GPU or CPU-only |
| Min VRAM | 8 GB | 0 (CPU mode) |
| File Types | txt, pdf, docx, xml | txt, pdf, docx, md, csv, xml |
| YouTube | Yes | Yes |
| Open Source | Partial (ref project) | Fully open source |
| Install Size | ~40 GB | ~2 GB + model |
| Customizable | Limited | Fully customizable |

## Contributing

Contributions are welcome! Please open an issue or PR.

## License

MIT License — use it however you want.
