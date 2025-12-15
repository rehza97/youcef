"""fix_cascade_delete_objectifs_monthly_dot

Revision ID: 1540626b1dd7
Revises: 2374e7f93c89
Create Date: 2025-12-15 18:53:17.451720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1540626b1dd7'
down_revision: Union[str, None] = '2374e7f93c89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if constraint exists and if it has CASCADE
    # Drop existing constraint if it doesn't have CASCADE
    op.execute("""
        DO $$
        BEGIN
            -- Check if constraint exists
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'objectifs_monthly_dot_file_upload_id_fkey'
            ) THEN
                -- Drop the constraint
                ALTER TABLE objectifs_monthly_dot
                DROP CONSTRAINT objectifs_monthly_dot_file_upload_id_fkey;
                
                -- Recreate with CASCADE delete
                ALTER TABLE objectifs_monthly_dot
                ADD CONSTRAINT objectifs_monthly_dot_file_upload_id_fkey
                FOREIGN KEY (file_upload_id) 
                REFERENCES file_uploads(id) 
                ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop CASCADE constraint and recreate without CASCADE (if needed)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'objectifs_monthly_dot_file_upload_id_fkey'
            ) THEN
                ALTER TABLE objectifs_monthly_dot
                DROP CONSTRAINT objectifs_monthly_dot_file_upload_id_fkey;
                
                ALTER TABLE objectifs_monthly_dot
                ADD CONSTRAINT objectifs_monthly_dot_file_upload_id_fkey
                FOREIGN KEY (file_upload_id) 
                REFERENCES file_uploads(id);
            END IF;
        END $$;
    """)
