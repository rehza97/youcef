#!/usr/bin/env python3
"""
Revenue (Chiffre d'Affaires AR DOT) Column Mapping
Maps actual revenue file headers to database fields for 3 different file types
"""

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, date
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
    """Safely convert value to string, handling NaN, None, and empty values"""
    # Handle None first
    if value is None:
        return None
    
    # Handle pandas NaN/NaT values
    if pd.isna(value):
        return None
    
    # Convert to string and strip whitespace
    text = str(value).strip()
    
    # Check if it's empty or represents a null value
    if not text or text.lower() in ['nan', 'none', 'null', 'nat', '']:
        return None
    
    # If the original value was numeric NaN (like float('nan')), don't convert to string
    if isinstance(value, float) and pd.isna(value):
        return None
    
    return text


def smart_parse_numeric(value: Any) -> Optional[float]:
    """
    Intelligently parse numeric values handling multiple formats:
    - French format: 1.234.567,89 (dots=thousands, comma=decimal)
    - Mixed dots: 1.234.567.89 (dots for both, last dot is decimal)
    - US format: 1,234,567.89 (commas=thousands, dot=decimal)
    - Standard: 1234567.89
    """
    if value is None or pd.isna(value):
        return None
    
    text = str(value).strip()
    if not text or text.lower() in ['nan', 'none', 'null', '']:
        return None
    
    # Handle negative numbers
    is_negative = text.startswith('-')
    if is_negative:
        text = text[1:]
    
    try:
        # Case 1: Has comma - French format (dots=thousands, comma=decimal)
        if ',' in text:
            # Remove all dots (thousands separators), replace comma with dot
            cleaned = text.replace('.', '').replace(',', '.')
            result = float(cleaned)
            return -result if is_negative else result
        
        # Case 2: Has dots but no comma - need to detect decimal position
        if '.' in text:
            parts = text.rsplit('.', 1)  # Split from right, keep last part
            
            # Check if last part after dot has 2 digits (likely decimals)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
                # Last dot is decimal separator
                # Remove all other dots (thousands separators) from integer part
                integer_part = parts[0].replace('.', '')
                cleaned = integer_part + '.' + parts[1]
                result = float(cleaned)
                return -result if is_negative else result
            else:
                # All dots are thousands separators
                cleaned = text.replace('.', '')
                result = float(cleaned)
                return -result if is_negative else result
        
        # Case 3: No separators - just parse directly
        result = float(text)
        return -result if is_negative else result
        
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse numeric value '{value}': {e}")
        return None


def safe_float(value: Any, max_value: Optional[float] = None, min_value: Optional[float] = None) -> Optional[float]:
    """
    Safely convert value to float, handling multiple numeric formats intelligently.
    
    IMPORTANT:
    - If value is already a numeric type (int/float), we **do not** re-parse it as a string.
      This avoids scaling errors when values have already been cleaned earlier in the pipeline
      (e.g. DataFrame numeric columns).
    - For string inputs, we use smart_parse_numeric to handle French formats and mixed dots.
    """
    # 1) Handle already-numeric values first (from cleaned DataFrame)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Treat pandas NaN as None
        try:
            if pd.isna(value):  # type: ignore[arg-type]
                return None
        except Exception:
            pass
        float_value = float(value)
    else:
        # 2) Handle string/other inputs via smart parsing
        float_value = smart_parse_numeric(value)
        if float_value is None:
            return None
    
    # 3) Clamp to valid range if specified
    if max_value is not None and float_value > max_value:
        logger.warning(f"Float value {float_value} exceeds maximum {max_value}, clamping")
        return max_value
    if min_value is not None and float_value < min_value:
        logger.warning(f"Float value {float_value} below minimum {min_value}, clamping")
        return min_value
    
    return float_value


