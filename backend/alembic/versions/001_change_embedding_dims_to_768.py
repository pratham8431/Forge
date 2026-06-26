"""Change embedding column from vector(3072) to vector(768) for Ollama nomic-embed-text.

Revision ID: 001
Revises:
Create Date: 2026-06-24
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Safe because all existing documents have status='failed' and chunk_count=0
    op.execute("TRUNCATE TABLE document_chunks")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)")


def downgrade():
    op.execute("TRUNCATE TABLE document_chunks")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(3072)")
