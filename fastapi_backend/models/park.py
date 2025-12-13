from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Date, Boolean
from sqlalchemy.orm import relationship
from database.connection import Base


class Park(Base):
    __tablename__ = "parks"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship - track which file this park data came from
    file_upload_id = Column(Integer, ForeignKey(
        "file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="parks")

    # Extraction Date
    extraction_date = Column(Date, nullable=True, index=True)

    # DOT relationship
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="parks")

    # Actel Code
    actel_code = Column(String(100), nullable=True, index=True)

    # Customer Level 1
    customer_l1_code = Column(String(100), nullable=True, index=True)
    customer_l1_description = Column(String(255), nullable=True)

    # Customer Level 2
    customer_l2_code = Column(String(100), nullable=True, index=True)
    customer_l2_description = Column(String(255), nullable=True)

    # Customer Level 3
    customer_l3_code = Column(String(100), nullable=True, index=True)
    customer_l3_description = Column(String(255), nullable=True)

    # Telecom and Offer information
    telecom_type = Column(String(100), nullable=True, index=True)
    offer_type = Column(String(100), nullable=True, index=True)
    offer_name = Column(String(255), nullable=True, index=True)
    rental_fees = Column(Numeric(10, 2), nullable=True)

    # Customer and Service information
    customer_code = Column(String(100), nullable=True, index=True)
    service_number = Column(String(100), nullable=True, index=True)
    related_service_number = Column(String(100), nullable=True)
    username = Column(String(255), nullable=True)

    # Subscriber status
    subscriber_status = Column(String(100), nullable=True, index=True)
    status_date = Column(Date, nullable=True)
    creation_date = Column(Date, nullable=True)
    active_date = Column(Date, nullable=True)

    # CSR and Department
    csr_name = Column(String(255), nullable=True)
    department_name = Column(String(255), nullable=True)

    # Address information
    state = Column(String(200), nullable=True, index=True)
    area = Column(String(200), nullable=True, index=True)
    town = Column(String(200), nullable=True, index=True)
    grid = Column(String(200), nullable=True)
    street = Column(String(500), nullable=True)
    street_number = Column(String(100), nullable=True)
    building_no = Column(String(100), nullable=True)
    unit = Column(String(100), nullable=True)
    floor = Column(String(100), nullable=True)
    house_no = Column(String(100), nullable=True)
    additional_address_info = Column(Text, nullable=True)

    # Customer personal information
    customer_full_name = Column(String(500), nullable=True, index=True)
    province = Column(String(200), nullable=True, index=True)
    district = Column(String(200), nullable=True, index=True)
    city = Column(String(200), nullable=True, index=True)
    postal_code = Column(String(50), nullable=True)

    # Dates and technical information
    expiry_date = Column(Date, nullable=True)
    iccid = Column(String(100), nullable=True, index=True)
    imsi = Column(String(100), nullable=True, index=True)
    contact_number = Column(String(100), nullable=True)

    # Anomaly flags
    is_anomaly = Column(Boolean, default=False, index=True, nullable=False)
    anomaly_reason = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Park(id={self.id}, customer_code='{self.customer_code}', service_number='{self.service_number}', is_anomaly={self.is_anomaly})>"


class ParkAnomaly(Base):
    """
    Parc Corporate NGBSS Anomalies
    Stores records that match anomaly criteria:
    - Code Customer L3: Categories 5 and 57
    - Offer Name containing: Moohtarif, Solutions Hébergements
    - Telecom Type: X25, WIFI, WIMAX
    """
    __tablename__ = "park_anomalies"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="park_anomalies")

    # Reference to original data (key fields for identification)
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT")
    actel_code = Column(String(100), nullable=True, index=True)
    customer_code = Column(String(100), nullable=True, index=True)
    service_number = Column(String(100), nullable=True, index=True)
    customer_l3_code = Column(String(100), nullable=True, index=True)
    telecom_type = Column(String(100), nullable=True, index=True)
    offer_name = Column(String(255), nullable=True, index=True)

    # Anomaly details
    anomaly_type = Column(String(100), default="Anomalie Parc NGBSS", nullable=False)
    anomaly_reason = Column(Text, nullable=True)

    # Original record data (JSON string containing all fields)
    original_data = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ParkAnomaly(id={self.id}, service_number='{self.service_number}', reason='{self.anomaly_reason}')>"

