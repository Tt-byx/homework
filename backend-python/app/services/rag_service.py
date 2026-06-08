import asyncio
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed, RAG disabled. Install: pip install chromadb")


class RAGService:

    def __init__(self, persist_dir: str = "./data/chroma_db",
                 collection_name: str = "scenic_knowledge"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        return CHROMADB_AVAILABLE and self._initialized

    async def init(self):
        if not CHROMADB_AVAILABLE:
            logger.warning("chromadb not installed, skip RAG init")
            return

        try:
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            count = self._collection.count()
            self._initialized = True
            logger.info(f"ChromaDB init OK, docs: {count}")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")

    async def search(self, query: str, top_k: int = 3) -> list[str]:
        if not self.is_available:
            return []

        loop = asyncio.get_event_loop()

        def _query():
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            if results and results["documents"]:
                return results["documents"][0]
            return []

        return await loop.run_in_executor(None, _query)

    def build_prompt(self, query: str, context_chunks: list[str]) -> str:
        if not context_chunks:
            return query

        context = "\n---\n".join(context_chunks)
        return f"Please answer based on the following reference materials. If no relevant info, use your knowledge.\n\nReference:\n{context}\n\nQuestion: {query}"

    def _split_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        text = re.sub(r"\s+", " ", text.strip())
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks

    async def ingest_text(self, text: str, doc_id: str, metadata: Optional[dict] = None):
        if not self.is_available:
            logger.warning("RAG not available, cannot ingest")
            return

        chunks = self._split_text(text)
        if not chunks:
            return

        loop = asyncio.get_event_loop()

        def _insert():
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = []
            for i, chunk in enumerate(chunks):
                meta = {"doc_id": doc_id, "chunk_index": i}
                if metadata:
                    meta.update(metadata)
                metadatas.append(meta)
            self._collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

        await loop.run_in_executor(None, _insert)
        logger.info(f"Doc {doc_id} ingested, {len(chunks)} chunks")

    async def ingest_file(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        doc_id = os.path.splitext(file_name)[0]

        if file_path.endswith(('.txt', '.md')):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_path.endswith('.pdf'):
            try:
                import fitz
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            except ImportError:
                raise RuntimeError("PDF requires PyMuPDF: pip install PyMuPDF")
        elif file_path.endswith('.docx'):
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                raise RuntimeError("Word requires python-docx: pip install python-docx")
        else:
            raise ValueError(f"Unsupported format: {file_path}")

        await self.ingest_text(text, doc_id, metadata={"file_name": file_name})
        return doc_id

    async def ingest_from_directory(self, dir_path: str):
        if not os.path.exists(dir_path):
            logger.warning(f"Directory not found: {dir_path}")
            return

        supported_ext = ('.txt', '.md', '.pdf', '.docx')
        files = [
            os.path.join(dir_path, f)
            for f in os.listdir(dir_path)
            if f.endswith(supported_ext)
        ]

        if not files:
            logger.warning(f"No supported docs in {dir_path}")
            return

        logger.info(f"Ingesting {len(files)} docs...")
        for file_path in files:
            try:
                await self.ingest_file(file_path)
                logger.info(f"Ingested: {file_path}")
            except Exception as e:
                logger.error(f"Failed {file_path}: {e}")

    async def delete_doc(self, doc_id: str):
        if not self.is_available:
            return

        loop = asyncio.get_event_loop()

        def _delete():
            results = self._collection.get(where={"doc_id": doc_id})
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])

        await loop.run_in_executor(None, _delete)
        logger.info(f"Doc {doc_id} deleted")


rag_service = RAGService()
