"""Add revenue_dot_corporate table

Revision ID: add_revenue_dot_corporate_001
Revises: 0b33abb2a8e9
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_revenue_dot_corporate_001'
down_revision = 'c7f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection
    conn = op.get_bind()
    inspector = inspect(conn)
    table_exists = 'revenue_dot_corporate' in inspector.get_table_names()
    
    if table_exists:
        # Table exists, check if year column exists
        columns = [col['name'] for col in inspector.get_columns('revenue_dot_corporate')]
        if 'year' not in columns:
            # Add year column - first add as nullable
            op.add_column('revenue_dot_corporate',
                          sa.Column('year', sa.Integer(), nullable=True))
            # Update existing rows to have current year
            op.execute("UPDATE revenue_dot_corporate SET year = EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER")
            # Now make it NOT NULL
            op.alter_column('revenue_dot_corporate', 'year', nullable=False)
            # Create index
            op.create_index(op.f('ix_revenue_dot_corporate_year'),
                          'revenue_dot_corporate', ['year'], unique=False)
        return
    
    # Create revenue_dot_corporate table
    op.create_table('revenue_dot_corporate',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('file_upload_id', sa.Integer(), nullable=True),
                    sa.Column('dot_id', sa.Integer(), nullable=True),
                    sa.Column('dot_name', sa.String(length=200), nullable=False),
                    sa.Column('year', sa.Integer(), nullable=False),
                    sa.Column('january', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('february', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('march', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('april', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('may', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('june', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('july', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('august', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('september', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('october', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('november', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('december', sa.Numeric(precision=15, scale=2), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_revenue_dot_corporate_id'),
                    'revenue_dot_corporate', ['id'], unique=False)
    op.create_index(op.f('ix_revenue_dot_corporate_file_upload_id'),
                    'revenue_dot_corporate', ['file_upload_id'], unique=False)
    op.create_index(op.f('ix_revenue_dot_corporate_dot_id'),
                    'revenue_dot_corporate', ['dot_id'], unique=False)
    op.create_index(op.f('ix_revenue_dot_corporate_dot_name'),
                    'revenue_dot_corporate', ['dot_name'], unique=False)
    op.create_index(op.f('ix_revenue_dot_corporate_year'),
                    'revenue_dot_corporate', ['year'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_revenue_dot_corporate_year'),
                  table_name='revenue_dot_corporate')
    op.drop_index(op.f('ix_revenue_dot_corporate_dot_name'),
                  table_name='revenue_dot_corporate')
    op.drop_index(op.f('ix_revenue_dot_corporate_dot_id'),
                  table_name='revenue_dot_corporate')
    op.drop_index(op.f('ix_revenue_dot_corporate_file_upload_id'),
                  table_name='revenue_dot_corporate')
    op.drop_index(op.f('ix_revenue_dot_corporate_id'),
                  table_name='revenue_dot_corporate')
    op.drop_table('revenue_dot_corporate')









