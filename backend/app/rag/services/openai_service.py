"""
OpenAI service for Forge RAG — standard OpenAI (not Azure).
Preserves parallel embedding + answer architecture from the original RAG repo.
"""
import asyncio
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.config import RAGConfig
from app.rag.agents.agentic_prompts import (
    construct_rag_prompt_with_document_detection,
    get_document_specific_prompt,
    get_file_type_prompt,
)

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_embedding_executor = ThreadPoolExecutor(max_workers=RAGConfig.MAX_WORKERS_EMBEDDINGS)
_llm_cache: dict = {}


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ── Embeddings ────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(RAGConfig.MAX_RETRIES), wait=wait_exponential(min=RAGConfig.RETRY_DELAY, max=6))
async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Parallel batched embedding generation."""
    if not texts:
        return []

    client = get_client()
    batch_size = RAGConfig.BATCH_SIZE_EMBEDDINGS

    async def _batch(batch: List[str]) -> List[List[float]]:
        try:
            resp = await client.embeddings.create(
                model=RAGConfig.OPENAI_EMBEDDING_MODEL,
                input=batch,
                timeout=RAGConfig.EMBEDDING_TIMEOUT,
            )
            return [e.embedding for e in resp.data]
        except Exception as e:
            logger.error(f"Embedding batch error: {e}")
            return []

    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    results = await asyncio.gather(*[_batch(b) for b in batches], return_exceptions=True)

    embeddings: List[List[float]] = []
    for r in results:
        if isinstance(r, list):
            embeddings.extend(r)
    return embeddings


async def get_query_embedding(query: str) -> List[float]:
    results = await get_embeddings([query])
    return results[0] if results else []


# ── Answer generation ─────────────────────────────────────────────────────────

def _build_prompt(
    query: str,
    relevant_docs: Dict,
    mode: str = "fast",
    document_url: str | None = None,
    file_extension: str | None = None,
    document_content: str = "",
    file_type: str = "pdf",
) -> str:
    """Build the appropriate prompt based on mode."""
    context_parts = []
    for doc in relevant_docs.get("documents", [[]])[0]:
        context_parts.append(doc if isinstance(doc, str) else str(doc))
    context_text = "\n".join(context_parts)

    if not context_text.strip() or len(context_text.strip()) < 50:
        return (
            "CRITICAL INSTRUCTION: The provided context contains insufficient information.\n\n"
            f"Question: {query}\n\n"
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


@retry(stop=stop_after_attempt(RAGConfig.MAX_RETRIES), wait=wait_exponential(min=RAGConfig.RETRY_DELAY, max=6))
async def generate_answer(
    query: str,
    relevant_docs: Dict,
    mode: str = "fast",
    document_url: str | None = None,
    file_extension: str | None = None,
    document_content: str = "",
    file_type: str = "pdf",
) -> str:
    """Generate an answer from retrieved context. mode: fast | concise | dynamic"""
    cache_key = f"{mode}:{query}:{len(relevant_docs.get('documents', [[]])[0])}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    client = get_client()
    prompt = _build_prompt(query, relevant_docs, mode, document_url, file_extension, document_content, file_type)

    max_tokens = {"fast": RAGConfig.MAX_TOKENS, "concise": 150, "dynamic": 800}.get(mode, RAGConfig.MAX_TOKENS)
    temperature = {"fast": RAGConfig.TEMPERATURE, "concise": 0.1, "dynamic": 0.2}.get(mode, RAGConfig.TEMPERATURE)

    response = await client.chat.completions.create(
        model=RAGConfig.OPENAI_COMPLETION_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=RAGConfig.COMPLETION_TIMEOUT,
    )
    answer = response.choices[0].message.content
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
    """Answer multiple questions in parallel."""
    tasks = [
        generate_answer(q, d, mode, document_url, file_extension, document_content, file_type)
        for q, d in zip(questions, relevant_docs_list)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        str(r) if isinstance(r, Exception) else r
        for r in results
    ]
