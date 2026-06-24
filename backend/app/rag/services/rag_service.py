"""Core RAG pipeline — upload → chunk → embed → store → search → answer."""
import uuid
import logging
import asyncio
from typing import List
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import Document, Conversation
from app.rag.services.utils import extract_text_from_file, chunk_text_advanced, process_chunks_parallel
from app.rag.services.openai_service import get_embeddings, get_query_embedding, generate_answer, answer_questions_parallel
from app.rag.services.pgvector_service import store_chunks, similarity_search, similarity_search_global, format_results_for_rag, delete_document_chunks
from app.rag.config import RAGConfig
from app.workers.audit_tasks import log_audit_event

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/csv": "csv",
    "application/zip": "zip",
    "image/png": "png",
    "image/jpeg": "jpg",
}


# ── Upload & Process ──────────────────────────────────────────────────────────

async def upload_document(
    file: UploadFile,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Document:
    file_type = SUPPORTED_TYPES.get(file.content_type)
    if not file_type:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    content = await file.read()
    file_size = len(content)

    doc = Document(
        user_id=user_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    await db.flush()

    try:
        # Restore file pointer for extraction
        class _FileLike:
            def __init__(self, data: bytes, name: str):
                self._data = data
                self.filename = name
                self._pos = 0

            def read(self, n=-1):
                if n == -1:
                    chunk = self._data[self._pos:]
                    self._pos = len(self._data)
                else:
                    chunk = self._data[self._pos:self._pos + n]
                    self._pos += n
                return chunk

            def seek(self, offset, whence=0):
                if whence == 0:
                    self._pos = offset
                elif whence == 1:
                    self._pos += offset
                elif whence == 2:
                    self._pos = len(self._data) + offset
                return self._pos

            def tell(self):
                return self._pos

        file_like = _FileLike(content, file.filename)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, extract_text_from_file, file_like)
        if not text:
            raise ValueError("No text could be extracted from the document")

        chunks = await loop.run_in_executor(None, chunk_text_advanced, text)
        processed_chunks = await loop.run_in_executor(None, process_chunks_parallel, chunks, "")

        if not processed_chunks:
            raise ValueError("Document produced no processable chunks")

        embeddings = await get_embeddings(processed_chunks)
        if not embeddings:
            raise ValueError("Failed to generate embeddings")

        stored = await store_chunks(db, doc.id, processed_chunks, embeddings)
        doc.chunk_count = stored
        doc.status = "ready"

    except Exception as e:
        doc.status = "failed"
        doc.metadata = {"error": str(e)}
        logger.error(f"Document processing failed for {file.filename}: {e}")

    await db.commit()
    await db.refresh(doc)

    log_audit_event.delay(str(user_id), "DOCUMENT_UPLOADED", metadata={
        "document_id": str(doc.id),
        "filename": doc.filename,
        "chunks": doc.chunk_count,
        "status": doc.status,
    })

    return doc


# ── Search ────────────────────────────────────────────────────────────────────

async def search_document(
    query: str,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    mode: str = "fast",
) -> dict:
    from sqlalchemy import select
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready (status: {doc.status})")

    query_embedding = await get_query_embedding(query)
    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to embed query")

    raw_results = await similarity_search(db, query_embedding, document_id)
    rag_docs = format_results_for_rag(raw_results)

    answer = await generate_answer(
        query, rag_docs, mode=mode,
        file_extension=doc.file_type, file_type=doc.file_type,
    )

    sources = [{"content": c[:200], "distance": d} for c, d in raw_results[:5]]

    convo = Conversation(
        user_id=user_id,
        document_id=document_id,
        question=query,
        answer=answer,
        sources=sources,
    )
    db.add(convo)
    await db.commit()

    log_audit_event.delay(str(user_id), "PROMPT_SUBMITTED", metadata={
        "document_id": str(document_id),
        "query_preview": query[:100],
    })

    return {"answer": answer, "sources": sources, "document": doc.filename}


async def search_all_documents(
    query: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    mode: str = "fast",
) -> dict:
    query_embedding = await get_query_embedding(query)
    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to embed query")

    raw_results = await similarity_search_global(db, query_embedding, user_id)
    if not raw_results:
        return {"answer": "No relevant documents found in your knowledge base.", "sources": []}

    rag_docs = format_results_for_rag([(c, d) for c, d, _ in raw_results])
    answer = await generate_answer(query, rag_docs, mode=mode)
    sources = [{"content": c[:200], "distance": d, "document_id": str(did)} for c, d, did in raw_results[:5]]

    convo = Conversation(user_id=user_id, question=query, answer=answer, sources=sources)
    db.add(convo)
    await db.commit()

    log_audit_event.delay(str(user_id), "PROMPT_SUBMITTED", metadata={"query_preview": query[:100], "global": True})
    return {"answer": answer, "sources": sources}


# ── Batch Q&A ─────────────────────────────────────────────────────────────────

async def batch_qa(
    questions: List[str],
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    mode: str = "fast",
) -> List[dict]:
    from sqlalchemy import select
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc or doc.status != "ready":
        raise HTTPException(status_code=404, detail="Document not found or not ready")

    query_embeddings = await get_embeddings(questions)

    async def _get_docs(emb):
        raw = await similarity_search(db, emb, document_id)
        return format_results_for_rag(raw)

    docs_list = await asyncio.gather(*[_get_docs(e) for e in query_embeddings])
    answers = await answer_questions_parallel(questions, docs_list, mode=mode, file_type=doc.file_type)

    return [{"question": q, "answer": a} for q, a in zip(questions, answers)]
