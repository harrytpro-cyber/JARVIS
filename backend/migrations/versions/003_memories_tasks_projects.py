"""memories, tasks, projects, morning_briefings

Revision ID: 003
Revises: 002
Create Date: 2026-05-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Projets ───────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    # ── Tâches ────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="3"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_status_priority", "tasks", ["status", "priority"])

    # ── Morning Briefings ─────────────────────────────────
    op.create_table(
        "morning_briefings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("briefing_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_morning_briefings_user_date", "morning_briefings", ["user_id", "briefing_date"], unique=True)

    # ── Memories (pgvector) ───────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        # vecteur 1536 dims (text-embedding-3-small) ou 768 (nomic-embed)
        sa.Column("embedding", sa.Text, nullable=True),   # stocké via pgvector raw SQL
        sa.Column("memory_type", sa.String(50), nullable=False, server_default="fact"),
        sa.Column("importance", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("access_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_accessed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    # Ajouter la colonne vector avec pgvector directement en SQL
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("""
        CREATE INDEX ix_memories_embedding_hnsw
        ON memories
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_type", "memories", ["memory_type"])

    # ── RLS sur memories ──────────────────────────────────
    op.execute("ALTER TABLE memories ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY memories_isolation ON memories
        USING (user_id::text = current_setting('app.current_user_id', true))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memories_isolation ON memories")
    op.execute("ALTER TABLE memories DISABLE ROW LEVEL SECURITY")
    op.drop_table("memories")
    op.drop_table("morning_briefings")
    op.drop_table("tasks")
    op.drop_table("projects")
