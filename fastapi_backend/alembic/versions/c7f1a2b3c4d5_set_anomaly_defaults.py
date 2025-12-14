"""set_anomaly_defaults

Revision ID: c7f1a2b3c4d5
Revises: 252155891fc9
Create Date: 2025-12-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7f1a2b3c4d5"
down_revision: Union[str, None] = "252155891fc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure inserts that omit the column don't violate NOT NULL
    op.execute("UPDATE parks SET is_anomaly = FALSE WHERE is_anomaly IS NULL")
    op.execute("UPDATE parks_2b SET is_anomaly = FALSE WHERE is_anomaly IS NULL")

    op.alter_column(
        "parks",
        "is_anomaly",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.alter_column(
        "parks_2b",
        "is_anomaly",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.alter_column(
        "parks",
        "is_anomaly",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )
    op.alter_column(
        "parks_2b",
        "is_anomaly",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )

