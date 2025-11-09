"""add_encaissement_ar_dot_tables

Revision ID: 4f8d5e2c1a94
Revises: 3550a61ba981
Create Date: 2025-10-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4f8d5e2c1a94'
down_revision: Union[str, None] = '3550a61ba981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create encaissement_ar_dot table
    op.create_table(
        'encaissement_ar_dot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('organisation', sa.String(length=200), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('n_fact', sa.Integer(), nullable=True),
        sa.Column('typ_fact', sa.String(length=50), nullable=True),
        sa.Column('date_fact', sa.Date(), nullable=True),
        sa.Column('mois', sa.String(length=7), nullable=True),
        sa.Column('client', sa.String(length=255), nullable=True),
        sa.Column('n_client', sa.String(length=100), nullable=True),
        sa.Column('obj_fact', sa.Text(), nullable=True),
        sa.Column('periode', sa.String(length=255), nullable=True),
        sa.Column('ref', sa.String(length=255), nullable=True),
        sa.Column('termine_flag', sa.String(length=10), nullable=True),
        sa.Column('creer_par', sa.String(length=100), nullable=True),
        sa.Column('montant_ht', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('montant_taxe', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('montant_ttc', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('chiffre_aff_exe', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('encaissement', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('n_rglt', sa.String(length=100), nullable=True),
        sa.Column('date_rglt', sa.Date(), nullable=True),
        sa.Column('facture_avoir_annulation', sa.String(length=255), nullable=True),
        sa.Column('taux_encaissement', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('montant_restant', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('composite_key', sa.String(length=500), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('anomaly_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for encaissement_ar_dot
    op.create_index('ix_encaissement_ar_dot_file_upload_id', 'encaissement_ar_dot', ['file_upload_id'])
    op.create_index('ix_encaissement_ar_dot_dot_id', 'encaissement_ar_dot', ['dot_id'])
    op.create_index('ix_encaissement_ar_dot_organisation', 'encaissement_ar_dot', ['organisation'])
    op.create_index('ix_encaissement_ar_dot_source', 'encaissement_ar_dot', ['source'])
    op.create_index('ix_encaissement_ar_dot_n_fact', 'encaissement_ar_dot', ['n_fact'])
    op.create_index('ix_encaissement_ar_dot_typ_fact', 'encaissement_ar_dot', ['typ_fact'])
    op.create_index('ix_encaissement_ar_dot_date_fact', 'encaissement_ar_dot', ['date_fact'])
    op.create_index('ix_encaissement_ar_dot_mois', 'encaissement_ar_dot', ['mois'])
    op.create_index('ix_encaissement_ar_dot_client', 'encaissement_ar_dot', ['client'])
    op.create_index('ix_encaissement_ar_dot_n_client', 'encaissement_ar_dot', ['n_client'])
    op.create_index('ix_encaissement_ar_dot_montant_ttc', 'encaissement_ar_dot', ['montant_ttc'])
    op.create_index('ix_encaissement_ar_dot_encaissement', 'encaissement_ar_dot', ['encaissement'])
    op.create_index('ix_encaissement_ar_dot_n_rglt', 'encaissement_ar_dot', ['n_rglt'])
    op.create_index('ix_encaissement_ar_dot_date_rglt', 'encaissement_ar_dot', ['date_rglt'])
    op.create_index('ix_encaissement_ar_dot_taux_encaissement', 'encaissement_ar_dot', ['taux_encaissement'])
    op.create_index('ix_encaissement_ar_dot_composite_key', 'encaissement_ar_dot', ['composite_key'])
    op.create_index('ix_encaissement_ar_dot_is_duplicate', 'encaissement_ar_dot', ['is_duplicate'])
    op.create_index('ix_encaissement_ar_dot_is_anomaly', 'encaissement_ar_dot', ['is_anomaly'])
    op.create_index('ix_encaissement_ar_dot_created_at', 'encaissement_ar_dot', ['created_at'])

    # Create encaissement_anomalies table
    op.create_table(
        'encaissement_anomalies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('organisation', sa.String(length=200), nullable=True),
        sa.Column('n_fact', sa.Integer(), nullable=True),
        sa.Column('typ_fact', sa.String(length=50), nullable=True),
        sa.Column('montant_ttc', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('encaissement', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('anomaly_type', sa.String(length=100), nullable=True),
        sa.Column('anomaly_reason', sa.Text(), nullable=True),
        sa.Column('original_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for encaissement_anomalies
    op.create_index('ix_encaissement_anomalies_file_upload_id', 'encaissement_anomalies', ['file_upload_id'])
    op.create_index('ix_encaissement_anomalies_dot_id', 'encaissement_anomalies', ['dot_id'])
    op.create_index('ix_encaissement_anomalies_organisation', 'encaissement_anomalies', ['organisation'])
    op.create_index('ix_encaissement_anomalies_n_fact', 'encaissement_anomalies', ['n_fact'])
    op.create_index('ix_encaissement_anomalies_anomaly_type', 'encaissement_anomalies', ['anomaly_type'])

    # Create encaissement_aggregate_views table
    op.create_table(
        'encaissement_aggregate_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('view_type', sa.String(length=50), nullable=False),
        sa.Column('mois', sa.String(length=7), nullable=True),
        sa.Column('organisation', sa.String(length=200), nullable=True),
        sa.Column('total_montant_ttc', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_encaissement', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_montant_restant', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('taux_encaissement', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('nombre_factures', sa.Integer(), nullable=True),
        sa.Column('percentage', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for encaissement_aggregate_views
    op.create_index('ix_encaissement_aggregate_views_file_upload_id', 'encaissement_aggregate_views', ['file_upload_id'])
    op.create_index('ix_encaissement_aggregate_views_dot_id', 'encaissement_aggregate_views', ['dot_id'])
    op.create_index('ix_encaissement_aggregate_views_view_type', 'encaissement_aggregate_views', ['view_type'])
    op.create_index('ix_encaissement_aggregate_views_mois', 'encaissement_aggregate_views', ['mois'])
    op.create_index('ix_encaissement_aggregate_views_organisation', 'encaissement_aggregate_views', ['organisation'])


def downgrade() -> None:
    # Drop indexes for encaissement_aggregate_views
    op.drop_index('ix_encaissement_aggregate_views_organisation', table_name='encaissement_aggregate_views')
    op.drop_index('ix_encaissement_aggregate_views_mois', table_name='encaissement_aggregate_views')
    op.drop_index('ix_encaissement_aggregate_views_view_type', table_name='encaissement_aggregate_views')
    op.drop_index('ix_encaissement_aggregate_views_dot_id', table_name='encaissement_aggregate_views')
    op.drop_index('ix_encaissement_aggregate_views_file_upload_id', table_name='encaissement_aggregate_views')

    # Drop encaissement_aggregate_views table
    op.drop_table('encaissement_aggregate_views')

    # Drop indexes for encaissement_anomalies
    op.drop_index('ix_encaissement_anomalies_anomaly_type', table_name='encaissement_anomalies')
    op.drop_index('ix_encaissement_anomalies_n_fact', table_name='encaissement_anomalies')
    op.drop_index('ix_encaissement_anomalies_organisation', table_name='encaissement_anomalies')
    op.drop_index('ix_encaissement_anomalies_dot_id', table_name='encaissement_anomalies')
    op.drop_index('ix_encaissement_anomalies_file_upload_id', table_name='encaissement_anomalies')

    # Drop encaissement_anomalies table
    op.drop_table('encaissement_anomalies')

    # Drop indexes for encaissement_ar_dot
    op.drop_index('ix_encaissement_ar_dot_created_at', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_is_anomaly', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_is_duplicate', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_composite_key', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_taux_encaissement', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_date_rglt', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_n_rglt', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_encaissement', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_montant_ttc', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_n_client', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_client', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_mois', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_date_fact', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_typ_fact', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_n_fact', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_source', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_organisation', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_dot_id', table_name='encaissement_ar_dot')
    op.drop_index('ix_encaissement_ar_dot_file_upload_id', table_name='encaissement_ar_dot')

    # Drop encaissement_ar_dot table
    op.drop_table('encaissement_ar_dot')
