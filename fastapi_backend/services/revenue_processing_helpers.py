"""
Revenue Processing Helper Methods
Additional helper methods for revenue processing service
"""

import pandas as pd
from typing import Optional, Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)


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
        Detect anomalies: Cpt Comptable contains 'A' AND Description doesn't start with '@'
        Returns anomaly reason if found, None otherwise
        """
        cpt_value = str(row.get(cpt_col, ''))
        desc_value = str(row.get(desc_col, ''))

        # Check if Cpt Comptable contains letter 'A'
        if 'A' in cpt_value.upper():
            # Check if Description starts with '@'
            if not desc_value.strip().startswith('@'):
                return f"Cpt Comptable '{cpt_value}' contains 'A' but description doesn't start with '@'"

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
    def keep_most_recent_year(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        """Keep only rows with the most recent year in Date GL"""
        if date_col not in df.columns:
            return df

        # Convert to datetime with dayfirst=True for French date format (dd/mm/yyyy)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)

        # Extract year
        years = df[date_col].dt.year.dropna()
        if len(years) == 0:
            return df

        most_recent_year = years.max()
        logger.info(f"Keeping only year {most_recent_year}")

        original = len(df)
        df = df[df[date_col].dt.year == most_recent_year]
        filtered = original - len(df)
        if filtered > 0:
            logger.info(
                f"Filtered {filtered} rows from older years")

        return df

    @staticmethod
    def clean_numeric_field(df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Clean numeric field by removing dots (thousands separator)"""
        if col not in df.columns:
            return df

        def clean_number(val):
            if pd.isna(val):
                return None
            try:
                # Convert to string, remove dots, replace comma with dot
                s = str(val).replace('.', '').replace(',', '.')
                return float(s) if s else None
            except:
                return None

        df[col] = df[col].apply(clean_number)
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
                return None

            try:
                ttc = float(ttc)
                ht = float(ht)

                # Handle division by zero or very small denominators
                if abs(ht) < MIN_DENOMINATOR:
                    # If denominator is too small, return None or 0
                    return None

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
                return None

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
        if ca_col not in df.columns or tva_col not in df.columns:
            logger.warning(
                "Cannot calculate CA TTC: required columns not found")
            return df

        # Maximum value for NUMERIC(15, 2): 9,999,999,999,999.99 (about 10 trillion)
        MAX_CA_TTC = 9999999999999.99
        MIN_CA_TTC = -9999999999999.99

        def calc_ca_ttc(row):
            ca = row.get(ca_col)
            tva = row.get(tva_col)

            if pd.isna(ca) or pd.isna(tva):
                return None

            try:
                ca = float(ca)
                tva = float(tva)

                ca_ttc_value = ca * tva

                # Clamp to valid range for NUMERIC(15, 2)
                if ca_ttc_value > MAX_CA_TTC:
                    logger.warning(f"CA TTC value {ca_ttc_value} exceeds maximum {MAX_CA_TTC}, clamping")
                    return MAX_CA_TTC
                elif ca_ttc_value < MIN_CA_TTC:
                    logger.warning(f"CA TTC value {ca_ttc_value} below minimum {MIN_CA_TTC}, clamping")
                    return MIN_CA_TTC

                return round(ca_ttc_value, 2)  # Round to 2 decimal places for NUMERIC(15, 2)
            except (ValueError, TypeError):
                return None

        df[ca_ttc_col] = df.apply(calc_ca_ttc, axis=1)
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
    def format_number_french(value: float) -> str:
        """Format number with thousands separator and 2 decimal places (French format)"""
        if pd.isna(value):
            return ""

        try:
            value = float(value)
            # Format with 2 decimals
            formatted = f"{value:,.2f}"
            # Replace , with space for thousands, and . with , for decimal
            formatted = formatted.replace(',', ' ').replace('.', ',')
            return formatted
        except:
            return str(value)

    @staticmethod
    def clean_org_name_for_matching(org_name: str) -> str:
        """Clean organization name for matching (remove DOT_, replace separators)"""
        if not org_name:
            return ""

        # Remove DOT_ prefix
        cleaned = re.sub(r'DOT[_\s]*', '', org_name, flags=re.IGNORECASE)

        # Replace – and _ with spaces
        cleaned = cleaned.replace('–', ' ').replace('_', ' ')

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
        """Match Org Name with revenue objectives"""
        if not org_name or not revenue_objectives:
            return None

        # Clean org name for matching
        org_clean = RevenueProcessingHelpers.clean_org_name_for_matching(
            org_name)

        # Try exact match first
        if org_clean in revenue_objectives:
            return revenue_objectives[org_clean]

        # Try partial match
        for key, value in revenue_objectives.items():
            key_clean = RevenueProcessingHelpers.clean_org_name_for_matching(
                key)
            if org_clean in key_clean or key_clean in org_clean:
                return value

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
