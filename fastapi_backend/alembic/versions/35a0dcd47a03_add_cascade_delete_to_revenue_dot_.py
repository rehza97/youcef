"""add_cascade_delete_to_revenue_dot_corporate

Revision ID: 35a0dcd47a03
Revises: add_revenue_dot_corporate_001
Create Date: 2025-12-15 18:12:24.833839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35a0dcd47a03'
down_revision: Union[str, None] = 'add_revenue_dot_corporate_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing foreign key constraint
    op.drop_constraint(
        'revenue_dot_corporate_file_upload_id_fkey',
        'revenue_dot_corporate',
        type_='foreignkey'
    )
    
    # Recreate with CASCADE delete
    op.create_foreign_key(
        'revenue_dot_corporate_file_upload_id_fkey',
        'revenue_dot_corporate',
        'file_uploads',
        ['file_upload_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop CASCADE constraint
    op.drop_constraint(
        'revenue_dot_corporate_file_upload_id_fkey',
        'revenue_dot_corporate',
        type_='foreignkey'
    )
    
    # Recreate without CASCADE
    op.create_foreign_key(
        'revenue_dot_corporate_file_upload_id_fkey',
        'revenue_dot_corporate',
        'file_uploads',
        ['file_upload_id'],
        ['id']
    )
