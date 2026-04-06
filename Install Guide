Here's a complete step-by-step guide for all three platforms.

---

## Windows

### Step 1 — Install Python 3.12

1. Go to **https://www.python.org/downloads/**
2. Download **Python 3.12.x** (not 3.13 or 3.14 — those have compatibility issues)
3. Run the installer
4. **Check the box "Add python.exe to PATH"** at the bottom of the installer — this is critical
5. Click "Install Now"
6. Verify it works — open PowerShell and type:
   ```powershell
   python --version
   ```
   You should see `Python 3.12.x`

### Step 2 — Install Ollama

1. Go to **https://ollama.com/download**
2. Download the Windows installer
3. Run it — Ollama installs and starts automatically in the system tray
4. Verify — open PowerShell:
   ```powershell
   ollama --version
   ```

### Step 3 — Pull a model

Open PowerShell:

```powershell
# Pick ONE based on your hardware:

# Low-end (no GPU, 8-20GB RAM) — fastest, ~1GB download
ollama pull qwen2.5:1.5b

# Mid-range (GPU with 6-8GB VRAM)
ollama pull llama3.1:8b

# High-end (GPU with 16GB+ VRAM)
ollama pull qwen2.5:14b
```

Wait for it to finish downloading. Verify:
```powershell
ollama list
```

### Step 4 — Download OpenChat Local

Option A — With Git:
```powershell
git clone https://github.com/your-username/openchat-local.git
cd openchat-local
```

Option B — Without Git:
1. Download the ZIP from GitHub
2. Extract it to a folder like `E:\openchat-local`
3. Open PowerShell and navigate there:
   ```powershell
   cd E:\openchat-local
   ```

### Step 5 — Create virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of your prompt.

### Step 6 — Install dependencies

```powershell
pip install -r requirements.txt
```

This takes a few minutes. If you get a Rust compilation error, run this instead:
```powershell
pip install fastapi uvicorn[standard] python-multipart jinja2 aiohttp chromadb sentence-transformers pypdf2 python-docx beautifulsoup4 yt-dlp pydantic pydantic-settings aiofiles psutil fpdf2 openpyxl
```

### Step 7 — Configure

```powershell
copy .env.example .env
notepad .env
```

In Notepad, change these lines to match your setup:
```env
DEFAULT_MODEL=qwen2.5:1.5b
PERFORMANCE_PROFILE=low
```

If you want auto-indexing, set your watch folder in PowerShell before running (don't put it in .env):
```powershell
$env:WATCH_FOLDER = "C:\Users\YourName\Documents"
```

Save and close Notepad.

### Step 8 — Run

```powershell
python main.py
```

Open **http://localhost:8000** in your browser.

### Step 9 — Optional features

```powershell
# Voice input
pip install faster-whisper

# Image understanding (pull a vision model)
ollama pull moondream
```

### Everyday usage (after first setup)

```powershell
cd E:\openchat-local
venv\Scripts\activate
python main.py
```

---

## macOS

### Step 1 — Install Python 3.12

Option A — From python.org:
1. Go to **https://www.python.org/downloads/**
2. Download Python 3.12.x for macOS
3. Run the installer

Option B — With Homebrew (if you have it):
```bash
brew install python@3.12
```

Verify:
```bash
python3 --version
```

### Step 2 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or download from **https://ollama.com/download** and drag to Applications.

Verify:
```bash
ollama --version
```

### Step 3 — Pull a model

```bash
# Apple Silicon (M1/M2/M3/M4) — uses unified memory, can run bigger models
ollama pull llama3.1:8b

# Intel Mac or if you want faster responses
ollama pull qwen2.5:1.5b
```

### Step 4 — Download and set up

```bash
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Step 5 — Configure

```bash
cp .env.example .env
nano .env    # or: open -e .env
```

Edit:
```env
DEFAULT_MODEL=llama3.1:8b
PERFORMANCE_PROFILE=auto
```

For watch folder, set it as an environment variable:
```bash
export WATCH_FOLDER="$HOME/Documents"
```

Save and exit (in nano: Ctrl+O, Enter, Ctrl+X).

### Step 6 — Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

### Step 7 — Optional features

```bash
# Voice input
pip install faster-whisper

# Image understanding
ollama pull moondream
```

### Everyday usage

```bash
cd ~/openchat-local
source venv/bin/activate
python main.py
```

---

## Linux (Ubuntu/Debian)

### Step 1 — Install Python 3.12

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Verify:
```bash
python3 --version
```

If it shows 3.13+, install 3.12 specifically:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### Step 2 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start Ollama:
```bash
ollama serve &
```

Verify:
```bash
ollama --version
```

### Step 3 — Pull a model

```bash
# No GPU
ollama pull qwen2.5:1.5b

# NVIDIA GPU
ollama pull llama3.1:8b

# AMD GPU (make sure ROCm is installed)
ollama pull llama3.1:8b
```

### Step 4 — Download and set up

```bash
git clone https://github.com/your-username/openchat-local.git
cd openchat-local

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Step 5 — Configure

```bash
cp .env.example .env
nano .env
```

Edit:
```env
DEFAULT_MODEL=qwen2.5:1.5b
PERFORMANCE_PROFILE=auto
```

For watch folder:
```bash
export WATCH_FOLDER="$HOME/Documents"
```

### Step 6 — Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

### Step 7 — Optional features

```bash
# Voice input
pip install faster-whisper

# Image understanding
ollama pull moondream
```

### Run on startup (optional)

Create a systemd service:
```bash
sudo nano /etc/systemd/system/openchat.service
```

Paste:
```ini
[Unit]
Description=OpenChat Local
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/openchat-local
Environment=WATCH_FOLDER=/home/your-username/Documents
ExecStart=/home/your-username/openchat-local/venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable openchat
sudo systemctl start openchat
```

---

## Quick reference card

| What | Windows | macOS | Linux |
|------|---------|-------|-------|
| Activate venv | `venv\Scripts\activate` | `source venv/bin/activate` | `source venv/bin/activate` |
| Set watch folder | `$env:WATCH_FOLDER = "C:\..."` | `export WATCH_FOLDER="$HOME/..."` | `export WATCH_FOLDER="$HOME/..."` |
| Run | `python main.py` | `python main.py` | `python main.py` |
| Stop | `Ctrl+C` | `Ctrl+C` | `Ctrl+C` |
| Open UI | http://localhost:8000 | http://localhost:8000 | http://localhost:8000 |
