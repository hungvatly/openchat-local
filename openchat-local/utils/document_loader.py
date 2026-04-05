"""
OpenChat Local — Document Loader
Supports: .txt, .pdf, .docx, .md, .csv, .xml, YouTube URLs
"""
import os
import re
import subprocess
import json
from typing import List, Dict, Optional


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def load_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_pdf(filepath: str) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"[Error reading PDF: {e}]"


def load_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[Error reading DOCX: {e}]"


def load_csv(filepath: str) -> str:
    import csv
    rows = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(", ".join(row))
    return "\n".join(rows)


def load_youtube_transcript(url: str) -> Optional[str]:
    """Extract transcript from a YouTube video using yt-dlp."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--sub-format", "json3",
                "-o", "/tmp/yt_transcript",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        transcript_file = "/tmp/yt_transcript.en.json3"
        if os.path.exists(transcript_file):
            with open(transcript_file, "r") as f:
                data = json.load(f)
            segments = data.get("events", [])
            text_parts = []
            for seg in segments:
                segs = seg.get("segs", [])
                for s in segs:
                    t = s.get("utf8", "").strip()
                    if t and t != "\n":
                        text_parts.append(t)
            os.remove(transcript_file)
            return " ".join(text_parts)

        vtt_file = "/tmp/yt_transcript.en.vtt"
        if os.path.exists(vtt_file):
            with open(vtt_file, "r") as f:
                content = f.read()
            lines = content.split("\n")
            text_parts = []
            for line in lines:
                line = line.strip()
                if not line or "-->" in line or line.startswith("WEBVTT") or line.isdigit():
                    continue
                clean = re.sub(r"<[^>]+>", "", line)
                if clean:
                    text_parts.append(clean)
            os.remove(vtt_file)
            return " ".join(text_parts)

        return None
    except Exception as e:
        print(f"YouTube transcript error: {e}")
        return None


LOADERS = {
    ".txt": load_txt,
    ".md": load_txt,
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".csv": load_csv,
    ".xml": load_txt,
}


def load_document(filepath: str) -> Dict:
    """Load a document and return its text content with metadata."""
    ext = os.path.splitext(filepath)[1].lower()
    loader = LOADERS.get(ext)
    if not loader:
        return {"error": f"Unsupported file type: {ext}", "text": "", "filename": os.path.basename(filepath)}

    text = loader(filepath)
    return {
        "text": text,
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "extension": ext,
        "size": os.path.getsize(filepath),
    }


def load_folder(folder_path: str) -> List[Dict]:
    """Load all supported documents from a folder."""
    documents = []
    supported_exts = set(LOADERS.keys())

    for root, dirs, files in os.walk(folder_path):
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported_exts:
                fpath = os.path.join(root, fname)
                doc = load_document(fpath)
                if doc.get("text"):
                    documents.append(doc)

    return documents
