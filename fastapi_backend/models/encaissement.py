"""
Encaissement AR DOT Models
Models for encaissement (collection) data with DOT relationships and RBAC support
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime


class EncaissementARDot(Base):
    """
    Main Encaissement AR DOT - AT- Etat des Factures AR et encaissements par période
    Stores invoice and collection data with DOT relationships for RBAC control
    """
    __tablename__ = "encaissement_ar_dot"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship - track which file this data came from
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="encaissement_ar_records")

    # DOT relationship for RBAC control
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="encaissement_ar_records")

    # Organization info
    organisation = Column(String(200), nullable=True, index=True)  # DOT name (cleaned: no DOT_, no AT_SIEGE)

    # Invoice identifiers
    source = Column(String(100), nullable=True, index=True)  # Source (DCC, DII, DINR, etc.)
    n_fact = Column(Integer, nullable=True, index=True)  # Invoice number (numeric)
    typ_fact = Column(String(50), nullable=True, index=True)  # Invoice type (INV, CM, etc.)
    date_fact = Column(Date, nullable=True, index=True)  # Invoice date
    mois = Column(String(7), nullable=True, index=True)  # Month (YYYY-MM) for aggregation

    # Customer info
    client = Column(String(255), nullable=True, index=True)  # Customer name
    n_client = Column(String(100), nullable=True, index=True)  # Customer number

    # Invoice details
    obj_fact = Column(Text, nullable=True)  # Invoice object/description
    periode = Column(String(255), nullable=True)  # Period
    ref = Column(String(255), nullable=True)  # Reference
    termine_flag = Column(String(10), nullable=True)  # Terminated flag (Y/N)
    creer_par = Column(String(100), nullable=True)  # Created by

    # Financial amounts (Numeric for precision)
    montant_ht = Column(Numeric(15, 2), nullable=True)  # Amount excluding tax
    montant_taxe = Column(Numeric(15, 2), nullable=True)  # Tax amount
    montant_ttc = Column(Numeric(15, 2), nullable=True, index=True)  # Amount including tax
    chiffre_aff_exe = Column(Numeric(15, 2), nullable=True)  # Executed revenue

    # Collection/Payment info
    encaissement = Column(Numeric(15, 2), nullable=True, index=True)  # Collection amount
    n_rglt = Column(String(100), nullable=True, index=True)  # Payment reference number
    date_rglt = Column(Date, nullable=True, index=True)  # Payment date
    facture_avoir_annulation = Column(String(255), nullable=True)  # Credit/Cancel note

    # Calculated KPIs
    taux_encaissement = Column(Numeric(10, 2), nullable=True, index=True)  # Collection rate (Encaissement/Montant TTC * 100)
    montant_restant = Column(Numeric(15, 2), nullable=True)  # Remaining amount (Montant TTC - Encaissement)

    # Duplicate detection
    composite_key = Column(String(500), nullable=True, index=True)  # Organisation & N_Fact & Typ_Fact
    is_duplicate = Column(Boolean, default=False, index=True)  # Flag for duplicate entries

    # Anomaly tracking
    is_anomaly = Column(Boolean, default=False, index=True)
    anomaly_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EncaissementARDot(id={self.id}, organisation='{self.organisation}', n_fact={self.n_fact}, montant_ttc={self.montant_ttc}, encaissement={self.encaissement})>"


class EncaissementAnomaly(Base):
    """
    Encaissement Anomalies - Stores records marked as anomalies
    Includes negative amounts, excessive collection rates, etc.
    """
    __tablename__ = "encaissement_anomalies"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="encaissement_anomaly_records")

    # DOT relationship for RBAC control
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="encaissement_anomaly_records")

    # Reference to original data
    organisation = Column(String(200), nullable=True, index=True)
    n_fact = Column(Integer, nullable=True, index=True)
    typ_fact = Column(String(50), nullable=True)
    montant_ttc = Column(Numeric(15, 2), nullable=True)
    encaissement = Column(Numeric(15, 2), nullable=True)

    # Anomaly details
    anomaly_type = Column(String(100), nullable=True, index=True)  # e.g., "negative_montant_ttc", "excessive_taux"
    anomaly_reason = Column(Text, nullable=True)

    # Original record data (JSON string)
    original_data = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EncaissementAnomaly(id={self.id}, organisation='{self.organisation}', n_fact={self.n_fact}, type='{self.anomaly_type}')>"


class EncaissementAggregateView(Base):
    """
    Aggregated Encaissement Views - Pre-calculated for fast dashboard loading
    Stores monthly and DOT-level aggregations
    """
    __tablename__ = "encaissement_aggregate_views"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="encaissement_aggregate_views")

    # DOT relationship for RBAC control
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="encaissement_aggregate_views")

    # Aggregation type
    view_type = Column(String(50), nullable=False, index=True)  # 'by_month', 'by_dot', 'overview'

    # For monthly aggregation
    mois = Column(String(7), nullable=True, index=True)  # YYYY-MM

    # For DOT aggregation
    organisation = Column(String(200), nullable=True, index=True)

    # Aggregated metrics
    total_montant_ttc = Column(Numeric(15, 2), nullable=True)
    total_encaissement = Column(Numeric(15, 2), nullable=True)
    total_montant_restant = Column(Numeric(15, 2), nullable=True)
    taux_encaissement = Column(Numeric(10, 2), nullable=True)
    nombre_factures = Column(Integer, nullable=True)

    # For pie chart percentages
    percentage = Column(Numeric(10, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EncaissementAggregateView(id={self.id}, view_type='{self.view_type}', mois='{self.mois}', organisation='{self.organisation}')>"
