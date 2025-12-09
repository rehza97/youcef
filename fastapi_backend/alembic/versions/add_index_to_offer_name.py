"""add_index_to_offer_name

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-09 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index to offer_name column in parks table for better query performance"""
    # Create index on offer_name column
    op.create_index(
        'ix_parks_offer_name',  # Index name
        'parks',                # Table name
        ['offer_name'],         # Column name
        unique=False            # Not unique, multiple records can have same offer_name
    )


def downgrade() -> None:
    """Remove index from offer_name column"""
    op.drop_index('ix_parks_offer_name', table_name='parks')
