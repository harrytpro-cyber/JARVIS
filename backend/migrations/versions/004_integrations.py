"""integrations table (OAuth tokens chiffrés)

Revision ID: 004
Revises: 003
Create Date: 2026-05-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),          # google, spotify
        sa.Column("access_token", sa.Text, nullable=True),             # chiffré Fernet
        sa.Column("refresh_token", sa.Text, nullable=True),            # chiffré Fernet
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text, nullable=True),
        sa.Column("meta", JSONB, nullable=True),                       # données provider-specific
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_integrations_user_provider", "integrations", ["user_id", "provider"], unique=True)

    # Config utilisateur (ville météo, préférences briefing...)
    op.add_column("users", sa.Column("city", sa.String(100), nullable=True, server_default="Paris"))
    op.add_column("users", sa.Column("spotify_connected", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("users", sa.Column("google_connected", sa.Boolean, nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("users", "google_connected")
    op.drop_column("users", "spotify_connected")
    op.drop_column("users", "city")
    op.drop_table("integrations")
