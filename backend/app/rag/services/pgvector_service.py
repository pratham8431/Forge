"""pgvector service — replaces ChromaDB/Pinecone from the original RAG repo."""
import uuid
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from sqlalchemy.orm import selectinload

from app.rag.models import Document, DocumentChunk
from app.rag.config import RAGConfig

logger = logging.getLogger(__name__)


async def store_chunks(
    db: AsyncSession,
    document_id: uuid.UUID,
    chunks: List[str],
    embeddings: List[List[float]],
) -> int:
    """Store document chunks with their embeddings in pgvector."""
    stored = 0
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        doc_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=idx,
            content=chunk,
            embedding=embedding,
        )
        db.add(doc_chunk)
        stored += 1

    await db.flush()
    return stored


async def similarity_search(
    db: AsyncSession,
    query_embedding: List[float],
    document_id: uuid.UUID,
    top_k: int = RAGConfig.SIMILARITY_TOP_K,
) -> List[Tuple[str, float]]:
    """
    Cosine similarity search against pgvector.
    Returns list of (chunk_content, distance) sorted by relevance.
    """
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT content, embedding <=> :embedding AS distance
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY distance ASC
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "doc_id": str(document_id), "top_k": top_k},
    )
    rows = result.fetchall()
    return [(row.content, float(row.distance)) for row in rows]


async def similarity_search_global(
    db: AsyncSession,
    query_embedding: List[float],
    user_id: uuid.UUID,
    top_k: int = RAGConfig.SIMILARITY_TOP_K,
) -> List[Tuple[str, float, uuid.UUID]]:
    """Search across all documents owned by a user."""
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT dc.content, dc.embedding <=> :embedding AS distance, dc.document_id
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.user_id = :user_id AND d.status = 'ready'
            ORDER BY distance ASC
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "user_id": str(user_id), "top_k": top_k},
    )
    rows = result.fetchall()
    return [(row.content, float(row.distance), row.document_id) for row in rows]


async def delete_document_chunks(db: AsyncSession, document_id: uuid.UUID) -> None:
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.flush()


def format_results_for_rag(results: List[Tuple[str, float]]) -> dict:
    """Convert pgvector results into the ChromaDB-compatible dict the RAG pipeline expects."""
    docs = [r[0] for r in results]
    distances = [r[1] for r in results]
    return {
        "documents": [docs],
        "metadatas": [[{}] * len(docs)],
        "distances": [distances],
    }
