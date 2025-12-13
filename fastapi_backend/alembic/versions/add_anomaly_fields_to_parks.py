"""add_anomaly_fields_to_parks

Revision ID: add_anomaly_fields_001
Revises: 0b33abb2a8e9
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_anomaly_fields_001'
down_revision = '0b33abb2a8e9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add anomaly detection fields to parks and parks_2b tables
    Create park_anomalies table for storing anomaly records
    """
    # Add anomaly fields to parks table
    op.add_column('parks', sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('parks', sa.Column('anomaly_reason', sa.Text(), nullable=True))
    
    # Create index on is_anomaly for faster filtering
    op.create_index('ix_parks_is_anomaly', 'parks', ['is_anomaly'], unique=False)
    
    # Add anomaly fields to parks_2b table
    op.add_column('parks_2b', sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('parks_2b', sa.Column('anomaly_reason', sa.Text(), nullable=True))
    
    # Create index on is_anomaly for faster filtering
    op.create_index('ix_parks_2b_is_anomaly', 'parks_2b', ['is_anomaly'], unique=False)
    
    # Create park_anomalies table
    op.create_table(
        'park_anomalies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('actel_code', sa.String(length=100), nullable=True),
        sa.Column('customer_code', sa.String(length=100), nullable=True),
        sa.Column('service_number', sa.String(length=100), nullable=True),
        sa.Column('customer_l3_code', sa.String(length=100), nullable=True),
        sa.Column('telecom_type', sa.String(length=100), nullable=True),
        sa.Column('offer_name', sa.String(length=255), nullable=True),
        sa.Column('anomaly_type', sa.String(length=100), nullable=False, server_default='Anomalie Parc NGBSS'),
        sa.Column('anomaly_reason', sa.Text(), nullable=True),
        sa.Column('original_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for park_anomalies table
    op.create_index('ix_park_anomalies_id', 'park_anomalies', ['id'], unique=False)
    op.create_index('ix_park_anomalies_file_upload_id', 'park_anomalies', ['file_upload_id'], unique=False)
    op.create_index('ix_park_anomalies_dot_id', 'park_anomalies', ['dot_id'], unique=False)
    op.create_index('ix_park_anomalies_actel_code', 'park_anomalies', ['actel_code'], unique=False)
    op.create_index('ix_park_anomalies_customer_code', 'park_anomalies', ['customer_code'], unique=False)
    op.create_index('ix_park_anomalies_service_number', 'park_anomalies', ['service_number'], unique=False)
    op.create_index('ix_park_anomalies_customer_l3_code', 'park_anomalies', ['customer_l3_code'], unique=False)
    op.create_index('ix_park_anomalies_telecom_type', 'park_anomalies', ['telecom_type'], unique=False)
    op.create_index('ix_park_anomalies_offer_name', 'park_anomalies', ['offer_name'], unique=False)


def downgrade():
    """
    Remove anomaly fields and park_anomalies table
    """
    # Drop park_anomalies table and indexes
    op.drop_index('ix_park_anomalies_offer_name', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_telecom_type', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_customer_l3_code', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_service_number', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_customer_code', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_actel_code', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_dot_id', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_file_upload_id', table_name='park_anomalies')
    op.drop_index('ix_park_anomalies_id', table_name='park_anomalies')
    op.drop_table('park_anomalies')
    
    # Remove anomaly fields from parks_2b table
    op.drop_index('ix_parks_2b_is_anomaly', table_name='parks_2b')
    op.drop_column('parks_2b', 'anomaly_reason')
    op.drop_column('parks_2b', 'is_anomaly')
    
    # Remove anomaly fields from parks table
    op.drop_index('ix_parks_is_anomaly', table_name='parks')
    op.drop_column('parks', 'anomaly_reason')
    op.drop_column('parks', 'is_anomaly')

