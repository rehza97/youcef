"""
Revenue (Chiffre d'Affaires AR DOT) Models
Models for revenue journal, account descriptions, and objectives
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime


class RevenueJournal(Base):
    """
    Main Revenue Journal - AT- Journal Chiffre d affaire de l exercice avec Date GL
    Stores revenue transactions with account details and customer information
    """
    __tablename__ = "revenue_journal"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="revenue_journals")

    # DOT relationship
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="revenue_journals")

    # Organization info
    org_name = Column(String(200), nullable=True, index=True)  # DOT name from Org Name

    # Transaction identifiers
    origine = Column(String(100), nullable=True)  # Origin
    n_fact = Column(String(100), nullable=True, index=True)  # Invoice number
    typ_fact = Column(String(100), nullable=True, index=True)  # Invoice type
    date_fact = Column(Date, nullable=True, index=True)  # Invoice date

    # Customer info
    n_client = Column(String(100), nullable=True, index=True)  # Customer number
    client = Column(String(255), nullable=True)  # Customer name
    delai_paie = Column(String(100), nullable=True)  # Payment delay

    # Financial info
    devise = Column(String(20), nullable=True)  # Currency
    obj_fact = Column(Text, nullable=True)  # Invoice object
    cpt_comptable = Column(String(100), nullable=True, index=True)  # Account code
    date_facture_gl = Column(Date, nullable=True)  # GL invoice date
    date_gl = Column(Date, nullable=True, index=True)  # GL date
    periode_de_facturation = Column(String(100), nullable=True)  # Billing period
    reference = Column(String(255), nullable=True)  # Reference

    # Status and metadata
    termine_flag = Column(Boolean, nullable=True)  # Terminated flag
    tax_amount = Column(Numeric(15, 2), nullable=True)  # Tax amount
    creer_par = Column(String(100), nullable=True)  # Created by

    # Line item details
    n_ligne = Column(String(100), nullable=True)  # Line number
    description_ligne_de_produit = Column(Text, nullable=True)  # Product line description
    uom = Column(String(50), nullable=True)  # Unit of measure
    qte = Column(Numeric(15, 4), nullable=True)  # Quantity
    prix_uni = Column(Numeric(15, 2), nullable=True)  # Unit price
    taux_change = Column(Numeric(15, 6), nullable=True)  # Exchange rate

    # Amounts
    mnt_ht = Column(Numeric(15, 2), nullable=True)  # Amount excluding tax
    tax = Column(String(50), nullable=True)  # Tax code
    mnt_tax = Column(Numeric(15, 2), nullable=True)  # Tax amount
    mnt_ttc = Column(Numeric(15, 2), nullable=True)  # Amount including tax
    memo_line_id = Column(String(100), nullable=True)  # Memo line ID
    chiffre_aff_exe_dzd = Column(Numeric(15, 2), nullable=True, index=True)  # Revenue in DZD

    # Calculated fields
    tva = Column(Numeric(10, 4), nullable=True)  # VAT rate (Mnt Ttc/Mnt Ht)
    chiffre_aff_exe_dzd_ttc = Column(Numeric(15, 2), nullable=True)  # Revenue TTC (CA * TVA)
    taux_realisation_ca = Column(Numeric(10, 4), nullable=True, index=True)  # Achievement rate (CA/Objectif)

    # Foreign key to AccountDescription
    account_description_id = Column(Integer, ForeignKey("account_descriptions.id"), nullable=True)
    account_description = relationship("AccountDescription", back_populates="revenue_journals")

    # Foreign key to RevenueObjective
    revenue_objective_id = Column(Integer, ForeignKey("revenue_objectives.id"), nullable=True)
    revenue_objective = relationship("RevenueObjective", back_populates="revenue_journals")

    # Anomaly flag
    is_anomaly = Column(Boolean, default=False, index=True)
    anomaly_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RevenueJournal(id={self.id}, org_name='{self.org_name}', n_fact='{self.n_fact}', ca={self.chiffre_aff_exe_dzd})>"


class AccountDescription(Base):
    """
    Account Descriptions - Description Cpt Comptable.xlsx
    Stores chart of accounts with descriptions and metadata
    """
    __tablename__ = "account_descriptions"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="account_descriptions")

    # Account info
    cpt_comptable = Column(String(100), nullable=False, unique=True, index=True)  # Account code
    description_cpt_comptable = Column(String(500), nullable=True)  # Account description
    aut_bdg = Column(String(100), nullable=True)  # Budget authority
    aut_imp = Column(String(100), nullable=True)  # Implementation authority
    type_cpte = Column(String(100), nullable=True, index=True)  # Account type
    auxil = Column(String(100), nullable=True)  # Auxiliary
    let = Column(String(100), nullable=True)  # Letter

    # Relationship back to revenue journals
    revenue_journals = relationship("RevenueJournal", back_populates="account_description")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AccountDescription(id={self.id}, cpt_comptable='{self.cpt_comptable}', description='{self.description_cpt_comptable}')>"


class RevenueObjective(Base):
    """
    Revenue Objectives - Objectif C.A.xlsx
    Stores revenue targets by DOT
    """
    __tablename__ = "revenue_objectives"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="revenue_objectives")

    # DOT relationship
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="revenue_objectives")

    # Objective data
    dot_name = Column(String(200), nullable=False, index=True)  # DOT name
    objectif_ca = Column(Numeric(15, 2), nullable=False)  # Revenue objective

    # Relationship back to revenue journals
    revenue_journals = relationship("RevenueJournal", back_populates="revenue_objective")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RevenueObjective(id={self.id}, dot_name='{self.dot_name}', objectif={self.objectif_ca})>"


class RevenueAnomaly(Base):
    """
    Revenue Anomalies - Stores records marked as anomalies
    Records where Cpt Comptable contains 'A' and Description doesn't start with '@'
    """
    __tablename__ = "revenue_anomalies"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="revenue_anomalies")

    # Reference to original data
    org_name = Column(String(200), nullable=True, index=True)
    n_fact = Column(String(100), nullable=True, index=True)
    cpt_comptable = Column(String(100), nullable=True, index=True)
    description_ligne_de_produit = Column(Text, nullable=True)

    # Anomaly details
    anomaly_type = Column(String(100), default="Chiffre d'Affaires AR DOT")
    anomaly_reason = Column(Text, nullable=True)

    # Original record data (JSON or full copy)
    original_data = Column(Text, nullable=True)  # Can store JSON string of full record

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RevenueAnomaly(id={self.id}, org_name='{self.org_name}', reason='{self.anomaly_reason}')>"


class RevenueDOTCorporate(Base):
    """
    Revenue DOT Corporate - Monthly revenue data by DOT
    Stores monthly revenue figures for each DOT from Excel files
    """
    __tablename__ = "objectifs_monthly_dot"

    id = Column(Integer, primary_key=True, index=True)

    # File relationship
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=True, index=True)
    file_upload = relationship("FileUpload", back_populates="revenue_dot_corporate")

    # DOT relationship
    dot_id = Column(Integer, ForeignKey("dots.id"), nullable=True, index=True)
    dot = relationship("DOT", back_populates="revenue_dot_corporate")

    # DOT name
    dot_name = Column(String(200), nullable=False, index=True)

    # Year for filtering
    year = Column(Integer, nullable=False, default=lambda: datetime.utcnow().year, index=True)

    # Monthly revenue values
    january = Column(Numeric(15, 2), nullable=True)  # Jan
    february = Column(Numeric(15, 2), nullable=True)  # fév
    march = Column(Numeric(15, 2), nullable=True)  # mars
    april = Column(Numeric(15, 2), nullable=True)  # Avril
    may = Column(Numeric(15, 2), nullable=True)  # Mai
    june = Column(Numeric(15, 2), nullable=True)  # Juin
    july = Column(Numeric(15, 2), nullable=True)  # Juillet
    august = Column(Numeric(15, 2), nullable=True)  # aout
    september = Column(Numeric(15, 2), nullable=True)  # Sept
    october = Column(Numeric(15, 2), nullable=True)  # Oct
    november = Column(Numeric(15, 2), nullable=True)  # Nov
    december = Column(Numeric(15, 2), nullable=True)  # Déc (total)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RevenueDOTCorporate(id={self.id}, dot_name='{self.dot_name}', year={self.year}, total={self.december})>"
