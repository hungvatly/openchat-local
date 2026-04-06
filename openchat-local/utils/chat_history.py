"""
OpenChat Local — Chat History (SQLite)
Persistent chat storage with personas, folders, tags, and full-text search.
"""
import os
import json
import sqlite3
import time
from typing import List, Dict, Optional
from config import settings

DB_PATH = os.path.join(settings.CHROMA_PERSIST_DIR, "chat_history.db")

# ── Default Personas ───────────────────────────────────

DEFAULT_PERSONAS = [
    {
        "id": "default",
        "name": "Default",
        "prompt": "You are OpenChat Local, a helpful AI assistant running entirely on the user's machine. You provide thorough, detailed, and comprehensive answers. When context from the user's documents is provided, use it extensively — quote relevant passages, explain key points in depth, and cite which source file the information comes from. Do not summarize unless the user specifically asks for a summary. Give complete, in-depth responses that fully address the user's question. If the context doesn't contain relevant information, say so honestly and answer from your general knowledge. Always be helpful, clear, and respectful.",
    },
    {
        "id": "translator",
        "name": "Translator",
        "prompt": "You are a professional translator. Translate text accurately between languages while preserving tone, context, and nuance. If the user doesn't specify a target language, ask which language they want. Provide natural, fluent translations — not word-for-word. For ambiguous phrases, explain multiple possible translations.",
    },
    {
        "id": "code_reviewer",
        "name": "Code Reviewer",
        "prompt": "You are a senior software engineer performing code review. Analyze code for bugs, security issues, performance problems, and style. Suggest specific improvements with corrected code. Explain why each change matters. Be thorough but constructive.",
    },
    {
        "id": "email_writer",
        "name": "Email Writer",
        "prompt": "You are a professional email composer. Write clear, well-structured emails matching the requested tone (formal, friendly, persuasive, apologetic). Include subject line suggestions. Adjust formality based on context. Keep emails concise but complete.",
    },
    {
        "id": "legal_advisor",
        "name": "Legal Advisor",
        "prompt": "You are a legal research assistant. Provide general legal information and help analyze documents from a legal perspective. Always clarify that you are an AI and not a licensed attorney. Flag potential legal issues, explain relevant concepts, and suggest when professional legal counsel is needed.",
    },
    {
        "id": "creative_writer",
        "name": "Creative Writer",
        "prompt": "You are a creative writing assistant. Help with stories, poems, scripts, and creative content. Use vivid language, strong imagery, and engaging narrative techniques. Adapt your style to match the requested genre and tone.",
    },
    {
        "id": "data_analyst",
        "name": "Data Analyst",
        "prompt": "You are a data analyst. Help interpret data, create analyses, and explain findings clearly. When given data, identify patterns, trends, and insights. Suggest visualizations. Present findings in a structured format with clear conclusions.",
    },
]


