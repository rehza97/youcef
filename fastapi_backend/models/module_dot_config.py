"""
Module DOT Configuration Model
Allows setting a default DOT for each module at the system level
"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.connection import Base

# Module constants
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

class ModuleDOTConfig(Base):
    """
    System-level configuration for module-specific DOT assignments.
    Each module can have its own default DOT.

    Priority order for DOT resolution:
    1. User-specific module DOT (UserModuleDOT)
    2. Module-level default DOT (ModuleDOTConfig)
    3. User's global dot_id
    4. All DOTs (for superusers/staff)
    """
    __tablename__ = "module_dot_config"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(100), nullable=False, unique=True)
    dot_id = Column(Integer, ForeignKey("dots.id", ondelete="CASCADE"), nullable=False)

    # Relationship
    dot = relationship("DOT", backref="module_configs")

    __table_args__ = (
        UniqueConstraint('module', name='uq_module_dot_config_module'),
    )

    def __repr__(self):
        return f"<ModuleDOTConfig(module='{self.module}', dot_id={self.dot_id})>"
