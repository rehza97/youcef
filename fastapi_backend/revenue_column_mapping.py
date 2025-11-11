#!/usr/bin/env python3
"""
Revenue (Chiffre d'Affaires AR DOT) Column Mapping
Maps actual revenue file headers to database fields for 3 different file types
"""

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FILE 1: Journal Chiffre d'Affaires (Main Revenue Journal)
# ============================================================================
REVENUE_JOURNAL_HEADERS = [
    "Org Name",
    "Origine",
    "N Fact",
    "Typ Fact",
    "Date Fact",
    "N Client",
    "Client",
    "Delai Paie",
    "Devise",
    "Obj Fact",
    "Cpt Comptable",
    "Date facture GL",
    "Date GL",
    "Periode de facturation",
    "Reference",
    "Termine Flag",
    "Tax Amount",
    "Creer Par",
    "N Ligne",
    "Description (ligne de produit)",
    "Uom",
    "Qte",
    "Prix Uni",
    "Taux Change",
    "Mnt Ht",
    "Tax",
    "Mnt Tax",
    "Mnt Ttc",
    "Memo Line Id",
    "Chiffre Aff Exe Dzd"
]

REVENUE_JOURNAL_TO_DB = {
    "Org Name": "org_name",
    "Origine": "origine",
    "N Fact": "n_fact",
    "Typ Fact": "typ_fact",
    "Date Fact": "date_fact",
    "N Client": "n_client",
    "Client": "client",
    "Delai Paie": "delai_paie",
    "Devise": "devise",
    "Obj Fact": "obj_fact",
    "Cpt Comptable": "cpt_comptable",
    "Date facture GL": "date_facture_gl",
    "Date GL": "date_gl",
    "Periode de facturation": "periode_de_facturation",
    "Reference": "reference",
    "Termine Flag": "termine_flag",
    "Tax Amount": "tax_amount",
    "Creer Par": "creer_par",
    "N Ligne": "n_ligne",
    "Description (ligne de produit)": "description_ligne_de_produit",
    "Uom": "uom",
    "Qte": "qte",
    "Prix Uni": "prix_uni",
    "Taux Change": "taux_change",
    "Mnt Ht": "mnt_ht",
    "Tax": "tax",
    "Mnt Tax": "mnt_tax",
    "Mnt Ttc": "mnt_ttc",
    "Memo Line Id": "memo_line_id",
    "Chiffre Aff Exe Dzd": "chiffre_aff_exe_dzd"
}

# ============================================================================
# FILE 2: Description Cpt Comptable (Account Descriptions)
# ============================================================================
ACCOUNT_DESCRIPTION_HEADERS = [
    "Cpt Comptable",
    "Description Cpt Comptable",
    "AUT_BDG",
    "AUT_IMP",
    "TYPE_CPTE",
    "AUXIL",
    "LET"
]

ACCOUNT_DESCRIPTION_TO_DB = {
    "Cpt Comptable": "cpt_comptable",
    "Description Cpt Comptable": "description_cpt_comptable",
    "AUT_BDG": "aut_bdg",
    "AUT_IMP": "aut_imp",
    "TYPE_CPTE": "type_cpte",
    "AUXIL": "auxil",
    "LET": "let"
}

# ============================================================================
# FILE 3: Objectif C.A (Revenue Objectives)
# ============================================================================
REVENUE_OBJECTIVE_HEADERS = [
    "DOT",
    "Objectif C.A"
]

REVENUE_OBJECTIVE_TO_DB = {
    "DOT": "dot_name",
    "Objectif C.A": "objectif_ca"
}


# ============================================================================
# Helper Functions
# ============================================================================

def normalize_column_name(name: str) -> str:
    """Normalize column name for matching"""
    return (
        str(name).lower()
        .replace('_', ' ')
        .replace('-', ' ')
        .replace("'", "'")
        .replace("'", "'")
        .strip()
    )


def find_column(df: pd.DataFrame, keywords: list) -> Optional[str]:
    """Find a column by keywords with improved matching"""
    # Create normalized map
    norm_map = {normalize_column_name(col): col for col in df.columns}

    # Try exact match first
    for col in df.columns:
        if col in keywords:
            return col

    # Try all keywords match
    tokens = [normalize_column_name(k) for k in keywords]
    for norm_col, orig_col in norm_map.items():
        if all(token in norm_col for token in tokens):
            return orig_col

    # Try any keyword match
    for norm_col, orig_col in norm_map.items():
        if any(token in norm_col for token in tokens):
            return orig_col

    return None


def safe_string(value: Any) -> Optional[str]:
    """Safely convert value to string"""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() not in ['nan', 'none', 'null', ''] else None


