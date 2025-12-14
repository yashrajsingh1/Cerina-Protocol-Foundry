"""Initial schema for Cerina Protocol Foundry.

Revision ID: 0001_initial
Revises: None
Create Date: 2025-12-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocol_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intent", sa.String(length=512), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latest_draft", sa.Text(), nullable=True),
        sa.Column("human_edited_draft", sa.Text(), nullable=True),
        sa.Column("final_protocol", sa.Text(), nullable=True),
        sa.Column("safety_score", sa.Float(), nullable=True),
        sa.Column("empathy_score", sa.Float(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_protocol_sessions_id",
        "protocol_sessions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_protocol_sessions_thread_id",
        "protocol_sessions",
        ["thread_id"],
        unique=True,
    )

    op.create_table(
        "draft_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("protocol_sessions.id", ondelete="CASCADE")),
        sa.Column("version_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("safety_score", sa.Float(), nullable=True),
        sa.Column("empathy_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("protocol_sessions.id", ondelete="CASCADE")),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_logs")
    op.drop_table("draft_versions")
    op.drop_index("ix_protocol_sessions_thread_id", table_name="protocol_sessions")
    op.drop_index("ix_protocol_sessions_id", table_name="protocol_sessions")
    op.drop_table("protocol_sessions")
