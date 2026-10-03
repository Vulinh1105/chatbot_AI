"""alter_documents_and_add_versions

Revision ID: b587c3589164
Revises: 
Create Date: ...
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b587c3589164'
down_revision: Union[str, None] = '7d290dbcb2b9' # giữ nguyên giá trị down_revision có sẵn trong file của bạn
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Bổ sung các cột mới vào bảng documents
    op.add_column('documents', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('documents', sa.Column('description', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('documents', sa.Column('current_version_id', sa.Integer(), nullable=True))

    # 2. Chuyển các cột file cũ thành nullable
    op.alter_column('documents', 'original_filename', existing_type=sa.String(length=255), nullable=True)
    op.alter_column('documents', 'content_type', existing_type=sa.String(length=255), nullable=True)
    op.alter_column('documents', 'size_bytes', existing_type=sa.Integer(), nullable=True)
    op.alter_column('documents', 'file_path', existing_type=sa.String(length=1024), nullable=True)


def downgrade() -> None:
    op.alter_column('documents', 'file_path', existing_type=sa.String(length=1024), nullable=False)
    op.alter_column('documents', 'size_bytes', existing_type=sa.Integer(), nullable=False)
    op.alter_column('documents', 'content_type', existing_type=sa.String(length=255), nullable=False)
    op.alter_column('documents', 'original_filename', existing_type=sa.String(length=255), nullable=False)

    op.drop_column('documents', 'current_version_id')
    op.drop_column('documents', 'is_deleted')
    op.drop_column('documents', 'description')
    op.drop_column('documents', 'title')