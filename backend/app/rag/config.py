"""RAG-specific configuration — tuning knobs for chunking, embeddings, and generation."""


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

    # ── OpenAI (standard) ─────────────────────────────────────────────────────
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
    OPENAI_EMBEDDING_DIMS = 3072
    OPENAI_COMPLETION_MODEL = "gpt-4o"
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

    # ── Gemini (image OCR fallback) ───────────────────────────────────────────
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    GEMINI_TIMEOUT = 10

    # ── Context ───────────────────────────────────────────────────────────────
    CONTEXT_WINDOW_SIZE = 300

    # ── Document size thresholds ──────────────────────────────────────────────
    SMALL_DOC_THRESHOLD = 50_000
    LARGE_DOC_THRESHOLD = 200_000

    ENABLE_FAST_CHUNKING = True
