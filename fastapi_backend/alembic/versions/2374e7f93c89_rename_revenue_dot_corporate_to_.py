"""rename_revenue_dot_corporate_to_objectifs_monthly_dot

Revision ID: 2374e7f93c89
Revises: 35a0dcd47a03
Create Date: 2025-12-15 18:46:24.297157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2374e7f93c89'
down_revision: Union[str, None] = '35a0dcd47a03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists before renaming
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    old_table_exists = 'revenue_dot_corporate' in inspector.get_table_names()
    new_table_exists = 'objectifs_monthly_dot' in inspector.get_table_names()
    
    if new_table_exists:
        # Table already renamed, skip
        return
    
    if not old_table_exists:
        raise Exception("revenue_dot_corporate table does not exist and objectifs_monthly_dot also doesn't exist")
    
    # Rename indexes - check both old and new names exist
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_revenue_dot_corporate_id' AND tablename = 'revenue_dot_corporate') 
               AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_objectifs_monthly_dot_id') THEN
                ALTER INDEX ix_revenue_dot_corporate_id RENAME TO ix_objectifs_monthly_dot_id;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_revenue_dot_corporate_file_upload_id' AND tablename = 'revenue_dot_corporate')
               AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_objectifs_monthly_dot_file_upload_id') THEN
                ALTER INDEX ix_revenue_dot_corporate_file_upload_id RENAME TO ix_objectifs_monthly_dot_file_upload_id;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_revenue_dot_corporate_dot_id' AND tablename = 'revenue_dot_corporate')
               AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_objectifs_monthly_dot_dot_id') THEN
                ALTER INDEX ix_revenue_dot_corporate_dot_id RENAME TO ix_objectifs_monthly_dot_dot_id;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_revenue_dot_corporate_dot_name' AND tablename = 'revenue_dot_corporate')
               AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_objectifs_monthly_dot_dot_name') THEN
                ALTER INDEX ix_revenue_dot_corporate_dot_name RENAME TO ix_objectifs_monthly_dot_dot_name;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_revenue_dot_corporate_year' AND tablename = 'revenue_dot_corporate')
               AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_objectifs_monthly_dot_year') THEN
                ALTER INDEX ix_revenue_dot_corporate_year RENAME TO ix_objectifs_monthly_dot_year;
            END IF;
        END $$;
    """)
    
    # Drop and recreate foreign key constraint with new name (only if it exists)
    try:
        op.drop_constraint(
            'revenue_dot_corporate_file_upload_id_fkey',
            'revenue_dot_corporate',
            type_='foreignkey'
        )
    except Exception:
        pass  # Constraint might not exist or already renamed
    
    # Rename the table
    op.rename_table('revenue_dot_corporate', 'objectifs_monthly_dot')
    
    # Recreate foreign key constraint with new name (only if it doesn't exist)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'objectifs_monthly_dot_file_upload_id_fkey'
            ) THEN
                ALTER TABLE objectifs_monthly_dot
                ADD CONSTRAINT objectifs_monthly_dot_file_upload_id_fkey
                FOREIGN KEY (file_upload_id) REFERENCES file_uploads(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint(
        'objectifs_monthly_dot_file_upload_id_fkey',
        'objectifs_monthly_dot',
        type_='foreignkey'
    )
    
    # Rename table back
    op.rename_table('objectifs_monthly_dot', 'revenue_dot_corporate')
    
    # Recreate foreign key constraint with old name
    op.create_foreign_key(
        'revenue_dot_corporate_file_upload_id_fkey',
        'revenue_dot_corporate',
        'file_uploads',
        ['file_upload_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Rename indexes back
    op.execute("ALTER INDEX IF EXISTS ix_objectifs_monthly_dot_id RENAME TO ix_revenue_dot_corporate_id")
    op.execute("ALTER INDEX IF EXISTS ix_objectifs_monthly_dot_file_upload_id RENAME TO ix_revenue_dot_corporate_file_upload_id")
    op.execute("ALTER INDEX IF EXISTS ix_objectifs_monthly_dot_dot_id RENAME TO ix_revenue_dot_corporate_dot_id")
    op.execute("ALTER INDEX IF EXISTS ix_objectifs_monthly_dot_dot_name RENAME TO ix_revenue_dot_corporate_dot_name")
    op.execute("ALTER INDEX IF EXISTS ix_objectifs_monthly_dot_year RENAME TO ix_revenue_dot_corporate_year")
