"""
User Module DOT Model
Allows users to have different DOT assignments per module
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime

# Module constants
MODULE_PARC_CORPORATE_NGBSS = "parc_corporate_ngbss"
MODULE_CHIFFRE_AFFAIRES = "chiffre_affaires"
MODULE_ENCAISSEMENT_AR_DOT = "encaissement_ar_dot"
MODULE_CREANCE_PERIODIQUE_DOT = "creance_periodique_dot"

ALL_MODULES = [
    MODULE_PARC_CORPORATE_NGBSS,
    MODULE_CHIFFRE_AFFAIRES,
    MODULE_ENCAISSEMENT_AR_DOT,
    MODULE_CREANCE_PERIODIQUE_DOT,
]


class UserModuleDOT(Base):
    """
    Stores module-specific DOT assignments for users
    Allows a user to have different DOT access for different modules
    """
    __tablename__ = "user_module_dots"

    id = Column(Integer, primary_key=True, index=True)

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="module_dots")

    # DOT relationship
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=False, index=True)
    dot = relationship("DOT")

    # Module name (e.g., "parc_corporate_ngbss", "chiffre_affaires")
    module = Column(String(100), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one DOT assignment per user per module
    __table_args__ = (
        UniqueConstraint('user_id', 'module', name='uq_user_module_dot'),
    )

    def __repr__(self):
        return f"<UserModuleDOT(user_id={self.user_id}, module='{self.module}', dot_id={self.dot_id})>"





