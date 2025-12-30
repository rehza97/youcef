from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database.connection import Base

# Module constants (same as in module_dot_config.py)
MODULE_PARC_CORPORATE_NGBSS = "parc_corporate_ngbss"
MODULE_CHIFFRE_AFFAIRES = "chiffre_affaires"
MODULE_ENCAISSEMENT_AR_DOT = "encaissement_ar_dot"
MODULE_CREANCE_PERIODIQUE_DOT = "creance_periodique_dot"

AVAILABLE_MODULES = [
    MODULE_PARC_CORPORATE_NGBSS,
    MODULE_CHIFFRE_AFFAIRES,
    MODULE_ENCAISSEMENT_AR_DOT,
    MODULE_CREANCE_PERIODIQUE_DOT
]


class DOT(Base):
    __tablename__ = "dots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    module = Column(String(100), nullable=True, index=True)  # NEW: Module this DOT belongs to
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # Relationships with CASCADE DELETE
    # When a DOT is deleted, all related records will be automatically deleted
    parks = relationship("Park", back_populates="dot", cascade="all, delete-orphan")
    parks_2b = relationship("Park2B", back_populates="dot", cascade="all, delete-orphan")
    users = relationship("User", back_populates="dot", cascade="all, delete-orphan")
    revenue_journals = relationship("RevenueJournal", back_populates="dot", cascade="all, delete-orphan")
    revenue_objectives = relationship("RevenueObjective", back_populates="dot", cascade="all, delete-orphan")
    revenue_dot_corporate = relationship("RevenueDOTCorporate", back_populates="dot", cascade="all, delete-orphan")
    encaissement_ar_records = relationship("EncaissementARDot", back_populates="dot", cascade="all, delete-orphan")
    encaissement_anomaly_records = relationship("EncaissementAnomaly", back_populates="dot", cascade="all, delete-orphan")
    encaissement_aggregate_views = relationship("EncaissementAggregateView", back_populates="dot", cascade="all, delete-orphan")
    creance_periodique_records = relationship("CreancePeriodiqueDot", back_populates="dot_relationship", cascade="all, delete-orphan")
    creance_aggregate_views = relationship("CreanceAggregateView", back_populates="dot_relationship", cascade="all, delete-orphan")

    # Unique constraint: DOT name must be unique within each module
    __table_args__ = (
        UniqueConstraint('name', 'module', name='uq_dot_name_module'),
    )

    def __repr__(self):
        module_str = f", module='{self.module}'" if self.module else ""
        return f"<DOT(id={self.id}, name='{self.name}'{module_str})>"

