"""
OpenChat Local — Folder Watcher
Monitors a directory for new or modified documents and auto-indexes them into RAG.
Uses a lightweight polling approach (no external dependencies like watchdog needed).
"""
import os
import time
import json
import hashlib
import asyncio
import threading
from typing import Dict, Set
from pathlib import Path

from config import settings
from utils.rag_engine import rag_engine
from utils.document_loader import LOADERS

WATCH_STATE_FILE = os.path.join(settings.CHROMA_PERSIST_DIR, "_watch_state.json")


class FolderWatcher:
    def __init__(self):
        self.watch_dirs: list[str] = []
        self.poll_interval: int = int(os.getenv("WATCH_INTERVAL", "3600"))  # seconds (default: 60 min)
        self._file_hashes: Dict[str, str] = {}
        self._running = False
        self._thread = None
        self._stats = {"total_watched": 0, "last_scan": None, "auto_indexed": 0}
        self._load_state()

    # ── State persistence ───────────────────

    def _state_path(self) -> str:
        return WATCH_STATE_FILE

    def _load_state(self):
        """Load previously seen file hashes and watch dirs from disk."""
        try:
            with open(self._state_path(), "r") as f:
                data = json.load(f)
                self._file_hashes = data.get("hashes", {})
                self.watch_dirs = data.get("watch_dirs", [])
                self._stats["auto_indexed"] = data.get("auto_indexed", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            self._file_hashes = {}
            self.watch_dirs = []

        default_watch = os.getenv("WATCH_FOLDER", "")
        if default_watch and default_watch not in self.watch_dirs:
            if os.path.isdir(default_watch):
                self.watch_dirs.append(default_watch)

    def _save_state(self):
        """Persist file hashes and watch dirs to disk."""
        os.makedirs(os.path.dirname(self._state_path()), exist_ok=True)
        data = {
            "hashes": self._file_hashes,
            "watch_dirs": self.watch_dirs,
            "auto_indexed": self._stats["auto_indexed"],
        }
        with open(self._state_path(), "w") as f:
            json.dump(data, f)

    # ── File hashing ────────────────────────

    def _hash_file(self, filepath: str) -> str:
        """Fast hash using file size + mtime + first 4KB."""
        try:
            stat = os.stat(filepath)
            h = hashlib.md5()
            h.update(f"{filepath}:{stat.st_size}:{stat.st_mtime}".encode())
            with open(filepath, "rb") as f:
                h.update(f.read(4096))
            return h.hexdigest()
        except OSError:
            return ""

    # ── Scanning ────────────────────────────

    def _get_supported_files(self, folder: str) -> Dict[str, str]:
        """Walk a folder and return {filepath: hash} for all supported files."""
        supported = set(LOADERS.keys())
        files = {}
        try:
            for root, dirs, filenames in os.walk(folder):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in supported:
                        fpath = os.path.join(root, fname)
                        files[fpath] = self._hash_file(fpath)
        except OSError as e:
            print(f"[Watcher] Error scanning {folder}: {e}")
        return files

    def scan_and_index(self) -> Dict:
        """Scan all watch dirs, find new/changed files, and index them."""
        new_files = []
        changed_files = []
        all_current = {}

        for folder in self.watch_dirs:
            if not os.path.isdir(folder):
                continue
            current_files = self._get_supported_files(folder)
            all_current.update(current_files)

            for fpath, fhash in current_files.items():
                if fpath not in self._file_hashes:
                    new_files.append(fpath)
                elif self._file_hashes[fpath] != fhash:
                    changed_files.append(fpath)

        # Index new and changed files
        indexed = []
        for fpath in new_files + changed_files:
            try:
                result = rag_engine.ingest_file(fpath)
                if result.get("status") == "ok":
                    indexed.append({
                        "filename": result.get("filename", os.path.basename(fpath)),
                        "chunks": result.get("chunks", 0),
                        "is_new": fpath in new_files,
                    })
                    self._stats["auto_indexed"] += 1
            except Exception as e:
                print(f"[Watcher] Error indexing {fpath}: {e}")

        # Update hashes
        self._file_hashes = all_current
        self._stats["total_watched"] = len(all_current)
        self._stats["last_scan"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_state()

        return {
            "new_files": len(new_files),
            "changed_files": len(changed_files),
            "indexed": indexed,
        }

    # ── Background loop ─────────────────────

    def _poll_loop(self):
        """Background polling loop (runs in a thread)."""
        print(f"[Watcher] Started — polling every {self.poll_interval}s")
        print(f"[Watcher] Watching: {self.watch_dirs}")

        while self._running:
            try:
                result = self.scan_and_index()
                if result["indexed"]:
                    names = [f["filename"] for f in result["indexed"]]
                    print(f"[Watcher] Auto-indexed {len(names)} file(s): {', '.join(names)}")
            except Exception as e:
                print(f"[Watcher] Error in poll loop: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start the background watcher thread."""
        if self._running or not self.watch_dirs:
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background watcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    # ── Management ──────────────────────────

    def add_folder(self, folder: str) -> Dict:
        """Add a folder to the watch list."""
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return {"status": "error", "message": f"Not a valid directory: {folder}"}

        if folder in self.watch_dirs:
            return {"status": "ok", "message": "Already watching this folder"}

        self.watch_dirs.append(folder)
        self._save_state()

        # Do an immediate scan
        result = self.scan_and_index()

        # Start watcher if not running
        if not self._running:
            self.start()

        return {
            "status": "ok",
            "folder": folder,
            "initial_scan": result,
        }

    def remove_folder(self, folder: str) -> Dict:
        """Remove a folder from the watch list."""
        folder = os.path.abspath(folder)
        if folder in self.watch_dirs:
            self.watch_dirs.remove(folder)
            # Remove hashes for files in this folder
            self._file_hashes = {
                k: v for k, v in self._file_hashes.items()
                if not k.startswith(folder)
            }
            self._save_state()
            return {"status": "ok", "message": f"Stopped watching {folder}"}
        return {"status": "error", "message": "Folder not in watch list"}

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "watch_dirs": self.watch_dirs,
            "poll_interval": self.poll_interval,
            "total_files_tracked": self._stats["total_watched"],
            "total_auto_indexed": self._stats["auto_indexed"],
            "last_scan": self._stats["last_scan"],
        }


folder_watcher = FolderWatcher()
