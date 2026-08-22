"""add chunk_strategy to document

Revision ID: d5e0f4231c6a
Revises: b3a8f2c19d4e
Create Date: 2026-06-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision: str = "d5e0f4231c6a"
down_revision: str = "b3a8f2c19d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document",
        sa.Column("chunk_strategy", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document", "chunk_strategy")
