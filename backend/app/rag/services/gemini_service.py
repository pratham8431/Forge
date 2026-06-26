"""
Gemini service for Forge RAG — generation + embeddings via Google Generative AI.
text-embedding-004 → 768 dims (matches current vector column, free tier).
gemini-2.0-flash → fast generation (free tier: 15 RPM / 1M TPD).
"""
import asyncio
import logging
from typing import List, Dict
from functools import partial

import google.generativeai as genai

from app.core.config import settings
from app.rag.config import RAGConfig
from app.rag.agents.agentic_prompts import (
    get_document_specific_prompt,
    get_file_type_prompt,
)

logger = logging.getLogger(__name__)

_configured = False
_llm_cache: dict = {}


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


# ── Embeddings ────────────────────────────────────────────────────────────────

def _embed_batch_sync(texts: List[str], task_type: str) -> List[List[float]]:
    _ensure_configured()
    result = genai.embed_content(
        model=RAGConfig.GEMINI_EMBEDDING_MODEL,
        content=texts,
        task_type=task_type,
    )
    embeddings = result.get("embedding", [])
    # Single text returns a flat list; multiple texts returns list of lists
    if texts and not isinstance(embeddings[0], list):
        return [embeddings]
    return embeddings


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    _ensure_configured()
    loop = asyncio.get_event_loop()
    batch_size = 20  # Stay well within free-tier rate limits
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = await loop.run_in_executor(
                None,
                partial(_embed_batch_sync, batch, "retrieval_document"),
            )
            all_embeddings.extend(result)
        except Exception as e:
            logger.error(f"Gemini embedding batch error: {e}")
            # Fill with zeros so the rest of the pipeline doesn't crash
            return []  # surface the error instead of storing garbage zero vectors

    return all_embeddings


async def get_query_embedding(query: str) -> List[float]:
    _ensure_configured()
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            partial(_embed_batch_sync, [query], "retrieval_query"),
        )
        return result[0] if result else []
    except Exception as e:
        logger.error(f"Gemini query embedding error: {e}")
        return []


# ── Answer generation ─────────────────────────────────────────────────────────

def _build_system_prompt(
    query: str,
    relevant_docs: Dict,
    mode: str,
    document_url: str | None,
    file_extension: str | None,
    document_content: str,
    file_type: str,
) -> str:
    context_parts = []
    for doc in relevant_docs.get("documents", [[]])[0]:
        context_parts.append(doc if isinstance(doc, str) else str(doc))
    context_text = "\n".join(context_parts)

    if not context_text.strip() or len(context_text.strip()) < 50:
        return (
            "The provided context contains insufficient information. "
            f"Question: {query} "
            "Response: I cannot answer based on the available document content."
        )

    doc_prompt = None
    if document_url:
        doc_prompt = get_document_specific_prompt(document_url, document_content, file_type)
    if not doc_prompt and file_extension:
        doc_prompt = get_file_type_prompt(file_extension)

    base_instructions = (
        "Provide a comprehensive answer based on the document content below. "
        "Write in ONE flowing paragraph. No markdown, no bullet points, no source references. "
        "Be precise with numbers, dates, and names. "
        "If exact info is absent but context is related, use intelligent reasoning. "
        "For completely unrelated questions, politely decline."
    )
    if mode == "concise":
        base_instructions = (
            "Provide a SHORT, PRECISE answer based on the document content. "
            "One paragraph maximum. No markdown formatting."
        )

    prefix = f"{doc_prompt}\n\n" if doc_prompt else ""
    return (
        f"{prefix}{base_instructions}\n\n"
        f"Document Content:\n{context_text}\n\n"
        f"Question: {query}"
    )


def _generate_sync(prompt: str, mode: str) -> str:
    _ensure_configured()
    max_tokens = {"fast": RAGConfig.MAX_TOKENS, "concise": 150, "dynamic": 800}.get(mode, RAGConfig.MAX_TOKENS)
    temperature = {"fast": RAGConfig.TEMPERATURE, "concise": 0.1, "dynamic": 0.2}.get(mode, RAGConfig.TEMPERATURE)

    model = genai.GenerativeModel(
        RAGConfig.GEMINI_COMPLETION_MODEL,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    response = model.generate_content(prompt)
    return response.text


async def generate_answer(
    query: str,
    relevant_docs: Dict,
    mode: str = "fast",
    document_url: str | None = None,
    file_extension: str | None = None,
    document_content: str = "",
    file_type: str = "pdf",
) -> str:
    cache_key = f"{mode}:{query}:{len(relevant_docs.get('documents', [[]])[0])}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    prompt = _build_system_prompt(query, relevant_docs, mode, document_url, file_extension, document_content, file_type)
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, partial(_generate_sync, prompt, mode))
    _llm_cache[cache_key] = answer
    return answer


# ── Parallel Q&A ──────────────────────────────────────────────────────────────

async def answer_questions_parallel(
    questions: List[str],
    relevant_docs_list: List[Dict],
    mode: str = "fast",
    document_url: str | None = None,
    file_extension: str | None = None,
    document_content: str = "",
    file_type: str = "pdf",
) -> List[str]:
    tasks = [
        generate_answer(q, d, mode, document_url, file_extension, document_content, file_type)
        for q, d in zip(questions, relevant_docs_list)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [str(r) if isinstance(r, Exception) else r for r in results]
