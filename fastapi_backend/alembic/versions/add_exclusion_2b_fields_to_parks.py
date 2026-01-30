"""create_parks_2b_table_and_migrate_data

Revision ID: 6a7e8f9d0c1b
Revises: add_module_to_dots
Create Date: 2025-12-12 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6a7e8f9d0c1b'
down_revision = 'add_module_to_dots'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create parks_2b table and migrate records where customer_l1_code = '2B'
    """
    # Create parks_2b table with same structure as parks table
    op.create_table(
        'parks_2b',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_upload_id', sa.Integer(), nullable=True),
        sa.Column('extraction_date', sa.Date(), nullable=True),
        sa.Column('dot_id', sa.Integer(), nullable=True),
        sa.Column('actel_code', sa.String(length=100), nullable=True),
        sa.Column('customer_l1_code', sa.String(length=100), nullable=True),
        sa.Column('customer_l1_description', sa.String(length=255), nullable=True),
        sa.Column('customer_l2_code', sa.String(length=100), nullable=True),
        sa.Column('customer_l2_description', sa.String(length=255), nullable=True),
        sa.Column('customer_l3_code', sa.String(length=100), nullable=True),
        sa.Column('customer_l3_description', sa.String(length=255), nullable=True),
        sa.Column('telecom_type', sa.String(length=100), nullable=True),
        sa.Column('offer_type', sa.String(length=100), nullable=True),
        sa.Column('offer_name', sa.String(length=255), nullable=True),
        sa.Column('rental_fees', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('customer_code', sa.String(length=100), nullable=True),
        sa.Column('service_number', sa.String(length=100), nullable=True),
        sa.Column('related_service_number', sa.String(length=100), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('subscriber_status', sa.String(length=100), nullable=True),
        sa.Column('status_date', sa.Date(), nullable=True),
        sa.Column('creation_date', sa.Date(), nullable=True),
        sa.Column('active_date', sa.Date(), nullable=True),
        sa.Column('csr_name', sa.String(length=255), nullable=True),
        sa.Column('department_name', sa.String(length=255), nullable=True),
        sa.Column('state', sa.String(length=200), nullable=True),
        sa.Column('area', sa.String(length=200), nullable=True),
        sa.Column('town', sa.String(length=200), nullable=True),
        sa.Column('grid', sa.String(length=200), nullable=True),
        sa.Column('street', sa.String(length=500), nullable=True),
        sa.Column('street_number', sa.String(length=100), nullable=True),
        sa.Column('building_no', sa.String(length=100), nullable=True),
        sa.Column('unit', sa.String(length=100), nullable=True),
        sa.Column('floor', sa.String(length=100), nullable=True),
        sa.Column('house_no', sa.String(length=100), nullable=True),
        sa.Column('additional_address_info', sa.Text(), nullable=True),
        sa.Column('customer_full_name', sa.String(length=500), nullable=True),
        sa.Column('province', sa.String(length=200), nullable=True),
        sa.Column('district', sa.String(length=200), nullable=True),
        sa.Column('city', sa.String(length=200), nullable=True),
        sa.Column('postal_code', sa.String(length=50), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('iccid', sa.String(length=100), nullable=True),
        sa.Column('imsi', sa.String(length=100), nullable=True),
        sa.Column('contact_number', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
        sa.ForeignKeyConstraint(['file_upload_id'], ['file_uploads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for parks_2b table
    op.create_index(op.f('ix_parks_2b_id'), 'parks_2b', ['id'], unique=False)
    op.create_index(op.f('ix_parks_2b_file_upload_id'), 'parks_2b', ['file_upload_id'], unique=False)
    op.create_index(op.f('ix_parks_2b_extraction_date'), 'parks_2b', ['extraction_date'], unique=False)
    op.create_index(op.f('ix_parks_2b_dot_id'), 'parks_2b', ['dot_id'], unique=False)
    op.create_index(op.f('ix_parks_2b_actel_code'), 'parks_2b', ['actel_code'], unique=False)
    op.create_index(op.f('ix_parks_2b_customer_l1_code'), 'parks_2b', ['customer_l1_code'], unique=False)
    op.create_index(op.f('ix_parks_2b_customer_l2_code'), 'parks_2b', ['customer_l2_code'], unique=False)
    op.create_index(op.f('ix_parks_2b_customer_l3_code'), 'parks_2b', ['customer_l3_code'], unique=False)
    op.create_index(op.f('ix_parks_2b_telecom_type'), 'parks_2b', ['telecom_type'], unique=False)
    op.create_index(op.f('ix_parks_2b_offer_type'), 'parks_2b', ['offer_type'], unique=False)
    op.create_index(op.f('ix_parks_2b_offer_name'), 'parks_2b', ['offer_name'], unique=False)
    op.create_index(op.f('ix_parks_2b_customer_code'), 'parks_2b', ['customer_code'], unique=False)
    op.create_index(op.f('ix_parks_2b_service_number'), 'parks_2b', ['service_number'], unique=False)
    op.create_index(op.f('ix_parks_2b_subscriber_status'), 'parks_2b', ['subscriber_status'], unique=False)
    op.create_index(op.f('ix_parks_2b_state'), 'parks_2b', ['state'], unique=False)
    op.create_index(op.f('ix_parks_2b_area'), 'parks_2b', ['area'], unique=False)
    op.create_index(op.f('ix_parks_2b_town'), 'parks_2b', ['town'], unique=False)
    op.create_index(op.f('ix_parks_2b_customer_full_name'), 'parks_2b', ['customer_full_name'], unique=False)
    op.create_index(op.f('ix_parks_2b_province'), 'parks_2b', ['province'], unique=False)
    op.create_index(op.f('ix_parks_2b_district'), 'parks_2b', ['district'], unique=False)
    op.create_index(op.f('ix_parks_2b_city'), 'parks_2b', ['city'], unique=False)
    op.create_index(op.f('ix_parks_2b_iccid'), 'parks_2b', ['iccid'], unique=False)
    op.create_index(op.f('ix_parks_2b_imsi'), 'parks_2b', ['imsi'], unique=False)

    # Migrate existing 2B records from parks to parks_2b
    op.execute("""
        INSERT INTO parks_2b (
            id, file_upload_id, extraction_date, dot_id, actel_code,
            customer_l1_code, customer_l1_description,
            customer_l2_code, customer_l2_description,
            customer_l3_code, customer_l3_description,
            telecom_type, offer_type, offer_name, rental_fees,
            customer_code, service_number, related_service_number, username,
            subscriber_status, status_date, creation_date, active_date,
            csr_name, department_name,
            state, area, town, grid, street, street_number, building_no, unit, floor, house_no,
            additional_address_info,
            customer_full_name, province, district, city, postal_code,
            expiry_date, iccid, imsi, contact_number,
            created_at, updated_at
        )
        SELECT
            id, file_upload_id, extraction_date, dot_id, actel_code,
            customer_l1_code, customer_l1_description,
            customer_l2_code, customer_l2_description,
            customer_l3_code, customer_l3_description,
            telecom_type, offer_type, offer_name, rental_fees,
            customer_code, service_number, related_service_number, username,
            subscriber_status, status_date, creation_date, active_date,
            csr_name, department_name,
            state, area, town, grid, street, street_number, building_no, unit, floor, house_no,
            additional_address_info,
            customer_full_name, province, district, city, postal_code,
            expiry_date, iccid, imsi, contact_number,
            created_at, updated_at
        FROM parks
        WHERE customer_l1_code = '2B'
    """)

    # Delete migrated 2B records from parks table
    op.execute("DELETE FROM parks WHERE customer_l1_code = '2B'")

    # Remove is_exclusion_2b and exclusion_2b_reason columns if they exist
    # (These were added in the previous implementation but are no longer needed)
    try:
        op.drop_index('ix_parks_is_exclusion_2b', table_name='parks')
    except:
        pass  # Index doesn't exist

    try:
        op.drop_column('parks', 'is_exclusion_2b')
    except:
        pass  # Column doesn't exist

    try:
        op.drop_column('parks', 'exclusion_2b_reason')
    except:
        pass  # Column doesn't exist


def downgrade():
    """
    Migrate parks_2b records back to parks table and drop parks_2b table
    """
    # Migrate all parks_2b records back to parks table
    op.execute("""
        INSERT INTO parks (
            id, file_upload_id, extraction_date, dot_id, actel_code,
            customer_l1_code, customer_l1_description,
            customer_l2_code, customer_l2_description,
            customer_l3_code, customer_l3_description,
            telecom_type, offer_type, offer_name, rental_fees,
            customer_code, service_number, related_service_number, username,
            subscriber_status, status_date, creation_date, active_date,
            csr_name, department_name,
            state, area, town, grid, street, street_number, building_no, unit, floor, house_no,
            additional_address_info,
            customer_full_name, province, district, city, postal_code,
            expiry_date, iccid, imsi, contact_number,
            created_at, updated_at
        )
        SELECT
            id, file_upload_id, extraction_date, dot_id, actel_code,
            customer_l1_code, customer_l1_description,
            customer_l2_code, customer_l2_description,
            customer_l3_code, customer_l3_description,
            telecom_type, offer_type, offer_name, rental_fees,
            customer_code, service_number, related_service_number, username,
            subscriber_status, status_date, creation_date, active_date,
            csr_name, department_name,
            state, area, town, grid, street, street_number, building_no, unit, floor, house_no,
            additional_address_info,
            customer_full_name, province, district, city, postal_code,
            expiry_date, iccid, imsi, contact_number,
            created_at, updated_at
        FROM parks_2b
    """)

    # Drop all indexes
    op.drop_index(op.f('ix_parks_2b_imsi'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_iccid'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_city'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_district'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_province'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_customer_full_name'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_town'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_area'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_state'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_subscriber_status'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_service_number'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_customer_code'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_offer_name'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_offer_type'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_telecom_type'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_customer_l3_code'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_customer_l2_code'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_customer_l1_code'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_actel_code'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_dot_id'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_extraction_date'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_file_upload_id'), table_name='parks_2b')
    op.drop_index(op.f('ix_parks_2b_id'), table_name='parks_2b')

    # Drop parks_2b table
    op.drop_table('parks_2b')