def safe_float(value: Any, max_value: Optional[float] = None, min_value: Optional[float] = None) -> Optional[float]:
    """Safely convert value to float, removing thousands separators"""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in ['nan', 'none', 'null', '']:
        return None
    try:
        # Remove dots (thousands separator in French format)
        text = text.replace('.', '').replace(',', '.')
        float_value = float(text)
        
        # Clamp to valid range if specified
        if max_value is not None and float_value > max_value:
            logger.warning(f"Float value {float_value} exceeds maximum {max_value}, clamping")
            return max_value
        if min_value is not None and float_value < min_value:
            logger.warning(f"Float value {float_value} below minimum {min_value}, clamping")
            return min_value
        
        return float_value
    except Exception:
        return None


def safe_date(value: Any) -> Optional[datetime]:
    """Safely convert value to date"""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in ['nan', 'none', 'null', 'nat', '']:
        return None
    try:
        # Try ISO format first
        result = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
        # Check if result is NaT (Not a Time) before converting
        if pd.isna(result):
            return None
        return result.to_pydatetime()
    except:
        try:
            # Try flexible parsing with dayfirst=True for French date format (dd/mm/yyyy)
            result = pd.to_datetime(text, errors="coerce", dayfirst=True)
            # Check if result is NaT (Not a Time) before converting
            if pd.isna(result):
                return None
            return result.to_pydatetime()
        except:
            return None


def safe_boolean(value: Any) -> Optional[bool]:
    """Safely convert value to boolean"""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text in ['yes', 'oui', 'true', '1', 'y', 'o']:
        return True
    elif text in ['no', 'non', 'false', '0', 'n']:
        return False
    return None


# ============================================================================
# Mapping Functions
# ============================================================================

