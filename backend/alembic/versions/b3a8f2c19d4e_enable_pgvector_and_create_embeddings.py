"""enable pgvector and create embeddings table

Revision ID: b3a8f2c19d4e
Revises: 7f0e91ff0a5b
Create Date: 2026-06-13 00:00:00.000000

"""
from alembic import op

revision: str = "b3a8f2c19d4e"
down_revision: str = "7f0e91ff0a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (Neon supports this natively)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create embeddings table
    op.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id          SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES document(id) ON DELETE CASCADE,
            content     TEXT NOT NULL,
            embedding   vector(1536),
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # IVFFlat index for fast approximate cosine similarity search
    # lists=100 is a good default; tune upward as the table grows (sqrt(rows))
    op.execute("""
        CREATE INDEX IF NOT EXISTS embeddings_embedding_cosine_idx
        ON embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
