"""Add revenue module tables

Revision ID: revenue_module_001
Revises: fd3d43215e25
Create Date: 2025-01-10 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'revenue_module_001'
down_revision = '3550a61ba981'
branch_labels = None
depends_on = None


def upgrade():
    # Create account_descriptions table
    op.create_table('account_descriptions',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('file_upload_id', sa.Integer(), nullable=True),
                    sa.Column('cpt_comptable', sa.String(
                        length=100), nullable=False),
                    sa.Column('description_cpt_comptable',
                              sa.String(length=500), nullable=True),
                    sa.Column('aut_bdg', sa.String(length=100), nullable=True),
                    sa.Column('aut_imp', sa.String(length=100), nullable=True),
                    sa.Column('type_cpte', sa.String(
                        length=100), nullable=True),
                    sa.Column('auxil', sa.String(length=100), nullable=True),
                    sa.Column('let', sa.String(length=100), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['file_upload_id'], [
                                            'file_uploads.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_account_descriptions_id'),
                    'account_descriptions', ['id'], unique=False)
    op.create_index(op.f('ix_account_descriptions_cpt_comptable'),
                    'account_descriptions', ['cpt_comptable'], unique=True)
    op.create_index(op.f('ix_account_descriptions_file_upload_id'),
                    'account_descriptions', ['file_upload_id'], unique=False)
    op.create_index(op.f('ix_account_descriptions_type_cpte'),
                    'account_descriptions', ['type_cpte'], unique=False)

    # Create revenue_objectives table
    op.create_table('revenue_objectives',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('file_upload_id', sa.Integer(), nullable=True),
                    sa.Column('dot_id', sa.Integer(), nullable=True),
                    sa.Column('dot_name', sa.String(
                        length=200), nullable=False),
                    sa.Column('objectif_ca', sa.Numeric(
                        precision=15, scale=2), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
                    sa.ForeignKeyConstraint(['file_upload_id'], [
                                            'file_uploads.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_revenue_objectives_id'),
                    'revenue_objectives', ['id'], unique=False)
    op.create_index(op.f('ix_revenue_objectives_dot_id'),
                    'revenue_objectives', ['dot_id'], unique=False)
    op.create_index(op.f('ix_revenue_objectives_dot_name'),
                    'revenue_objectives', ['dot_name'], unique=False)
    op.create_index(op.f('ix_revenue_objectives_file_upload_id'),
                    'revenue_objectives', ['file_upload_id'], unique=False)

    # Create revenue_anomalies table
    op.create_table('revenue_anomalies',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('file_upload_id', sa.Integer(), nullable=True),
                    sa.Column('org_name', sa.String(
                        length=200), nullable=True),
                    sa.Column('n_fact', sa.String(length=100), nullable=True),
                    sa.Column('cpt_comptable', sa.String(
                        length=100), nullable=True),
                    sa.Column('description_ligne_de_produit',
                              sa.Text(), nullable=True),
                    sa.Column('anomaly_type', sa.String(
                        length=100), nullable=True),
                    sa.Column('anomaly_reason', sa.Text(), nullable=True),
                    sa.Column('original_data', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['file_upload_id'], [
                                            'file_uploads.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_revenue_anomalies_id'),
                    'revenue_anomalies', ['id'], unique=False)
    op.create_index(op.f('ix_revenue_anomalies_file_upload_id'),
                    'revenue_anomalies', ['file_upload_id'], unique=False)
    op.create_index(op.f('ix_revenue_anomalies_org_name'),
                    'revenue_anomalies', ['org_name'], unique=False)
    op.create_index(op.f('ix_revenue_anomalies_n_fact'),
                    'revenue_anomalies', ['n_fact'], unique=False)
    op.create_index(op.f('ix_revenue_anomalies_cpt_comptable'),
                    'revenue_anomalies', ['cpt_comptable'], unique=False)

    # Create revenue_journal table
    op.create_table('revenue_journal',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('file_upload_id', sa.Integer(), nullable=True),
                    sa.Column('dot_id', sa.Integer(), nullable=True),
                    sa.Column('org_name', sa.String(
                        length=200), nullable=True),
                    sa.Column('origine', sa.String(length=100), nullable=True),
                    sa.Column('n_fact', sa.String(length=100), nullable=True),
                    sa.Column('typ_fact', sa.String(
                        length=100), nullable=True),
                    sa.Column('date_fact', sa.Date(), nullable=True),
                    sa.Column('n_client', sa.String(
                        length=100), nullable=True),
                    sa.Column('client', sa.String(length=255), nullable=True),
                    sa.Column('delai_paie', sa.String(
                        length=100), nullable=True),
                    sa.Column('devise', sa.String(length=20), nullable=True),
                    sa.Column('obj_fact', sa.Text(), nullable=True),
                    sa.Column('cpt_comptable', sa.String(
                        length=100), nullable=True),
                    sa.Column('date_facture_gl', sa.Date(), nullable=True),
                    sa.Column('date_gl', sa.Date(), nullable=True),
                    sa.Column('periode_de_facturation',
                              sa.String(length=100), nullable=True),
                    sa.Column('reference', sa.String(
                        length=255), nullable=True),
                    sa.Column('termine_flag', sa.Boolean(), nullable=True),
                    sa.Column('tax_amount', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('creer_par', sa.String(
                        length=100), nullable=True),
                    sa.Column('n_ligne', sa.String(length=100), nullable=True),
                    sa.Column('description_ligne_de_produit',
                              sa.Text(), nullable=True),
                    sa.Column('uom', sa.String(length=50), nullable=True),
                    sa.Column('qte', sa.Numeric(
                        precision=15, scale=4), nullable=True),
                    sa.Column('prix_uni', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('taux_change', sa.Numeric(
                        precision=15, scale=6), nullable=True),
                    sa.Column('mnt_ht', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('tax', sa.String(length=50), nullable=True),
                    sa.Column('mnt_tax', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('mnt_ttc', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('memo_line_id', sa.String(
                        length=100), nullable=True),
                    sa.Column('chiffre_aff_exe_dzd', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('tva', sa.Numeric(
                        precision=10, scale=4), nullable=True),
                    sa.Column('chiffre_aff_exe_dzd_ttc', sa.Numeric(
                        precision=15, scale=2), nullable=True),
                    sa.Column('taux_realisation_ca', sa.Numeric(
                        precision=10, scale=4), nullable=True),
                    sa.Column('account_description_id',
                              sa.Integer(), nullable=True),
                    sa.Column('revenue_objective_id',
                              sa.Integer(), nullable=True),
                    sa.Column('is_anomaly', sa.Boolean(), nullable=True),
                    sa.Column('anomaly_reason', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['account_description_id'], [
                        'account_descriptions.id'], ),
                    sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
                    sa.ForeignKeyConstraint(['file_upload_id'], [
                                            'file_uploads.id'], ),
                    sa.ForeignKeyConstraint(['revenue_objective_id'], [
                        'revenue_objectives.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_revenue_journal_id'),
                    'revenue_journal', ['id'], unique=False)
    op.create_index(op.f('ix_revenue_journal_file_upload_id'),
                    'revenue_journal', ['file_upload_id'], unique=False)
    op.create_index(op.f('ix_revenue_journal_dot_id'),
                    'revenue_journal', ['dot_id'], unique=False)
    op.create_index(op.f('ix_revenue_journal_org_name'),
                    'revenue_journal', ['org_name'], unique=False)
    op.create_index(op.f('ix_revenue_journal_n_fact'),
                    'revenue_journal', ['n_fact'], unique=False)
    op.create_index(op.f('ix_revenue_journal_typ_fact'),
                    'revenue_journal', ['typ_fact'], unique=False)
    op.create_index(op.f('ix_revenue_journal_date_fact'),
                    'revenue_journal', ['date_fact'], unique=False)
    op.create_index(op.f('ix_revenue_journal_n_client'),
                    'revenue_journal', ['n_client'], unique=False)
    op.create_index(op.f('ix_revenue_journal_date_gl'),
                    'revenue_journal', ['date_gl'], unique=False)
    op.create_index(op.f('ix_revenue_journal_cpt_comptable'),
                    'revenue_journal', ['cpt_comptable'], unique=False)
    op.create_index(op.f('ix_revenue_journal_chiffre_aff_exe_dzd'),
                    'revenue_journal', ['chiffre_aff_exe_dzd'], unique=False)
    op.create_index(op.f('ix_revenue_journal_taux_realisation_ca'),
                    'revenue_journal', ['taux_realisation_ca'], unique=False)
    op.create_index(op.f('ix_revenue_journal_is_anomaly'),
                    'revenue_journal', ['is_anomaly'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_revenue_journal_is_anomaly'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_taux_realisation_ca'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_chiffre_aff_exe_dzd'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_cpt_comptable'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_date_gl'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_n_client'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_date_fact'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_typ_fact'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_n_fact'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_org_name'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_dot_id'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_file_upload_id'),
                  table_name='revenue_journal')
    op.drop_index(op.f('ix_revenue_journal_id'), table_name='revenue_journal')
    op.drop_table('revenue_journal')

    op.drop_index(op.f('ix_revenue_anomalies_cpt_comptable'),
                  table_name='revenue_anomalies')
    op.drop_index(op.f('ix_revenue_anomalies_n_fact'),
                  table_name='revenue_anomalies')
    op.drop_index(op.f('ix_revenue_anomalies_org_name'),
                  table_name='revenue_anomalies')
    op.drop_index(op.f('ix_revenue_anomalies_file_upload_id'),
                  table_name='revenue_anomalies')
    op.drop_index(op.f('ix_revenue_anomalies_id'),
                  table_name='revenue_anomalies')
    op.drop_table('revenue_anomalies')

    op.drop_index(op.f('ix_revenue_objectives_file_upload_id'),
                  table_name='revenue_objectives')
    op.drop_index(op.f('ix_revenue_objectives_dot_name'),
                  table_name='revenue_objectives')
    op.drop_index(op.f('ix_revenue_objectives_dot_id'),
                  table_name='revenue_objectives')
    op.drop_index(op.f('ix_revenue_objectives_id'),
                  table_name='revenue_objectives')
    op.drop_table('revenue_objectives')

    op.drop_index(op.f('ix_account_descriptions_type_cpte'),
                  table_name='account_descriptions')
    op.drop_index(op.f('ix_account_descriptions_file_upload_id'),
                  table_name='account_descriptions')
    op.drop_index(op.f('ix_account_descriptions_cpt_comptable'),
                  table_name='account_descriptions')
    op.drop_index(op.f('ix_account_descriptions_id'),
                  table_name='account_descriptions')
    op.drop_table('account_descriptions')