def safe_date(value: Any) -> Optional[date]:
    """
    Safely convert value to date - handles multiple formats:
    - Date/datetime objects
    - Date strings (various formats)
    - Numeric values (Excel date serial numbers)
    """
    if value is None or pd.isna(value):
        return None
    
    # If already a date object, return as-is
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    
    # If already a datetime object, extract date part
    if isinstance(value, (datetime, pd.Timestamp)):
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            dt = value.to_pydatetime()
        else:
            dt = value
        return dt.date() if hasattr(dt, 'date') else date(dt.year, dt.month, dt.day)
    
    # Handle numeric values (Excel date serial numbers)
    # Excel dates: 1 = January 1, 1900, but Excel incorrectly treats 1900 as leap year
    # Excel epoch: January 1, 1900 = day 1
    if isinstance(value, (int, float)):
        try:
            # Excel date serial number (days since 1899-12-30)
            excel_epoch = date(1899, 12, 30)  # Excel's epoch (adjusted for leap year bug)
            days = int(value)
            result_date = excel_epoch + pd.Timedelta(days=days)
            parsed_date = result_date.date() if hasattr(result_date, 'date') else result_date
            logger.debug(f"📅 Converted Excel serial {value} → {parsed_date}")
            return parsed_date
        except (ValueError, OverflowError, OSError) as e:
            logger.warning(f"⚠️ Failed to convert numeric date {value}: {e}")
            return None
    
    # Handle string values
    text = str(value).strip()
    if not text or text.lower() in ['nan', 'none', 'null', 'nat', '']:
        return None
    
    # Try to parse as number first (in case it's a string representation of Excel date)
    try:
        num_value = float(text)
        if num_value > 0 and num_value < 1000000:  # Reasonable Excel date range
            excel_epoch = date(1899, 12, 30)
            days = int(num_value)
            result_date = excel_epoch + pd.Timedelta(days=days)
            parsed_date = result_date.date() if hasattr(result_date, 'date') else result_date
            logger.debug(f"📅 Converted string Excel serial '{text}' → {parsed_date}")
            return parsed_date
    except (ValueError, TypeError):
        pass  # Not a number, continue with string parsing
    
    try:
        # Try parsing as pandas datetime first (handles most formats automatically)
        # Use dayfirst=True for French date format (dd/mm/yyyy)
        result = pd.to_datetime(text, errors="coerce", dayfirst=True)
        # Check if result is NaT (Not a Time)
        if pd.isna(result):
            # Try without dayfirst as fallback
            result = pd.to_datetime(text, errors="coerce", dayfirst=False)
            if pd.isna(result):
                logger.debug(f"Date parsing failed for '{text}': could not parse as date string")
                return None
        
        # Convert to date object
        dt = result.to_pydatetime()
        parsed_date = dt.date() if hasattr(dt, 'date') else date(dt.year, dt.month, dt.day)
        logger.debug(f"📅 Parsed date string '{text}' → {parsed_date}")
        return parsed_date
    except Exception as e:
        logger.warning(f"⚠️ Date parsing failed for '{text}': {e}")
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
        """Get value from record by finding column with keywords (exact match first, then substring)"""
        # Try exact match first (case-insensitive)
        for kw in keywords:
            for key in record.keys():
                if normalize_column_name(kw) == normalize_column_name(key):
                    return record.get(key, default)

        # Then try substring match
        for key in record.keys():
            if any(normalize_column_name(kw) in normalize_column_name(key) for kw in keywords):
                return record.get(key, default)

        return default

    # Maximum value for NUMERIC(15, 2): 9,999,999,999,999.99 (13 digits before decimal, 2 after)
    MAX_NUMERIC_15_2 = 9999999999999.99
    MIN_NUMERIC_15_2 = -9999999999999.99
    
    # Maximum value for NUMERIC(15, 4): 99,999,999,999.9999 (11 digits before decimal, 4 after)
    # This is used for qte (quantity) field
    MAX_NUMERIC_15_4 = 99999999999.9999
    MIN_NUMERIC_15_4 = -99999999999.9999
    
    # Maximum value for NUMERIC(15, 6): 999,999,999.999999 (9 digits before decimal, 6 after)
    # This is used for taux_change (exchange rate) field
    MAX_NUMERIC_15_6 = 999999999.999999
    MIN_NUMERIC_15_6 = -999999999.999999

    return {
        "file_upload_id": file_upload_id,
        "org_name": safe_string(_get(["Org Name", "org name", "organisation"])),
        "origine": safe_string(_get(["Origine", "origin"])),
        "n_fact": safe_string(_get(["N Fact", "numero facture", "invoice number"])),
        "typ_fact": safe_string(_get(["Typ Fact", "type facture", "invoice type"])),
        "date_fact": safe_date(_get(["Date Fact", "date facture", "date fact", "date_fact", "datefact", "date invoice"])),
        "n_client": safe_string(_get(["N Client", "numero client", "customer number"])),
        "client": safe_string(_get(["Client", "customer"])),
        "delai_paie": safe_string(_get(["Delai Paie", "payment delay"])),
        "devise": safe_string(_get(["Devise", "currency"])),
        "obj_fact": safe_string(_get(["Obj Fact", "objet facture", "invoice object"])),
        "cpt_comptable": safe_string(_get(["Cpt Comptable", "compte comptable", "account code"])),
        "date_facture_gl": safe_date(_get(["Date facture GL", "gl invoice date", "date facture gl", "date_facture_gl", "datefacturegl"])),
        "date_gl": safe_date(_get(["Date GL", "gl date", "date gl", "date_gl", "dategl", "date gl gl"])),
        "periode_de_facturation": safe_string(_get(["Periode de facturation", "billing period", "periode de facturation", "periode", "period", "billing"])),
        # Note: If value is NaN/empty in source, safe_string will return None (NULL in DB)
        "reference": safe_string(_get(["Reference", "ref"])),
        "termine_flag": safe_boolean(_get(["Termine Flag", "terminated"])),
        # Monetary fields with NUMERIC(15, 2) clamping
        "tax_amount": safe_float(_get(["Tax Amount", "montant taxe"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "creer_par": safe_string(_get(["Creer Par", "created by"])),
        "n_ligne": safe_string(_get(["N Ligne", "line number"])),
        "description_ligne_de_produit": safe_string(_get(["Description (ligne de produit)", "product line description", "description ligne"])),
        "uom": safe_string(_get(["Uom", "unit of measure", "unite"])),
        # qte uses NUMERIC(15, 4) in database, so it needs different validation
        "qte": safe_float(_get(["Qte", "quantity", "quantite"]), max_value=MAX_NUMERIC_15_4, min_value=MIN_NUMERIC_15_4),
        "prix_uni": safe_float(_get(["Prix Uni", "unit price", "prix unitaire"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        # taux_change uses NUMERIC(15, 6) in database, so it needs different validation
        "taux_change": safe_float(_get(["Taux Change", "exchange rate", "taux", "taux change", "taux_change", "tauxchange", "rate", "exchange"]), max_value=MAX_NUMERIC_15_6, min_value=MIN_NUMERIC_15_6),
        "mnt_ht": safe_float(_get(["Mnt Ht", "montant ht", "amount excluding tax"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "tax": safe_string(_get(["Tax", "taxe"])),
        "mnt_tax": safe_float(_get(["Mnt Tax", "montant tax", "tax amount"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "mnt_ttc": safe_float(_get(["Mnt Ttc", "montant ttc", "amount including tax"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "memo_line_id": safe_string(_get(["Memo Line Id", "memo", "memo line id", "memo_line_id", "memolineid", "memo id", "line id"])),
        "chiffre_aff_exe_dzd": safe_float(_get(["Chiffre Aff Exe Dzd", "chiffre affaires", "revenue dzd"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        # Calculated columns - clamp to NUMERIC(10, 4) range: -999999.9999 to 999999.9999
        "tva": safe_float(_get(["TVA", "tva", "vat"]), max_value=999999.9999, min_value=-999999.9999),
        "chiffre_aff_exe_dzd_ttc": safe_float(_get(["Chiffre_Aff_Exe_Dzd_TTC", "ca ttc", "revenue ttc"]), max_value=MAX_NUMERIC_15_2, min_value=MIN_NUMERIC_15_2),
        "taux_realisation_ca": safe_float(_get(["Taux_Realisation_CA", "achievement rate", "taux realisation"]), max_value=999999.9999, min_value=-999999.9999),
        # Matched relationships (will be set after matching)
        # account_description_id is set from Account_Description object in processing
        "account_description_id": None,  # Will be set from Account_Description object
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
    
    # Clean DOT name: remove separators (-, –, _) and DOT_ prefix
    if dot_name:
        import re
        # Remove DOT_ prefix
        dot_name = re.sub(r'^DOT[_\s]+', '', dot_name, flags=re.IGNORECASE)
        # Replace -, – and _ with spaces
        dot_name = dot_name.replace('-', ' ').replace('–', ' ').replace('_', ' ')
        # Normalize whitespace
        dot_name = re.sub(r'\s+', ' ', dot_name).strip()
    
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