class ChatHistory:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT 'New Chat',
                    model TEXT DEFAULT '',
                    persona_id TEXT DEFAULT 'default',
                    folder TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    is_builtin INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)

            # Add columns if upgrading from old schema
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN persona_id TEXT DEFAULT 'default'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN folder TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN tags TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

            # FTS5 for full-text search
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                        content, conversation_id UNINDEXED,
                        content='messages', content_rowid='id'
                    )
                """)
                # Triggers to keep FTS in sync
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                        INSERT INTO messages_fts(rowid, content, conversation_id)
                        VALUES (new.id, new.content, new.conversation_id);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                        INSERT INTO messages_fts(messages_fts, rowid, content, conversation_id)
                        VALUES('delete', old.id, old.content, old.conversation_id);
                    END
                """)
            except Exception:
                pass  # FTS5 not available in this SQLite build

            # Seed default personas
            for p in DEFAULT_PERSONAS:
                conn.execute(
                    "INSERT OR IGNORE INTO personas (id, name, prompt, is_builtin, created_at) VALUES (?, ?, ?, 1, ?)",
                    (p["id"], p["name"], p["prompt"], time.time()),
                )
            conn.commit()

    # ── Conversations ──────────────────────────────────

    def create_conversation(self, conv_id: str, title: str = "New Chat", model: str = "", persona_id: str = "default") -> Dict:
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, model, persona_id, folder, tags, created_at, updated_at) VALUES (?, ?, ?, ?, '', '', ?, ?)",
                (conv_id, title, model, persona_id, now, now),
            )
            conn.commit()
        return {"id": conv_id, "title": title, "model": model, "persona_id": persona_id, "created_at": now}

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

    def update_conversation(self, conv_id: str, **kwargs):
        """Update any conversation fields: title, folder, tags, persona_id."""
        allowed = {"title", "folder", "tags", "persona_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [conv_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE conversations SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def list_conversations(self, limit: int = 50, offset: int = 0, folder: str = None, tag: str = None) -> List[Dict]:
        with self._conn() as conn:
            query = "SELECT id, title, model, persona_id, folder, tags, created_at, updated_at FROM conversations"
            params = []
            conditions = []
            if folder:
                conditions.append("folder = ?")
                params.append(folder)
            if tag:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
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
                "persona_id": row["persona_id"] if "persona_id" in row.keys() else "default",
                "folder": row["folder"] if "folder" in row.keys() else "",
                "tags": row["tags"] if "tags" in row.keys() else "",
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

    def get_folders(self) -> List[str]:
        """Get all unique folder names."""
        with self._conn() as conn:
            rows = conn.execute("SELECT DISTINCT folder FROM conversations WHERE folder != '' ORDER BY folder").fetchall()
            return [r["folder"] for r in rows]

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across conversations."""
        with self._conn() as conn:
            rows = conn.execute("SELECT tags FROM conversations WHERE tags != ''").fetchall()
            all_tags = set()
            for r in rows:
                for t in r["tags"].split(","):
                    t = t.strip()
                    if t:
                        all_tags.add(t)
            return sorted(all_tags)

    # ── Search ─────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Full-text search across all messages."""
        with self._conn() as conn:
            try:
                rows = conn.execute("""
                    SELECT m.conversation_id, m.role, m.content, m.created_at, c.title
                    FROM messages_fts f
                    JOIN messages m ON m.id = f.rowid
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE messages_fts MATCH ?
                    ORDER BY m.created_at DESC LIMIT ?
                """, (query, limit)).fetchall()
                return [
                    {
                        "conversation_id": r["conversation_id"],
                        "conversation_title": r["title"],
                        "role": r["role"],
                        "content": r["content"][:200],
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ]
            except Exception:
                # Fallback: LIKE search if FTS5 not available
                rows = conn.execute("""
                    SELECT m.conversation_id, m.role, m.content, m.created_at, c.title
                    FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE m.content LIKE ?
                    ORDER BY m.created_at DESC LIMIT ?
                """, (f"%{query}%", limit)).fetchall()
                return [
                    {
                        "conversation_id": r["conversation_id"],
                        "conversation_title": r["title"],
                        "role": r["role"],
                        "content": r["content"][:200],
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ]

    # ── Personas ───────────────────────────────────────

    def list_personas(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, name, prompt, is_builtin FROM personas ORDER BY is_builtin DESC, name").fetchall()
            return [dict(r) for r in rows]

    def get_persona(self, persona_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
            return dict(row) if row else None

    def save_persona(self, persona_id: str, name: str, prompt: str) -> Dict:
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO personas (id, name, prompt, is_builtin, created_at) VALUES (?, ?, ?, 0, ?)",
                (persona_id, name, prompt, now),
            )
            conn.commit()
        return {"id": persona_id, "name": name}

    def delete_persona(self, persona_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM personas WHERE id = ? AND is_builtin = 0", (persona_id,))
            conn.commit()

    # ── Export ─────────────────────────────────────────

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
