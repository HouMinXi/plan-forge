"""Create llm_cache table.

Revision ID: 0001_llm_cache
Revises:
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_llm_cache"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("ttl_class", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_llm_cache_expires_at", "llm_cache", ["expires_at"])
    op.create_index(
        "idx_llm_cache_provider_model", "llm_cache", ["provider", "model"]
    )


def downgrade() -> None:
    op.drop_index("idx_llm_cache_provider_model", table_name="llm_cache")
    op.drop_index("idx_llm_cache_expires_at", table_name="llm_cache")
    op.drop_table("llm_cache")
