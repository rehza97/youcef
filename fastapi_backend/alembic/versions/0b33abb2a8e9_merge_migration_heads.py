"""Merge migration heads

Revision ID: 0b33abb2a8e9
Revises: 5g9e6f3d2b95, revenue_module_001
Create Date: 2025-11-11 10:10:35.169110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b33abb2a8e9'
down_revision: Union[str, None] = ('5g9e6f3d2b95', 'revenue_module_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
