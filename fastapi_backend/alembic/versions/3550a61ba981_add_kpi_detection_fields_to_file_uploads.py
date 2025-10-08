"""add_kpi_detection_fields_to_file_uploads

Revision ID: 3550a61ba981
Revises: bccabf43e697
Create Date: 2025-10-08 00:50:03.934722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3550a61ba981'
down_revision: Union[str, None] = 'bccabf43e697'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add detected_kpi_type column
    op.add_column('file_uploads', sa.Column(
        'detected_kpi_type', sa.String(length=100), nullable=True))

    # Add detection_confidence column
    op.add_column('file_uploads', sa.Column(
        'detection_confidence', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove detection_confidence column
    op.drop_column('file_uploads', 'detection_confidence')

    # Remove detected_kpi_type column
    op.drop_column('file_uploads', 'detected_kpi_type')
