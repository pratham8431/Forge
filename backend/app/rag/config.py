"""RAG-specific configuration — tuning knobs for chunking, embeddings, and generation."""
import os


class RAGConfig:
    # ── Chunking ──────────────────────────────────────────────────────────────
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 200
    MAX_CHUNKS_PER_DOCUMENT = 80
    MIN_CHUNK_LENGTH = 3
    MIN_MEANINGFUL_CHARS = 1

    # ── Vector search ─────────────────────────────────────────────────────────
    SIMILARITY_TOP_K = 25
    SIMILARITY_THRESHOLD = 0.5
    SMALL_DOC_TOP_K = 20
    MEDIUM_DOC_TOP_K = 35
    LARGE_DOC_TOP_K = 50

    # ── Provider selection ────────────────────────────────────────────────────
    # LLM_PROVIDER: "ollama" | "openai"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
    OPENAI_EMBEDDING_DIMS = 3072
    OPENAI_COMPLETION_MODEL = "gpt-4o"

    # ── Ollama (local) ────────────────────────────────────────────────────────
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_EMBEDDING_DIMS = 768
    OLLAMA_COMPLETION_MODEL = os.getenv("OLLAMA_COMPLETION_MODEL", "qwen3:8b")

    # ── Claude Haiku + Jina (cloud, no local GPU) ─────────────────────────────
    CLAUDE_COMPLETION_MODEL = "claude-haiku-4-5-20251001"
    JINA_EMBEDDING_MODEL = "jina-embeddings-v3"
    JINA_EMBEDDING_DIMS = 768  # Matryoshka truncation — matches current vector column

    # ── Active embedding dims (used by models.py for Vector column size) ──────
    EMBEDDING_DIMS = (
        OLLAMA_EMBEDDING_DIMS if LLM_PROVIDER == "ollama"
        else 3072  # gemini, openai, and claude all use 3072
    )

    TEMPERATURE = 0.1
    MAX_TOKENS = 1500

    # ── Parallel processing ───────────────────────────────────────────────────
    MAX_WORKERS_CHUNKING = 12
    MAX_WORKERS_EMBEDDINGS = 8
    MAX_WORKERS_ANSWERS = 6
    BATCH_SIZE_EMBEDDINGS = 100
    BATCH_SIZE_CHUNKS = 200

    # ── Timeouts ──────────────────────────────────────────────────────────────
    EMBEDDING_TIMEOUT = 15
    COMPLETION_TIMEOUT = 20
    MAX_RETRIES = 2
    RETRY_DELAY = 1

    # ── File processing ───────────────────────────────────────────────────────
    ENABLE_PPT_PROCESSING = True
    PPT_EXTRACT_NOTES = True
    ENABLE_IMAGE_PROCESSING = True
    ENABLE_EXCEL_PROCESSING = True
    ENABLE_CSV_PROCESSING = True
    ENABLE_ZIP_PROCESSING = True
    MAX_ZIP_FILES = 20
    MAX_EXCEL_ROWS = 10_000
    MAX_EXCEL_COLUMNS = 100

    # ── Gemini (generation + embeddings + image OCR) ──────────────────────────
    GEMINI_COMPLETION_MODEL = "gemini-2.0-flash-exp"
    GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
    GEMINI_EMBEDDING_DIMS = 3072
    GEMINI_MODEL = "gemini-2.0-flash-exp"   # kept for image OCR compatibility
    GEMINI_TIMEOUT = 10

    # ── Context ───────────────────────────────────────────────────────────────
    CONTEXT_WINDOW_SIZE = 300

    # ── Document size thresholds ──────────────────────────────────────────────
    SMALL_DOC_THRESHOLD = 50_000
    LARGE_DOC_THRESHOLD = 200_000

    ENABLE_FAST_CHUNKING = True
