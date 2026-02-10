"""
Revenue Processing Helper Methods
Additional helper methods for revenue processing service
"""

import pandas as pd
from typing import Optional, Dict, Any, List
import logging
import re
import math

logger = logging.getLogger(__name__)

# Numeric columns for revenue anomaly export (French headers + snake_case from DB/JSON)
REVENUE_ANOMALY_NUMERIC_COLS = {
    "Qte", "qte", "Prix Uni", "prix_uni", "Taux Change", "taux_change",
    "Mnt Ht", "mnt_ht", "Mnt Tax", "mnt_tax", "Mnt Ttc", "mnt_ttc",
    "Tax Amount", "tax_amount", "Chiffre Aff Exe Dzd", "chiffre_aff_exe_dzd",
    "Chiffre Aff Exe Dzd TTC", "chiffre_aff_exe_dzd_ttc",
    "TVA", "tva", "Taux Réalisation CA (%)", "taux_realisation_ca",
    "Taux de réalisation C.A",
}


class RevenueProcessingHelpers:
    """Helper methods for revenue processing"""

    @staticmethod
    def _find_column(df: pd.DataFrame, keywords: list) -> Optional[str]:
        """Find a column by keywords"""
        def normalize(s):
            return str(s).lower().replace('_', ' ').replace('-', ' ').strip()

        # Try exact match
        for col in df.columns:
            if col in keywords:
                return col

        # Try normalized match
        for col in df.columns:
            col_norm = normalize(col)
            if any(normalize(kw) in col_norm for kw in keywords):
                return col

        return None

    @staticmethod
    def sort_by_org_type_invoice(df: pd.DataFrame,
                                   org_col: str = None,
                                   type_col: str = None,
                                   invoice_col: str = None) -> pd.DataFrame:
        """Sort by Org Name, Type Fact, N Fact"""
        sort_columns = []

        if not org_col:
            org_col = RevenueProcessingHelpers._find_column(
                df, ['Org Name', 'organisation'])
        if org_col and org_col in df.columns:
            sort_columns.append(org_col)

        if not type_col:
            type_col = RevenueProcessingHelpers._find_column(
                df, ['Typ Fact', 'type facture', 'invoice type'])
        if type_col and type_col in df.columns:
            sort_columns.append(type_col)

        if not invoice_col:
            invoice_col = RevenueProcessingHelpers._find_column(
                df, ['N Fact', 'numero facture', 'invoice number'])
        if invoice_col and invoice_col in df.columns:
            sort_columns.append(invoice_col)

        if sort_columns:
            df = df.sort_values(by=sort_columns, na_position='last')

        return df

    @staticmethod
    def detect_anomalies_in_row(row: pd.Series, cpt_col: str, desc_col: str) -> Optional[str]:
        """
        Detect anomalies: Cpt Comptable contains letter 'A' (case-insensitive)
        Returns anomaly reason if found, None otherwise
        """
        cpt_value = str(row.get(cpt_col, ''))

        # Check if Cpt Comptable contains letter 'A' (case-insensitive)
        if 'A' in cpt_value.upper():
            return f"Cpt Comptable '{cpt_value}' contains letter 'A'"

        return None

    @staticmethod
    def detect_reprise_in_row(row: pd.Series, origine_col: str) -> Optional[str]:
        """
        Detect REPRISE anomaly: Origine contains 'REPRISE' (case-insensitive).
        Example: '20_REPRISE ALGER_EST' -> anomaly.
        Returns anomaly reason if found, None otherwise.
        """
        if not origine_col:
            return None
        origine_value = str(row.get(origine_col, ''))
        if 'REPRISE' in origine_value.upper():
            return f"Origine '{origine_value}' contains 'REPRISE'"
        return None

    @staticmethod
    def filter_cpt_comptable_with_a(df: pd.DataFrame, cpt_col: str) -> pd.DataFrame:
        """Remove rows where Cpt Comptable contains letter 'A'"""
        original = len(df)
        df = df[~df[cpt_col].astype(str).str.contains('A', case=False, na=False)]
        filtered = original - len(df)
        if filtered > 0:
            logger.info(f"Filtered {filtered} rows with 'A' in Cpt Comptable")
        return df

    @staticmethod
    def filter_reprise_rows(df: pd.DataFrame, origine_col: str) -> pd.DataFrame:
        """Remove rows where Origine contains 'REPRISE'"""
        if not origine_col or origine_col not in df.columns:
            return df
        original = len(df)
        df = df[~df[origine_col].astype(str).str.contains('REPRISE', case=False, na=False)]
        filtered = original - len(df)
        if filtered > 0:
            logger.info(f"Filtered {filtered} rows with 'REPRISE' in Origine")
        return df

    @staticmethod
    def keep_most_recent_year(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        """Keep only rows with the most recent year in Date GL"""
        if date_col not in df.columns:
            return df

        # Convert to datetime with dayfirst=True for French date format (dd/mm/yyyy)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)

        # Extract year from the journal table data
        years = df[date_col].dt.year.dropna()
        if len(years) == 0:
            logger.warning("⚠️ No valid years found in Date GL column")
            return df

        # Log all years found in the journal table
        unique_years = sorted(years.unique())
        year_counts = years.value_counts().sort_index()
        logger.info(f"📅 Years found in journal table: {unique_years}")
        logger.info(f"📅 Year distribution: {dict(year_counts)}")
        
        # Determine most recent year from the journal table data
        most_recent_year = years.max()
        logger.info(f"📅 Keeping only year {most_recent_year} (most recent year found in journal table)")

        original = len(df)
        
        # Calculate CA sum lost from year filter
        ca_col = RevenueProcessingHelpers._find_column(df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
        if ca_col:
            try:
                year_mask = df[date_col].dt.year == most_recent_year
                valid_date_mask = df[date_col].notna()
                filtered_mask = ~(year_mask & valid_date_mask)
                filtered_rows = df[filtered_mask]
                ca_numeric = pd.to_numeric(filtered_rows[ca_col], errors='coerce')
                filtered_ca_sum = ca_numeric.sum()
                if not pd.isna(filtered_ca_sum) and filtered_ca_sum != 0:
                    logger.info(f"   💰 CA Sum lost from year filter: {filtered_ca_sum:,.2f} DZD")
            except Exception as e:
                logger.debug(f"   Could not calculate CA sum lost from year filter: {e}")
        
        # Filter: keep only rows with most recent year AND valid date (not NaT)
        year_mask = df[date_col].dt.year == most_recent_year
        valid_date_mask = df[date_col].notna()
        
        # Log detailed breakdown before filtering
        if len(unique_years) > 1:
            logger.info(f"📅 Filtering breakdown:")
            for year in unique_years:
                year_rows = (df[date_col].dt.year == year).sum()
                logger.info(f"   - Year {year}: {year_rows} rows")
            invalid_rows = (~valid_date_mask).sum()
            if invalid_rows > 0:
                logger.info(f"   - Invalid dates: {invalid_rows} rows")
        
        df = df[year_mask & valid_date_mask]
        filtered = original - len(df)
        
        if filtered > 0:
            logger.info(f"Filtered {filtered} rows from older years or with invalid dates")
            # Log count of invalid dates
            invalid_dates = (~valid_date_mask).sum()
            if invalid_dates > 0:
                logger.warning(f"   ⚠️ Found {invalid_dates} rows with invalid dates that were filtered")
            # Log how many rows kept for the most recent year
            kept_rows = (year_mask & valid_date_mask).sum()
            logger.info(f"   ✅ Kept {kept_rows} rows from year {most_recent_year}")

        return df

    @staticmethod
    def smart_parse_numeric(value: Any) -> Optional[float]:
        """
        Intelligently parse numeric values handling multiple formats:
        - French format: 1.234.567,89 or 1 234 567,89 (dots/spaces=thousands, comma=decimal)
        - Mixed dots: 1.234.567.89 (dots for both, last dot is decimal)
        - US format: 1,234,567.89 (commas=thousands, dot=decimal)
        - Standard: 1234567.89
        - Already parsed floats: returns as-is
        
        CRITICAL: Always converts French format (comma as decimal) to standard format (dot as decimal)
        Handles spaces as thousands separators: "6 496 318 295,77" -> 6496318295.77
        """
        # Handle None and NaN first
        if value is None or pd.isna(value):
            return None
        
        # If already a numeric type (float/int), return as-is (already parsed correctly)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            # Check if it's a pandas NaN
            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass
            return float(value)
        
        # Convert to string for parsing
        text = str(value).strip()
        if not text or text.lower() in ['nan', 'none', 'null', '']:
            return None
        
        # Handle negative numbers
        is_negative = text.startswith('-')
        if is_negative:
            text = text[1:]
        
        try:
            # Case 1: Has comma - French format (dots/spaces=thousands, comma=decimal)
            # This is the most common case for French Excel files
            # Examples: "1.234.567,89" or "1 234 567,89" or "6 496 318 295,77"
            if ',' in text:
                comma_count = text.count(',')
                if comma_count > 1:
                    # Multi-comma values like "1,411,997":
                    # Treat the LAST comma as decimal separator and earlier commas as thousands separators.
                    parts = text.split(',')
                    integer_part = ''.join(parts[:-1])
                    decimal_part = parts[-1]
                    cleaned_int = integer_part.replace('.', '').replace(' ', '').replace(',', '')
                    cleaned_dec = decimal_part.replace(' ', '')
                    cleaned = f"{cleaned_int}.{cleaned_dec}" if cleaned_dec else cleaned_int
                else:
                    # Remove all dots and spaces (thousands separators), replace comma with dot
                    cleaned = text.replace('.', '').replace(' ', '').replace(',', '.')
                result = float(cleaned)
                return -result if is_negative else result
            
            # Case 2: Has dots but no comma - need to detect decimal position
            if '.' in text:
                parts = text.rsplit('.', 1)  # Split from right, keep last part
                
                # Check if last part after dot has 2 digits (likely decimals)
                if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
                    # Last dot is decimal separator
                    # Remove all other dots and spaces (thousands separators) from integer part
                    integer_part = parts[0].replace('.', '').replace(' ', '')
                    cleaned = integer_part + '.' + parts[1]
                    result = float(cleaned)
                    return -result if is_negative else result
                else:
                    # All dots are thousands separators
                    cleaned = text.replace('.', '').replace(' ', '')
                    result = float(cleaned)
                    return -result if is_negative else result
            
            # Case 2b: Has spaces but no dots or comma - remove spaces and parse
            if ' ' in text:
                cleaned = text.replace(' ', '')
                result = float(cleaned)
                return -result if is_negative else result
            
            # Case 3: No separators - just parse directly
            result = float(text)
            return -result if is_negative else result
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse numeric value '{value}': {e}")
            return None

    @staticmethod
    def clean_numeric_field(df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Clean numeric field handling multiple formats intelligently"""
        if col not in df.columns:
            return df

        df[col] = df[col].apply(RevenueProcessingHelpers.smart_parse_numeric)
        return df

    @staticmethod
    def calculate_tva(df: pd.DataFrame,
                       mnt_ttc_col: str,
                       mnt_ht_col: str,
                       tva_col: str = 'TVA') -> pd.DataFrame:
        """
        Calculate TVA = Mnt Ttc / Mnt Ht
        Limit to NUMERIC(10, 4) range: -999999.9999 to 999999.9999
        Handle division by zero and very small denominators
        """
        if mnt_ttc_col not in df.columns or mnt_ht_col not in df.columns:
            logger.warning(
                "Cannot calculate TVA: required columns not found")
            return df

        # Maximum value for NUMERIC(10, 4): 999999.9999
        MAX_TVA = 999999.9999
        MIN_TVA = -999999.9999
        MIN_DENOMINATOR = 0.0001  # Minimum denominator to avoid extreme values

        def calc_tva(row):
            ttc = row.get(mnt_ttc_col)
            ht = row.get(mnt_ht_col)

            if pd.isna(ttc) or pd.isna(ht):
                return 0.00  # RULE: Replace #DIV/0! with 0.00

            try:
                ttc = float(ttc)
                ht = float(ht)

                # Handle division by zero or very small denominators
                # RULE: Replace #DIV/0! with 0.00
                if abs(ht) < MIN_DENOMINATOR:
                    # If denominator is too small, return 0.00 (not None)
                    return 0.00

                tva_value = ttc / ht
                
                # Clamp to valid range for NUMERIC(10, 4)
                if tva_value > MAX_TVA:
                    logger.warning(f"TVA value {tva_value} exceeds maximum {MAX_TVA}, clamping")
                    return MAX_TVA
                elif tva_value < MIN_TVA:
                    logger.warning(f"TVA value {tva_value} below minimum {MIN_TVA}, clamping")
                    return MIN_TVA
                
                return round(tva_value, 4)  # Round to 4 decimal places
            except (ValueError, TypeError, ZeroDivisionError):
                # RULE: Replace #DIV/0! with 0.00
                return 0.00

        df[tva_col] = df.apply(calc_tva, axis=1)
        return df

    @staticmethod
    def calculate_ca_ttc(df: pd.DataFrame,
                          ca_col: str,
                          tva_col: str = 'TVA',
                          ca_ttc_col: str = 'Chiffre_Aff_Exe_Dzd_TTC') -> pd.DataFrame:
        """
        Calculate Chiffre Aff Exe Dzd TTC = CA * TVA
        Limit to NUMERIC(15, 2) range: -9999999999999.99 to 9999999999999.99
        """
        logger.info(f"   🔢 calculate_ca_ttc: Starting calculation")
        logger.info(f"      - Input CA column: '{ca_col}'")
        logger.info(f"      - Input TVA column: '{tva_col}'")
        logger.info(f"      - Output column: '{ca_ttc_col}'")

        if ca_col not in df.columns or tva_col not in df.columns:
            logger.warning(
                "Cannot calculate CA TTC: required columns not found")
            return df

        # Maximum value for NUMERIC(15, 2): 9,999,999,999,999.99 (about 10 trillion)
        MAX_CA_TTC = 9999999999999.99
        MIN_CA_TTC = -9999999999999.99

        # Track statistics
        null_ca_count = 0
        null_tva_count = 0
        success_count = 0
        error_count = 0
        clamped_count = 0

        def calc_ca_ttc(row):
            nonlocal null_ca_count, null_tva_count, success_count, error_count, clamped_count

            ca = row.get(ca_col)
            tva = row.get(tva_col)

            if pd.isna(ca):
                null_ca_count += 1
                return None

            if pd.isna(tva):
                null_tva_count += 1
                return None

            try:
                ca = float(ca)
                tva = float(tva)

                ca_ttc_value = ca * tva

                # Clamp to valid range for NUMERIC(15, 2)
                if ca_ttc_value > MAX_CA_TTC:
                    logger.warning(f"CA TTC value {ca_ttc_value} exceeds maximum {MAX_CA_TTC}, clamping")
                    clamped_count += 1
                    success_count += 1
                    return MAX_CA_TTC
                elif ca_ttc_value < MIN_CA_TTC:
                    logger.warning(f"CA TTC value {ca_ttc_value} below minimum {MIN_CA_TTC}, clamping")
                    clamped_count += 1
                    success_count += 1
                    return MIN_CA_TTC

                success_count += 1
                return round(ca_ttc_value, 2)  # Round to 2 decimal places for NUMERIC(15, 2)
            except (ValueError, TypeError) as e:
                error_count += 1
                logger.debug(f"Error converting values to float: CA={ca}, TVA={tva}, Error={e}")
                return None

        logger.info(f"   🔢 Applying calculation to {len(df)} rows...")
        df[ca_ttc_col] = df.apply(calc_ca_ttc, axis=1)

        # Log statistics
        logger.info(f"   📊 Calculation complete:")
        logger.info(f"      - Successful calculations: {success_count}")
        logger.info(f"      - NULL CA values: {null_ca_count}")
        logger.info(f"      - NULL TVA values: {null_tva_count}")
        logger.info(f"      - Conversion errors: {error_count}")
        logger.info(f"      - Clamped values: {clamped_count}")
        logger.info(f"      - Total NULL results: {null_ca_count + null_tva_count + error_count}")

        return df

    @staticmethod
    def calculate_achievement_rate(df: pd.DataFrame,
                                     ca_col: str,
                                     objectif_col: str = 'Objectif_CA',
                                     rate_col: str = 'Taux_Realisation_CA') -> pd.DataFrame:
        """
        Calculate Taux de réalisation = (CA / Objectif) * 100
        Limit to NUMERIC(10, 4) range: -999999.9999 to 999999.9999
        Handle division by zero and very small denominators
        """
        if ca_col not in df.columns or objectif_col not in df.columns:
            logger.warning(
                "Cannot calculate achievement rate: required columns not found")
            return df

        # Maximum value for NUMERIC(10, 4): 999999.9999
        MAX_RATE = 999999.9999
        MIN_RATE = -999999.9999
        MIN_DENOMINATOR = 0.01  # Minimum denominator (objectif) to avoid extreme values

        def calc_rate(row):
            ca = row.get(ca_col)
            objectif = row.get(objectif_col)

            if pd.isna(ca) or pd.isna(objectif):
                return None

            try:
                ca = float(ca)
                objectif = float(objectif)

                # Handle division by zero or very small denominators
                if abs(objectif) < MIN_DENOMINATOR:
                    # If objectif is too small, return None
                    return None

                rate_value = (ca / objectif) * 100  # Return as percentage
                
                # Clamp to valid range for NUMERIC(10, 4)
                if rate_value > MAX_RATE:
                    logger.warning(f"Achievement rate {rate_value} exceeds maximum {MAX_RATE}, clamping")
                    return MAX_RATE
                elif rate_value < MIN_RATE:
                    logger.warning(f"Achievement rate {rate_value} below minimum {MIN_RATE}, clamping")
                    return MIN_RATE
                
                return round(rate_value, 4)  # Round to 4 decimal places
            except (ValueError, TypeError, ZeroDivisionError):
                return None

        df[rate_col] = df.apply(calc_rate, axis=1)
        return df

    @staticmethod
    def format_number_french(value) -> str:
        """Format number as French: space thousands + comma decimal (preserve input precision when possible)."""
        # Handle None/NaN early
        if value is None or pd.isna(value):
            return ""

        def infer_decimals_from_text(s: str) -> Optional[int]:
            s = s.strip()
            if not s:
                return None
            if ',' in s:
                # Use digits after LAST comma
                dec = s.rsplit(',', 1)[1]
                dec_digits = re.sub(r'\D', '', dec)
                return len(dec_digits) if dec_digits else 0
            # If only dot present, it might be decimal; but in French data dots are often thousands.
            # Only treat dot as decimal if there's exactly one dot and the suffix is short & numeric.
            if s.count('.') == 1:
                dec = s.rsplit('.', 1)[1]
                return len(dec) if dec.isdigit() else None
            return None

        # Parse value
        decimals: int = 2
        if isinstance(value, str):
            s = value.strip()
            s_lower = s.lower()
            if not s or s_lower in {'nan', 'none', 'null', 'nat', 'inf', '-inf'} or s_lower.startswith('nan'):
                return ""

            inferred = infer_decimals_from_text(s)
            if inferred is not None:
                decimals = min(max(inferred, 0), 6)

            parsed = RevenueProcessingHelpers.smart_parse_numeric(s)
            if parsed is None:
                # Keep original if we can't parse (don't drop/blank valid-looking strings)
                return s
            num_value = float(parsed)
        else:
            try:
                num_value = float(value)
            except (TypeError, ValueError):
                return ""

        if not math.isfinite(num_value):
            return ""

        # Format using requested precision then convert to French style
        us_format = f"{num_value:,.{decimals}f}"
        if '.' in us_format:
            int_part, dec_part = us_format.split('.', 1)
            int_part = int_part.replace(',', ' ')
            return f"{int_part},{dec_part}"
        # No decimals
        return us_format.replace(',', ' ')

    @staticmethod
    def get_numeric_columns_for_anomaly_export(df: pd.DataFrame) -> List[str]:
        """Return column names in df that are numeric for revenue anomaly export."""
        def normalize(name: str) -> str:
            # Normalize header names so variants like "Mnt Ht", "mnt_ht", "Mnt Ht "
            # all map to the same key.
            s = str(name).strip().lower()
            s = s.replace("-", " ").replace("_", " ")
            s = re.sub(r"\s+", " ", s)
            return s

        normalized_targets = {normalize(n) for n in REVENUE_ANOMALY_NUMERIC_COLS}

        numeric_cols: List[str] = []
        for col in df.columns:
            if normalize(col) in normalized_targets:
                numeric_cols.append(col)
        return numeric_cols

    @staticmethod
    def apply_french_format_to_anomaly_df(df: pd.DataFrame, for_excel: bool = False) -> pd.DataFrame:
        """
        Prepare anomaly DataFrame for export.
        
        Args:
            df: DataFrame with anomaly data
            for_excel: If True, keep numeric columns as numbers (for Excel cell formatting).
                      If False, format numeric columns as French-formatted strings (for CSV).
        
        Returns:
            DataFrame with sanitized NaN values and optionally formatted numeric columns.
        """
        numeric_cols = RevenueProcessingHelpers.get_numeric_columns_for_anomaly_export(df)
        out = df.copy()

        # Sanitize NaN-like values across ALL columns to avoid exporting "nan" strings
        # (e.g. in columns like "Tax" and "Memo Line Id").
        def _sanitize_cell(x):
            if x is None:
                return ""
            try:
                if pd.isna(x):
                    return ""
            except Exception:
                pass
            if isinstance(x, str):
                s = x.strip()
                if not s:
                    return ""
                s_lower = s.lower()
                if s_lower in {"nan", "none", "null", "nat", "inf", "-inf"} or s_lower.startswith("nan"):
                    return ""
                return s
            return x

        for col in out.columns:
            out[col] = out[col].apply(_sanitize_cell)

        if not numeric_cols:
            return out

        for col in numeric_cols:
            if col in out.columns:
                if for_excel:
                    # For Excel: parse to numbers but keep as numeric (formatting via Excel cell format)
                    out[col] = out[col].apply(
                        lambda x: RevenueProcessingHelpers.smart_parse_numeric(x) 
                        if isinstance(x, str) or pd.notna(x) else None
                    )
                else:
                    # For CSV: format as French-formatted strings
                    out[col] = out[col].apply(RevenueProcessingHelpers.format_number_french)
        return out

    @staticmethod
    def clean_org_name_for_matching(org_name: str) -> str:
        """Clean organization name for matching (remove DOT_, replace separators)"""
        if not org_name:
            return ""

        # Remove DOT_ prefix
        cleaned = re.sub(r'DOT[_\s]*', '', org_name, flags=re.IGNORECASE)

        # Replace -, – and _ with spaces
        cleaned = cleaned.replace('-', ' ').replace('–', ' ').replace('_', ' ')

        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()

        return cleaned

    @staticmethod
    def match_account_description(cpt_comptable: str,
                                    account_descriptions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Match Cpt Comptable with account descriptions"""
        if not cpt_comptable or not account_descriptions:
            return None

        cpt_clean = str(cpt_comptable).strip().upper()

        # Try exact match first
        if cpt_clean in account_descriptions:
            return account_descriptions[cpt_clean]

        # Try partial match
        for key, value in account_descriptions.items():
            if cpt_clean in key or key in cpt_clean:
                return value

        return None

    @staticmethod
    def match_revenue_objective(org_name: str,
                                 revenue_objectives: Dict[str, Any]) -> Optional[float]:
        """
        Match Org Name with revenue objectives

        NOTE: revenue_objectives dict now contains RevenueDOTCorporate objects
        (not just float values). This method extracts annual_objective for
        backward compatibility.
        """
        if not org_name or not revenue_objectives:
            return None

        # Clean org name for matching
        org_clean = RevenueProcessingHelpers.clean_org_name_for_matching(
            org_name)

        # Try exact match first
        if org_clean in revenue_objectives:
            obj = revenue_objectives[org_clean]
            # Handle both old format (float) and new format (object with annual_objective)
            return obj.annual_objective if hasattr(obj, 'annual_objective') else obj

        # Try partial match
        for key, value in revenue_objectives.items():
            key_clean = RevenueProcessingHelpers.clean_org_name_for_matching(
                key)
            if org_clean in key_clean or key_clean in org_clean:
                # Handle both old format (float) and new format (object with annual_objective)
                return value.annual_objective if hasattr(value, 'annual_objective') else value

        return None

    @staticmethod
    def generate_pivot_table(df: pd.DataFrame,
                              values: str,
                              index: List[str],
                              aggfunc: str = 'sum') -> pd.DataFrame:
        """Generate pivot table (TCD - Tableau Croisé Dynamique)"""
        try:
            pivot = pd.pivot_table(
                df,
                values=values,
                index=index,
                aggfunc=aggfunc,
                fill_value=0
            )
            return pivot
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return pd.DataFrame()

    @staticmethod
    def apply_date_filters(df: pd.DataFrame,
                            date_col: str,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """Apply date range filters"""
        if date_col not in df.columns:
            return df

        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

        if start_date:
            start = pd.to_datetime(start_date)
            df = df[df[date_col] >= start]

        if end_date:
            end = pd.to_datetime(end_date)
            df = df[df[date_col] <= end]

        return df

    @staticmethod
    def apply_multi_select_filter(df: pd.DataFrame,
                                    col: str,
                                    values: List[Any]) -> pd.DataFrame:
        """Apply multi-select filter"""
        if col not in df.columns or not values:
            return df

        return df[df[col].isin(values)]

    @staticmethod
    def calculate_statistics(df: pd.DataFrame,
                               group_by: List[str],
                               agg_cols: Dict[str, str]) -> pd.DataFrame:
        """Calculate aggregated statistics"""
        try:
            stats = df.groupby(group_by).agg(agg_cols).reset_index()
            return stats
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return pd.DataFrame()
