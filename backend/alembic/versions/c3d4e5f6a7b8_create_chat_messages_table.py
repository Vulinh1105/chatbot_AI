"""create chat messages table

Revision ID: c3d4e5f6a7b8
Revises: b7a1f8c2d4e6
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7a1f8c2d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "user",
                "system",
                name="chat_message_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "error",
                name="chat_message_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_chat_id_id",
        "chat_messages",
        ["chat_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_chat_id_id", table_name="chat_messages")
    op.drop_table("chat_messages")
