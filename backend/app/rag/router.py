import uuid
from typing import Literal
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.iam.access.middleware import get_current_user, require_permission, CurrentUser
from app.rag.models import Document, Conversation
from app.rag.services import rag_service
from pydantic import BaseModel

router = APIRouter(prefix="/rag", tags=["RAG Search"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    mode: Literal["fast", "concise", "dynamic"] = "fast"


class BatchQARequest(BaseModel):
    questions: list[str]
    mode: Literal["fast", "concise", "dynamic"] = "fast"


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    doc = await rag_service.upload_document(file, current.user.id, db)
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "created_at": doc.created_at,
    }


# ── List documents ────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current.user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in docs
    ]


# ── Search a specific document ────────────────────────────────────────────────

@router.post("/documents/{document_id}/search")
async def search_document(
    document_id: uuid.UUID,
    body: SearchRequest,
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    return await rag_service.search_document(
        body.query, document_id, current.user.id, db, mode=body.mode
    )


# ── Batch Q&A on a specific document ─────────────────────────────────────────

@router.post("/documents/{document_id}/batch-qa")
async def batch_qa(
    document_id: uuid.UUID,
    body: BatchQARequest,
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    return await rag_service.batch_qa(
        body.questions, document_id, current.user.id, db, mode=body.mode
    )


# ── Global search (across all user's docs) ────────────────────────────────────

@router.post("/search")
async def global_search(
    body: SearchRequest,
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    return await rag_service.search_all_documents(body.query, current.user.id, db, mode=body.mode)


# ── Conversation history ──────────────────────────────────────────────────────

@router.get("/conversations")
async def get_conversations(
    document_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Conversation).where(Conversation.user_id == current.user.id)
    if document_id:
        query = query.where(Conversation.document_id == document_id)
    query = query.order_by(Conversation.created_at.desc()).limit(limit)

    result = await db.execute(query)
    convos = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "question": c.question,
            "answer": c.answer,
            "document_id": str(c.document_id) if c.document_id else None,
            "created_at": c.created_at,
        }
        for c in convos
    ]


# ── Delete a document ─────────────────────────────────────────────────────────

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current: CurrentUser = Depends(require_permission("rag:search")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current.user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")

    await rag_service.delete_document_chunks(db, document_id)
    await db.delete(doc)
    await db.commit()
    return {"message": f"Document '{doc.filename}' deleted"}
