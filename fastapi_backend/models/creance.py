"""
Créance Périodique DOT Models
Models for periodic debt (creance) data with DOT relationships and RBAC support
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime


class CreancePeriodiqueDot(Base):
    """
    Main Créance Périodique DOT table
    Stores periodic debt data with DOT relationships for RBAC control
    """
    __tablename__ = "creance_periodique_dot"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship - track which file this data came from
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="creance_periodique_records")

    # DOT relationship for RBAC control
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot_relationship = relationship("DOT", back_populates="creance_periodique_records")

    # Organization and location info
    dot = Column(String(200), nullable=True, index=True)  # DOT name (cleaned: _ replaced with space)
    actel = Column(String(255), nullable=True)  # ACTEL identifier

    # Time period
    mois = Column(String(2), nullable=True, index=True)  # Month (01-12)
    annee = Column(String(4), nullable=True, index=True)  # Year (2023, 2024, etc.)
    period_key = Column(String(7), nullable=True, index=True)  # YYYY-MM for aggregation

    # Subscription and product info
    subs_status = Column(String(50), nullable=True)  # Subscription status (B01, B02, B03, B04)
    produit = Column(String(100), nullable=True, index=True)  # Product type (cleaned)

    # Customer classification (3 levels)
    cust_lev1 = Column(String(200), nullable=True, index=True)  # Customer Level 1 (Corporate, etc.)
    cust_lev2 = Column(String(200), nullable=True, index=True)  # Customer Level 2 (cleaned)
    cust_lev3 = Column(String(200), nullable=True, index=True)  # Customer Level 3 (cleaned)

    # Financial amounts (Numeric for precision) - All in DZD
    invoice_amt = Column(Numeric(15, 2), nullable=True)  # Invoice amount (TTC)
    open_amt = Column(Numeric(15, 2), nullable=True, index=True)  # Open amount
    tax_amt = Column(Numeric(15, 2), nullable=True)  # Tax amount
    invoice_amt_ht = Column(Numeric(15, 2), nullable=True)  # Invoice amount excluding tax

    # Dispute amounts
    dispute_amt = Column(Numeric(15, 2), nullable=True)  # Dispute amount
    dispute_tax_amt = Column(Numeric(15, 2), nullable=True)  # Dispute tax amount
    dispute_net_amt = Column(Numeric(15, 2), nullable=True)  # Dispute net amount

    # Debt (Créance) amounts
    creance_brut = Column(Numeric(15, 2), nullable=True, index=True)  # Gross debt
    creance_net = Column(Numeric(15, 2), nullable=True, index=True)  # Net debt (main KPI)
    creance_ht = Column(Numeric(15, 2), nullable=True)  # Debt excluding tax

    # Credit note (Avoir) amounts
    avoir_amt = Column(Numeric(15, 2), nullable=True)  # Credit note amount (TTC)
    avoir_amt_ht = Column(Numeric(15, 2), nullable=True)  # Credit note amount excluding tax

    # Additional créance metrics
    exigible_mt = Column(Numeric(15, 2), nullable=True)  # Due amount
    creance_120_mt = Column(Numeric(15, 2), nullable=True)  # Créance over 120 days

    # Data quality flags
    is_filtered = Column(Boolean, default=False, index=True)  # Flag for filtered records
    filter_reason = Column(Text, nullable=True)  # Reason for filtering

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CreancePeriodiqueDot(id={self.id}, dot='{self.dot}', annee={self.annee}, mois={self.mois}, creance_net={self.creance_net})>"


class CreanceAggregateView(Base):
    """
    Aggregated Créance Views - Pre-calculated for fast dashboard loading
    Stores aggregations by DOT, year, product, and customer level
    """
    __tablename__ = "creance_aggregate_views"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="creance_aggregate_views")

    # DOT relationship for RBAC control
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot_relationship = relationship("DOT", back_populates="creance_aggregate_views")

    # Aggregation type
    view_type = Column(String(50), nullable=False, index=True)  # 'overview', 'by_dot', 'by_annee', 'by_produit', 'by_cust_lev2'

    # Dimension fields (depending on view_type)
    dot_name = Column(String(200), nullable=True, index=True)
    annee = Column(String(4), nullable=True, index=True)
    produit = Column(String(100), nullable=True, index=True)
    cust_lev2 = Column(String(200), nullable=True, index=True)

    # Aggregated metrics
    total_invoice_amt = Column(Numeric(15, 2), nullable=True)
    total_open_amt = Column(Numeric(15, 2), nullable=True)
    total_tax_amt = Column(Numeric(15, 2), nullable=True)
    total_invoice_amt_ht = Column(Numeric(15, 2), nullable=True)
    total_creance_brut = Column(Numeric(15, 2), nullable=True)
    total_creance_net = Column(Numeric(15, 2), nullable=True)  # Main KPI
    total_creance_ht = Column(Numeric(15, 2), nullable=True)
    nombre_lignes = Column(Integer, nullable=True)  # Number of records

    # For percentage calculations
    percentage = Column(Numeric(10, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CreanceAggregateView(id={self.id}, view_type='{self.view_type}', total_creance_net={self.total_creance_net})>"
