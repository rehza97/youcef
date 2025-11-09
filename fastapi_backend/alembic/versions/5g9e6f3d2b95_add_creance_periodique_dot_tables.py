"""add_creance_periodique_dot_tables

Revision ID: 5g9e6f3d2b95
Revises: 4f8d5e2c1a94
Create Date: 2025-10-31 22:12:58.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5g9e6f3d2b95'
down_revision: Union[str, None] = '4f8d5e2c1a94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create creance_periodique_dot table
    op.create_table(
        'creance_periodique_dot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('dot', sa.String(length=200), nullable=True),
        sa.Column('actel', sa.String(length=255), nullable=True),
        sa.Column('mois', sa.String(length=2), nullable=True),
        sa.Column('annee', sa.String(length=4), nullable=True),
        sa.Column('period_key', sa.String(length=7), nullable=True),
        sa.Column('subs_status', sa.String(length=50), nullable=True),
        sa.Column('produit', sa.String(length=100), nullable=True),
        sa.Column('cust_lev1', sa.String(length=200), nullable=True),
        sa.Column('cust_lev2', sa.String(length=200), nullable=True),
        sa.Column('cust_lev3', sa.String(length=200), nullable=True),
        sa.Column('invoice_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('open_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('tax_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('invoice_amt_ht', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('dispute_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('dispute_tax_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('dispute_net_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('creance_brut', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('creance_net', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('creance_ht', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_filtered', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('filter_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for creance_periodique_dot
    op.create_index('ix_creance_periodique_dot_file_upload_id', 'creance_periodique_dot', ['file_upload_id'])
    op.create_index('ix_creance_periodique_dot_dot_id', 'creance_periodique_dot', ['dot_id'])
    op.create_index('ix_creance_periodique_dot_dot', 'creance_periodique_dot', ['dot'])
    op.create_index('ix_creance_periodique_dot_mois', 'creance_periodique_dot', ['mois'])
    op.create_index('ix_creance_periodique_dot_annee', 'creance_periodique_dot', ['annee'])
    op.create_index('ix_creance_periodique_dot_period_key', 'creance_periodique_dot', ['period_key'])
    op.create_index('ix_creance_periodique_dot_produit', 'creance_periodique_dot', ['produit'])
    op.create_index('ix_creance_periodique_dot_cust_lev1', 'creance_periodique_dot', ['cust_lev1'])
    op.create_index('ix_creance_periodique_dot_cust_lev2', 'creance_periodique_dot', ['cust_lev2'])
    op.create_index('ix_creance_periodique_dot_cust_lev3', 'creance_periodique_dot', ['cust_lev3'])
    op.create_index('ix_creance_periodique_dot_open_amt', 'creance_periodique_dot', ['open_amt'])
    op.create_index('ix_creance_periodique_dot_creance_brut', 'creance_periodique_dot', ['creance_brut'])
    op.create_index('ix_creance_periodique_dot_creance_net', 'creance_periodique_dot', ['creance_net'])
    op.create_index('ix_creance_periodique_dot_is_filtered', 'creance_periodique_dot', ['is_filtered'])
    op.create_index('ix_creance_periodique_dot_created_at', 'creance_periodique_dot', ['created_at'])

    # Create creance_aggregate_views table
    op.create_table(
        'creance_aggregate_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('view_type', sa.String(length=50), nullable=False),
        sa.Column('dot_name', sa.String(length=200), nullable=True),
        sa.Column('annee', sa.String(length=4), nullable=True),
        sa.Column('produit', sa.String(length=100), nullable=True),
        sa.Column('cust_lev2', sa.String(length=200), nullable=True),
        sa.Column('total_invoice_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_open_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_tax_amt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_invoice_amt_ht', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_creance_brut', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_creance_net', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_creance_ht', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('nombre_lignes', sa.Integer(), nullable=True),
        sa.Column('percentage', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for creance_aggregate_views
    op.create_index('ix_creance_aggregate_views_file_upload_id', 'creance_aggregate_views', ['file_upload_id'])
    op.create_index('ix_creance_aggregate_views_dot_id', 'creance_aggregate_views', ['dot_id'])
    op.create_index('ix_creance_aggregate_views_view_type', 'creance_aggregate_views', ['view_type'])
    op.create_index('ix_creance_aggregate_views_dot_name', 'creance_aggregate_views', ['dot_name'])
    op.create_index('ix_creance_aggregate_views_annee', 'creance_aggregate_views', ['annee'])
    op.create_index('ix_creance_aggregate_views_produit', 'creance_aggregate_views', ['produit'])
    op.create_index('ix_creance_aggregate_views_cust_lev2', 'creance_aggregate_views', ['cust_lev2'])


def downgrade() -> None:
    # Drop indexes for creance_aggregate_views
    op.drop_index('ix_creance_aggregate_views_cust_lev2', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_produit', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_annee', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_dot_name', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_view_type', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_dot_id', table_name='creance_aggregate_views')
    op.drop_index('ix_creance_aggregate_views_file_upload_id', table_name='creance_aggregate_views')

    # Drop creance_aggregate_views table
    op.drop_table('creance_aggregate_views')

    # Drop indexes for creance_periodique_dot
    op.drop_index('ix_creance_periodique_dot_created_at', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_is_filtered', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_creance_net', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_creance_brut', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_open_amt', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_cust_lev3', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_cust_lev2', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_cust_lev1', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_produit', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_period_key', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_annee', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_mois', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_dot', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_dot_id', table_name='creance_periodique_dot')
    op.drop_index('ix_creance_periodique_dot_file_upload_id', table_name='creance_periodique_dot')

    # Drop creance_periodique_dot table
    op.drop_table('creance_periodique_dot')
