"""create chats table

Revision ID: b7a1f8c2d4e6
Revises: 9339c043985f
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7a1f8c2d4e6"
down_revision: Union[str, Sequence[str], None] = "9339c043985f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chats_id"), "chats", ["id"], unique=False)
    op.create_index(op.f("ix_chats_owner_id"), "chats", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chats_owner_id"), table_name="chats")
    op.drop_index(op.f("ix_chats_id"), table_name="chats")
    op.drop_table("chats")
