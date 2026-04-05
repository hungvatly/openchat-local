"""
OpenChat Local — RAG Engine
ChromaDB-backed retrieval-augmented generation pipeline.
"""
import hashlib
import time
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from utils.document_loader import chunk_text, load_document, load_folder


class RAGEngine:
    def __init__(self):
        self._client = None
        self._collection = None
        self._embedding_fn = None
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        self._client = chromadb.Client(ChromaSettings(
            anonymized_telemetry=False,
            is_persistent=True,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        ))
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True

    @property
    def collection(self):
        self._ensure_init()
        return self._collection

    def _make_id(self, text: str, source: str) -> str:
        h = hashlib.md5(f"{source}:{text[:200]}".encode()).hexdigest()
        return h

    def ingest_file(self, filepath: str) -> Dict:
        """Ingest a single file into the vector store."""
        doc = load_document(filepath)
        if not doc.get("text"):
            return {"status": "error", "message": f"Could not read {filepath}"}

        chunks = chunk_text(doc["text"], settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            return {"status": "error", "message": "No text content found"}

        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            cid = self._make_id(chunk, doc["filename"])
            ids.append(cid)
            documents.append(chunk)
            metadatas.append({
                "source": doc["filename"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        return {
            "status": "ok",
            "filename": doc["filename"],
            "chunks": len(chunks),
            "size": doc.get("size", 0),
        }

    def ingest_folder(self, folder_path: str) -> List[Dict]:
        """Ingest all documents in a folder."""
        docs = load_folder(folder_path)
        results = []
        for doc in docs:
            chunks = chunk_text(doc["text"], settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
            if not chunks:
                continue

            ids = []
            documents = []
            metadatas = []
            for i, chunk in enumerate(chunks):
                cid = self._make_id(chunk, doc["filename"])
                ids.append(cid)
                documents.append(chunk)
                metadatas.append({
                    "source": doc["filename"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })

            self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            results.append({
                "filename": doc["filename"],
                "chunks": len(chunks),
            })

        return results

    def ingest_text(self, text: str, source_name: str = "pasted_text") -> Dict:
        """Ingest raw text."""
        chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            return {"status": "error", "message": "No content"}

        ids = [self._make_id(c, source_name) for c in chunks]
        metadatas = [{"source": source_name, "chunk_index": i, "total_chunks": len(chunks)} for i, c in enumerate(chunks)]

        self.collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        return {"status": "ok", "source": source_name, "chunks": len(chunks)}

    def query(self, question: str, top_k: int = None) -> List[Dict]:
        """Retrieve relevant chunks for a question."""
        k = top_k or settings.TOP_K_RESULTS
        count = self.collection.count()
        if count == 0:
            return []

        k = min(k, count)
        results = self.collection.query(query_texts=[question], n_results=k)

        retrieved = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 0
                retrieved.append({
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": round(1 - dist, 4),
                })

        return retrieved

    def build_context(self, question: str) -> str:
        """Build a context string from retrieved documents."""
        results = self.query(question)
        if not results:
            return ""

        context_parts = []
        for r in results:
            context_parts.append(f"[Source: {r['source']}]\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)

    def get_stats(self) -> Dict:
        """Return stats about the current vector store."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
        }

    def clear(self) -> Dict:
        """Clear all documents from the store."""
        self._ensure_init()
        self._client.delete_collection("documents")
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        return {"status": "ok", "message": "All documents cleared"}


rag_engine = RAGEngine()
