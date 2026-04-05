"""
OpenChat Local — Chat History (SQLite)
Persistent chat storage with conversation management.
"""
import os
import json
import sqlite3
import time
from typing import List, Dict, Optional
from config import settings

DB_PATH = os.path.join(settings.CHROMA_PERSIST_DIR, "chat_history.db")


class ChatHistory:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT 'New Chat',
                    model TEXT DEFAULT '',
                    created_at REAL,
                    updated_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    images TEXT DEFAULT '',
                    sources TEXT DEFAULT '[]',
                    created_at REAL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def create_conversation(self, conv_id: str, title: str = "New Chat", model: str = "") -> Dict:
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, title, model, now, now),
            )
            conn.commit()
        return {"id": conv_id, "title": title, "model": model, "created_at": now}

    def add_message(self, conv_id: str, role: str, content: str, images: str = "", sources: list = None) -> int:
        now = time.time()
        src_json = json.dumps(sources or [])
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, images, sources, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (conv_id, role, content, images, src_json, now),
            )
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
            conn.commit()
            return cur.lastrowid

    def update_title(self, conv_id: str, title: str):
        with self._conn() as conn:
            conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
            conn.commit()

    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, model, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not row:
                return None
            messages = conn.execute(
                "SELECT role, content, images, sources, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conv_id,),
            ).fetchall()
            return {
                "id": row["id"],
                "title": row["title"],
                "model": row["model"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "messages": [
                    {
                        "role": m["role"],
                        "content": m["content"],
                        "images": m["images"],
                        "sources": json.loads(m["sources"]) if m["sources"] else [],
                        "created_at": m["created_at"],
                    }
                    for m in messages
                ],
            }

    def delete_conversation(self, conv_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()

    def export_markdown(self, conv_id: str) -> Optional[str]:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        lines = [f"# {conv['title']}\n"]
        for m in conv["messages"]:
            role_label = "You" if m["role"] == "user" else "AI"
            lines.append(f"### {role_label}\n")
            lines.append(m["content"] + "\n")
            if m["sources"]:
                src_names = [s.get("source", "") for s in m["sources"] if s.get("source")]
                if src_names:
                    lines.append(f"*Sources: {', '.join(src_names)}*\n")
            lines.append("---\n")
        return "\n".join(lines)

    def get_messages_for_context(self, conv_id: str, limit: int = 10) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
                (conv_id, limit),
            ).fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


chat_history = ChatHistory()
