"""
Revenue Pivot Table Models
Pre-calculated pivot tables for fast dashboard loading
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime


class RevenuePivotCache(Base):
    """
    Pre-calculated Pivot Table (TCD - Tableau Croisé Dynamique)
    Stores aggregated revenue data by different dimensions
    """
    __tablename__ = "revenue_pivot_cache"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="revenue_pivot_cache")

    # Pivot configuration
    pivot_type = Column(String(50), nullable=False, index=True)
    # Types: 'by_org', 'by_month', 'by_account', 'by_org_month', 'overview'

    # Dimensions (grouping keys)
    org_name = Column(String(200), nullable=True, index=True)
    month = Column(String(7), nullable=True, index=True)  # YYYY-MM format
    cpt_comptable = Column(String(50), nullable=True, index=True)
    year = Column(Integer, nullable=True, index=True)

    # Aggregated metrics
    total_revenue = Column(Numeric(15, 2), nullable=True)  # Sum of Chiffre Aff Exe Dzd
    total_revenue_ttc = Column(Numeric(15, 2), nullable=True)  # Sum of CA TTC
    total_objective = Column(Numeric(15, 2), nullable=True)  # Sum of Objectif CA
    avg_achievement_rate = Column(Numeric(10, 4), nullable=True)  # Avg Taux réalisation
    record_count = Column(Integer, nullable=True)  # Count of records

    # Statistical metrics
    min_revenue = Column(Numeric(15, 2), nullable=True)
    max_revenue = Column(Numeric(15, 2), nullable=True)
    median_revenue = Column(Numeric(15, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes for fast queries
    __table_args__ = (
        Index('idx_pivot_type_org', 'pivot_type', 'org_name'),
        Index('idx_pivot_type_month', 'pivot_type', 'month'),
        Index('idx_pivot_type_year', 'pivot_type', 'year'),
        Index('idx_org_month', 'org_name', 'month'),
    )

    def __repr__(self):
        return f"<RevenuePivotCache(id={self.id}, type='{self.pivot_type}', org='{self.org_name}', month='{self.month}')>"


class RevenuePivotMetadata(Base):
    """
    Metadata for pivot table generation
    Tracks last generation time and status
    """
    __tablename__ = "revenue_pivot_metadata"

    id = Column(Integer, primary_key=True, index=True)
    pivot_type = Column(String(50), nullable=False, unique=True, index=True)
    last_generated_at = Column(DateTime, nullable=True)
    generation_status = Column(String(20), nullable=True)  # 'pending', 'generating', 'completed', 'failed'
    generation_duration_seconds = Column(Integer, nullable=True)
    record_count = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RevenuePivotMetadata(type='{self.pivot_type}', status='{self.generation_status}')>"