def map_revenue_journal_record(record: dict, file_upload_id: int = None) -> dict:
    """Map a revenue journal record to database dictionary"""

    def _get(keywords: list, default=None):
        """Get value from record by finding column with keywords"""
        for key in record.keys():
            if any(normalize_column_name(kw) in normalize_column_name(key) for kw in keywords):
                return record.get(key, default)
        # Exact match fallback
        for kw in keywords:
            if kw in record:
                return record.get(kw, default)
        return default

    # Maximum value for NUMERIC(15, 2): 9,999,999,999,999.99
    MAX_NUMERIC_15_2 = 9999999999999.99
    MIN_NUMERIC_15_2 = -9999999999999.99

    return {
        "file_upload_id": file_upload_id,
        "org_name": safe_string(_get(["Org Name", "org name", "organisation"])),
        "origine": safe_string(_get(["Origine", "origin"])),
        "n_fact": safe_string(_get(["N Fact", "numero facture", "invoice number"])),
        "typ_fact": safe_string(_get(["Typ Fact", "type facture", "invoice type"])),
        "date_fact": safe_date(_get(["Date Fact", "date facture"])),
        "n_client": safe_string(_get(["N Client", "numero client", "customer number"])),
        "client": safe_string(_get(["Client", "customer"])),
        "delai_paie": safe_string(_get(["Delai Paie", "payment delay"])),
        "devise": safe_string(_get(["Devise", "currency"])),
        "obj_fact": safe_string(_get(["Obj Fact", "objet facture", "invoice object"])),
        "cpt_comptable": safe_string(_get(["Cpt Comptable", "compte comptable", "account code"])),
        "date_facture_gl": safe_date(_get(["Date facture GL", "gl invoice date"])),
        "date_gl": safe_date(_get(["Date GL", "gl date"])),
        "periode_de_facturation": safe_string(_get(["Periode de facturation", "billing period"])),
        "reference": safe_string(_get(["Reference", "ref"])),
        "termine_flag": safe_boolean(_get(["Termine Flag", "terminated"])),
        # Monetary fields with NUMERIC(15, 2) clamping
        "tax_amount": safe_float(_get(["Tax Amount", "montant taxe"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "creer_par": safe_string(_get(["Creer Par", "created by"])),
        "n_ligne": safe_string(_get(["N Ligne", "line number"])),
        "description_ligne_de_produit": safe_string(_get(["Description (ligne de produit)", "product line description", "description ligne"])),
        "uom": safe_string(_get(["Uom", "unit of measure", "unite"])),
        "qte": safe_float(_get(["Qte", "quantity", "quantite"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "prix_uni": safe_float(_get(["Prix Uni", "unit price", "prix unitaire"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "taux_change": safe_float(_get(["Taux Change", "exchange rate", "taux"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "mnt_ht": safe_float(_get(["Mnt Ht", "montant ht", "amount excluding tax"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "tax": safe_string(_get(["Tax", "taxe"])),
        "mnt_tax": safe_float(_get(["Mnt Tax", "montant tax", "tax amount"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "mnt_ttc": safe_float(_get(["Mnt Ttc", "montant ttc", "amount including tax"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "memo_line_id": safe_string(_get(["Memo Line Id", "memo"])),
        "chiffre_aff_exe_dzd": safe_float(_get(["Chiffre Aff Exe Dzd", "chiffre affaires", "revenue dzd"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        # Calculated columns - clamp to NUMERIC(10, 4) range: -999999.9999 to 999999.9999
        "tva": safe_float(_get(["TVA", "tva", "vat"]), max_value=999999.9999, min_value=-999999.9999),
        "chiffre_aff_exe_dzd_ttc": safe_float(_get(["Chiffre_Aff_Exe_Dzd_TTC", "ca ttc", "revenue ttc"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "taux_realisation_ca": safe_float(_get(["Taux_Realisation_CA", "achievement rate", "taux realisation"]), max_value=999999.9999, min_value=-999999.9999),
        # Matched relationships (will be set after matching)
        "account_description_id": _get(["account_description_id"]),
        "revenue_objective_id": _get(["revenue_objective_id"]),
        "created_at": datetime.utcnow(),
    }


def map_account_description_record(record: dict, file_upload_id: int = None) -> dict:
    """Map an account description record to database dictionary"""

    def _get(keywords: list, default=None):
        for key in record.keys():
            if any(normalize_column_name(kw) in normalize_column_name(key) for kw in keywords):
                return record.get(key, default)
        for kw in keywords:
            if kw in record:
                return record.get(kw, default)
        return default

    return {
        "file_upload_id": file_upload_id,
        "cpt_comptable": safe_string(_get(["Cpt Comptable", "compte comptable", "account code"])),
        "description_cpt_comptable": safe_string(_get(["Description Cpt Comptable", "description", "account description"])),
        "aut_bdg": safe_string(_get(["AUT_BDG", "aut bdg", "budget authority"])),
        "aut_imp": safe_string(_get(["AUT_IMP", "aut imp", "implementation authority"])),
        "type_cpte": safe_string(_get(["TYPE_CPTE", "type compte", "account type"])),
        "auxil": safe_string(_get(["AUXIL", "auxiliaire", "auxiliary"])),
        "let": safe_string(_get(["LET", "lettre", "letter"])),
        "created_at": datetime.utcnow(),
    }


def map_revenue_objective_record(record: dict, file_upload_id: int = None) -> dict:
    """Map a revenue objective record to database dictionary"""

    def _get(keywords: list, default=None):
        for key in record.keys():
            if any(normalize_column_name(kw) in normalize_column_name(key) for kw in keywords):
                return record.get(key, default)
        for kw in keywords:
            if kw in record:
                return record.get(kw, default)
        return default

    dot_name = safe_string(_get(["DOT", "dot name", "organisation"]))
    objectif_ca = safe_float(_get(["Objectif C.A", "objectif", "objective", "target"]))
    
    # Log mapping for debugging
    logger.debug(f"📋 Mapping revenue objective: dot_name='{dot_name}', objectif_ca={objectif_ca}")
    
    return {
        "file_upload_id": file_upload_id,
        "dot_name": dot_name,
        "objectif_ca": objectif_ca,
        "created_at": datetime.utcnow(),
    }


def get_revenue_journal_mapping():
    """Get the mapping for revenue journal"""
    return REVENUE_JOURNAL_TO_DB


def get_account_description_mapping():
    """Get the mapping for account descriptions"""
    return ACCOUNT_DESCRIPTION_TO_DB


def get_revenue_objective_mapping():
    """Get the mapping for revenue objectives"""
    return REVENUE_OBJECTIVE_TO_DB


if __name__ == "__main__":
    print("=" * 80)
    print("REVENUE COLUMN MAPPINGS")
    print("=" * 80)

    print("\n1. Revenue Journal Mapping:")
    for header, db_field in REVENUE_JOURNAL_TO_DB.items():
        print(f"  {header:40} -> {db_field}")

    print("\n2. Account Description Mapping:")
    for header, db_field in ACCOUNT_DESCRIPTION_TO_DB.items():
        print(f"  {header:40} -> {db_field}")

    print("\n3. Revenue Objective Mapping:")
    for header, db_field in REVENUE_OBJECTIVE_TO_DB.items():
        print(f"  {header:40} -> {db_field}")

    print("\n" + "=" * 80)
