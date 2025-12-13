"""merge_anomaly_fields_with_heads

Revision ID: 252155891fc9
Revises: add_anomaly_fields_001, 6a7e8f9d0c1b, b2c3d4e5f6g7
Create Date: 2025-12-13 15:55:41.006028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '252155891fc9'
down_revision: Union[str, None] = ('add_anomaly_fields_001', '6a7e8f9d0c1b', 'b2c3d4e5f6g7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
