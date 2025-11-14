"""
Créance Périodique DOT ETL Processor
Processes periodic debt files with DOT-based filtering and aggregation
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os
import re
from sqlalchemy.orm import Session

from .base import BaseETLProcessor, ETLResult, ETLStep, ETLStepType
from models.creance import CreancePeriodiqueDot, CreanceAggregateView
from models.dot import DOT

logger = logging.getLogger(__name__)


class CreancePeriodiqueDotETL(BaseETLProcessor):
    """
    ETL Processor for Créance Périodique DOT files

    Implements 10 business rules:
    1. DOT: Replace _ with space
    2. CUST_LEV1: Remove lines containing Residential, Startup PME TPE, VIP-AT
    3. CUST_LEV2: Remove lines containing Scolaires, Convention, KMS, PME
    4. CUST_LEV2: Replace Ã© with é
    5. CUST_LEV3: Remove lines containing "Ligne d'exploitation AT"
    6. CUST_LEV3: Replace Ã© with é
    7. PRODUIT: Remove lines containing ADSL, FTTX, PSTN, VOIP, X25, XDSL
    8. PRODUIT: Replace LS with "Specialized Line"
    9. Add thousand separators to all amount fields
    10. Create period_key (YYYY-MM) from ANNEE and MOIS
    """

    def __init__(self):
        super().__init__()
        self.kpi_type = "creance_periodique_dot"
        self.required_columns = [
            'DOT', 'ACTEL', 'MOIS', 'ANNEE', 'PRODUIT',
            'CUST_LEV1', 'CUST_LEV2', 'CUST_LEV3',
            'INVOICE_AMT', 'CREANCE_NET'
        ]

    def run_etl(
        self,
        input_paths: List[str],
        file_upload_id: Optional[int] = None,
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Main ETL pipeline with 7 steps

        Args:
            input_paths: List of file paths to process
            file_upload_id: Optional file upload ID for tracking
            db_session: Optional database session for persistence

        Returns:
            Dictionary with ETL results and statistics
        """
        result = {
            "success": False,
            "kpi_type": self.kpi_type,
            "file_upload_id": file_upload_id,
            "original_rows": 0,
            "processed_rows": 0,
            "filtered_rows": 0,
            "steps_completed": [],
            "errors": [],
            "warnings": [],
            "statistics": {},
            "output_file": None,
            "database_save": None
        }

        try:
            logger.info(f"Starting Créance Périodique DOT ETL for {len(input_paths)} file(s)")

            # Step 1: Ingest
            df = self._ingest_step(input_paths, result)
            if df is None or df.empty:
                result["errors"].append("No data loaded from input files")
                return result

            result["original_rows"] = len(df)
            result["steps_completed"].append("ingest")
            logger.info(f"Ingest complete: {len(df)} rows loaded")

            # Step 2: Clean
            df = self._clean_step(df, result)
            if df is None or df.empty:
                result["warnings"].append("All data filtered out during cleaning")
                return result

            result["steps_completed"].append("clean")
            logger.info(f"Clean complete: {len(df)} rows remaining")

            # Step 3: Validate
            df = self._validate_step(df, result)
            result["steps_completed"].append("validate")

            # Step 4: Transform
            df = self._transform_step(df, result)
            result["steps_completed"].append("transform")
            logger.info(f"Transform complete: {len(df)} rows")

            # Step 5: Detect Anomalies (empty/null field detection)
            df = self._detect_anomalies_step(df, result)
            result["steps_completed"].append("detect_anomalies")
            logger.info(f"Anomaly detection complete: {len(df)} rows")

            # Step 6: Generate Aggregates
            aggregates = self._generate_aggregates_step(df, result)
            result["steps_completed"].append("generate_aggregates")
            result["statistics"]["aggregates_generated"] = len(aggregates)
            logger.info(f"Generated {len(aggregates)} aggregate views")

            # Step 7: Output
            output_path = self._output_step(df, result)
            result["output_file"] = output_path
            result["steps_completed"].append("output")

            # Step 8: Save to Database (if session provided)
            if db_session:
                save_result = self.save_to_database(df, aggregates, file_upload_id, db_session, result)
                result["database_save"] = save_result
                result["steps_completed"].append("database_save")

            result["processed_rows"] = len(df)
            result["filtered_rows"] = result["original_rows"] - result["processed_rows"]
            result["success"] = True

            logger.info(f"✓ Créance Périodique DOT ETL completed successfully")
            logger.info(f"  Original: {result['original_rows']}, Processed: {result['processed_rows']}, Filtered: {result['filtered_rows']}")

        except Exception as e:
            logger.error(f"✗ ETL failed: {str(e)}", exc_info=True)
            result["errors"].append(f"ETL pipeline failed: {str(e)}")
            result["success"] = False

        return result

    def _ingest_step(self, input_paths: List[str], result: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Step 1: Ingest data from CSV files"""
        dfs = []

        for file_path in input_paths:
            try:
                logger.info(f"Reading file: {file_path}")

                # Read CSV with semicolon delimiter (French format)
                df = pd.read_csv(
                    file_path,
                    delimiter=';',
                    encoding='utf-8',
                    na_values=['', 'NA', 'N/A', 'nan', 'NaN'],
                    keep_default_na=True,
                    low_memory=False
                )

                logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {os.path.basename(file_path)}")
                dfs.append(df)

            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                result["errors"].append(f"File read error ({os.path.basename(file_path)}): {str(e)}")

        if not dfs:
            return None

        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined {len(dfs)} files into {len(combined_df)} total rows")

        return combined_df

    def _clean_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> pd.DataFrame:
        """
        Step 2: Clean data

        Applies business rules:
        - Rule 1: DOT: Replace _ with space
        - Rule 2: CUST_LEV1: Remove Residential, Startup PME TPE, VIP-AT
        - Rule 3: CUST_LEV2: Remove Scolaires, Convention, KMS, PME
        - Rule 4: CUST_LEV2: Replace Ã© with é
        - Rule 5: CUST_LEV3: Remove "Ligne d'exploitation AT"
        - Rule 6: CUST_LEV3: Replace Ã© with é
        - Rule 7: PRODUIT: Remove ADSL, FTTX, PSTN, VOIP, X25, XDSL
        - Rule 8: PRODUIT: Replace LS with "Specialized Line"
        """
        original_count = len(df)
        cleaned_df = df.copy()

        # Rule 1: DOT - Replace _ with space
        if 'DOT' in cleaned_df.columns:
            cleaned_df['DOT'] = cleaned_df['DOT'].astype(str).str.replace('_', ' ')
            logger.info("Applied Rule 1: DOT _ replaced with space")

        # Rule 2: CUST_LEV1 - Filter out specific values
        if 'CUST_LEV1' in cleaned_df.columns:
            before = len(cleaned_df)
            filter_values = ['Residential', 'Startup PME TPE', 'VIP-AT']
            mask = cleaned_df['CUST_LEV1'].astype(str).str.contains(
                '|'.join(filter_values), case=False, na=False
            )
            cleaned_df = cleaned_df[~mask]
            filtered = before - len(cleaned_df)
            if filtered > 0:
                logger.info(f"Applied Rule 2: Filtered {filtered} rows from CUST_LEV1")
                result["warnings"].append(f"Filtered {filtered} rows: CUST_LEV1 contains Residential/Startup PME TPE/VIP-AT")

        # Rule 3 & 4: CUST_LEV2 - Filter and clean
        if 'CUST_LEV2' in cleaned_df.columns:
            # Rule 3: Filter
            before = len(cleaned_df)
            filter_values = ['Scolaires', 'Convention', 'KMS', 'PME']
            mask = cleaned_df['CUST_LEV2'].astype(str).str.contains(
                '|'.join(filter_values), case=False, na=False
            )
            cleaned_df = cleaned_df[~mask]
            filtered = before - len(cleaned_df)
            if filtered > 0:
                logger.info(f"Applied Rule 3: Filtered {filtered} rows from CUST_LEV2")
                result["warnings"].append(f"Filtered {filtered} rows: CUST_LEV2 contains Scolaires/Convention/KMS/PME")

            # Rule 4: Replace Ã© with é
            cleaned_df['CUST_LEV2'] = cleaned_df['CUST_LEV2'].astype(str).str.replace('Ã©', 'é')
            logger.info("Applied Rule 4: CUST_LEV2 Ã© replaced with é")

        # Rule 5 & 6: CUST_LEV3 - Filter and clean
        if 'CUST_LEV3' in cleaned_df.columns:
            # Rule 5: Filter
            before = len(cleaned_df)
            mask = cleaned_df['CUST_LEV3'].astype(str).str.contains(
                "Ligne d'exploitation AT", case=False, na=False
            )
            cleaned_df = cleaned_df[~mask]
            filtered = before - len(cleaned_df)
            if filtered > 0:
                logger.info(f"Applied Rule 5: Filtered {filtered} rows from CUST_LEV3")
                result["warnings"].append(f"Filtered {filtered} rows: CUST_LEV3 contains Ligne d'exploitation AT")

            # Rule 6: Replace Ã© with é
            cleaned_df['CUST_LEV3'] = cleaned_df['CUST_LEV3'].astype(str).str.replace('Ã©', 'é')
            logger.info("Applied Rule 6: CUST_LEV3 Ã© replaced with é")

        # Rule 7 & 8: PRODUIT - Filter and clean
        if 'PRODUIT' in cleaned_df.columns:
            # Rule 7: Filter
            before = len(cleaned_df)
            filter_values = ['ADSL', 'FTTX', 'PSTN', 'VOIP', 'X25', 'XDSL']
            mask = cleaned_df['PRODUIT'].astype(str).str.contains(
                '|'.join(filter_values), case=False, na=False
            )
            cleaned_df = cleaned_df[~mask]
            filtered = before - len(cleaned_df)
            if filtered > 0:
                logger.info(f"Applied Rule 7: Filtered {filtered} rows from PRODUIT")
                result["warnings"].append(f"Filtered {filtered} rows: PRODUIT contains ADSL/FTTX/PSTN/VOIP/X25/XDSL")

            # Rule 8: Replace LS with Specialized Line
            cleaned_df['PRODUIT'] = cleaned_df['PRODUIT'].astype(str).str.replace('LS', 'Specialized Line', case=False)
            logger.info("Applied Rule 8: PRODUIT LS replaced with Specialized Line")

        total_filtered = original_count - len(cleaned_df)
        logger.info(f"Cleaning complete: {total_filtered} rows filtered out, {len(cleaned_df)} remaining")

        return cleaned_df

    def _validate_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> pd.DataFrame:
        """Step 3: Validate data quality"""
        validated_df = df.copy()

        # Check for required columns
        missing_cols = [col for col in self.required_columns if col not in validated_df.columns]
        if missing_cols:
            result["warnings"].append(f"Missing columns: {missing_cols}")

        # Validate and clean MOIS (month) - should be 01-12
        if 'MOIS' in validated_df.columns:
            # Convert to string, remove spaces, and validate
            validated_df['MOIS'] = (
                validated_df['MOIS']
                .astype(str)
                .str.strip()
                .str.replace(' ', '')
            )
            # Try to extract valid month (1-12) from the value
            def extract_month(val):
                if pd.isna(val) or val == '' or val == 'nan':
                    return None
                val_str = str(val).strip()
                # Remove spaces and split by common separators to get first value
                val_str = val_str.replace(' ', '').split(';')[0].split(',')[0]
                
                # If it's a number, check if it's in valid range
                try:
                    month_int = int(float(val_str))
                    if 1 <= month_int <= 12:
                        return str(month_int).zfill(2)
                    # If it's a large number, try to extract last 2 digits
                    if month_int > 12:
                        month_str = str(month_int)
                        # Try last 2 digits
                        if len(month_str) >= 2:
                            last_two = month_str[-2:]
                            month_int = int(last_two)
                            if 1 <= month_int <= 12:
                                return str(month_int).zfill(2)
                        # Try first 2 digits if it's very long (e.g., "28693" -> "28" invalid, try "86" or "93")
                        # Actually, for months, we want last 2 digits
                except (ValueError, OverflowError):
                    pass
                return None
            
            validated_df['MOIS'] = validated_df['MOIS'].apply(extract_month)
            # Filter out rows with invalid months
            before = len(validated_df)
            validated_df = validated_df[validated_df['MOIS'].notna()]
            filtered = before - len(validated_df)
            if filtered > 0:
                logger.warning(f"Filtered {filtered} rows with invalid MOIS values")
                result["warnings"].append(f"Filtered {filtered} rows: Invalid MOIS values")

        # Validate and clean ANNEE (year) - should be reasonable year (2000-2100)
        if 'ANNEE' in validated_df.columns:
            # Convert to string and validate
            validated_df['ANNEE'] = (
                validated_df['ANNEE']
                .astype(str)
                .str.strip()
                .str.replace(' ', '')
            )
            # Try to extract valid year (2000-2100) from the value
            def extract_year(val):
                if pd.isna(val) or val == '' or val == 'nan':
                    return None
                val_str = str(val).strip()
                # Remove spaces and split by common separators to get first value
                val_str = val_str.replace(' ', '').split(';')[0].split(',')[0]
                
                try:
                    year_int = int(float(val_str))
                    # If it's in valid range, return as is
                    if 2000 <= year_int <= 2100:
                        return str(year_int)
                    # If it's a very large number, try to extract last 4 digits
                    if year_int > 2100:
                        year_str = str(year_int)
                        # Try last 4 digits (most common case: "21684" -> "1684" invalid, but "179229" -> "9229" invalid)
                        # Actually, we should try different positions
                        if len(year_str) >= 4:
                            # Try last 4 digits first
                            last_four = year_str[-4:]
                            year_int_test = int(last_four)
                            if 2000 <= year_int_test <= 2100:
                                return str(year_int_test)
                            # If that doesn't work, try first 4 digits (e.g., "2168" from "21684")
                            if len(year_str) > 4:
                                first_four = year_str[:4]
                                year_int_test = int(first_four)
                                if 2000 <= year_int_test <= 2100:
                                    return str(year_int_test)
                except (ValueError, OverflowError):
                    pass
                return None
            
            validated_df['ANNEE'] = validated_df['ANNEE'].apply(extract_year)
            # Filter out rows with invalid years
            before = len(validated_df)
            validated_df = validated_df[validated_df['ANNEE'].notna()]
            filtered = before - len(validated_df)
            if filtered > 0:
                logger.warning(f"Filtered {filtered} rows with invalid ANNEE values")
                result["warnings"].append(f"Filtered {filtered} rows: Invalid ANNEE values")

        # Convert amount columns to numeric (handle French format with spaces)
        amount_columns = [
            'INVOICE_AMT', 'OPEN_AMT', 'TAX_AMT', 'INVOICE_AMT_HT',
            'DISPUTE_AMT', 'DISPUTE_TAX_AMT', 'DISPUTE_NET_AMT',
            'CREANCE_BRUT', 'CREANCE_NET', 'CREANCE_HT'
        ]

        for col in amount_columns:
            if col in validated_df.columns:
                # Remove spaces (thousand separators), replace comma with dot, and convert to numeric
                validated_df[col] = (
                    validated_df[col]
                    .astype(str)
                    .str.replace(' ', '')  # Remove all spaces (French thousand separator)
                    .str.replace(',', '.')  # Replace comma with dot for decimal
                    .str.replace(';', '')   # Remove semicolons that might be present
                )
                # Handle cases where multiple values might be concatenated (e.g., "286 93" -> "28693" or "286.93")
                # Try to parse as float, if it fails, try to extract first valid number
                def parse_amount(val):
                    if pd.isna(val) or val == '' or val == 'nan' or val == 'None':
                        return None
                    val_str = str(val).strip()
                    # Extract first number (with decimal point)
                    match = re.search(r'-?\d+\.?\d*', val_str)
                    if match:
                        try:
                            return float(match.group())
                        except (ValueError, TypeError):
                            pass
                    return None
                
                validated_df[col] = validated_df[col].apply(parse_amount)
                # Fill NaN with 0 for amount columns (assuming 0 if empty)
                validated_df[col] = validated_df[col].fillna(0)

        logger.info("Validation complete: MOIS/ANNEE validated, Amount columns converted to numeric")

        return validated_df

    def _transform_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> pd.DataFrame:
        """
        Step 4: Transform data

        Applies:
        - Rule 10: Create period_key (YYYY-MM)
        - Column name standardization
        - Data type conversions
        """
        transformed_df = df.copy()

        # Rule 10: Create period_key from ANNEE and MOIS
        if 'ANNEE' in transformed_df.columns and 'MOIS' in transformed_df.columns:
            transformed_df['PERIOD_KEY'] = (
                transformed_df['ANNEE'].astype(str) + '-' +
                transformed_df['MOIS'].astype(str).str.zfill(2)
            )
            logger.info("Applied Rule 10: Created PERIOD_KEY (YYYY-MM)")

        # Ensure string columns remain as strings (convert from numeric if needed)
        # This ensures that columns like SUBS_STATUS (which might be parsed as numeric) are converted to strings
        string_columns = ['DOT', 'ACTEL', 'MOIS', 'ANNEE', 'PERIOD_KEY', 'SUBS_STATUS', 
                         'PRODUIT', 'CUST_LEV1', 'CUST_LEV2', 'CUST_LEV3']
        for col in string_columns:
            if col in transformed_df.columns:
                # Convert to object type first to preserve None values
                transformed_df[col] = transformed_df[col].astype('object')
                # Convert all values to strings, but keep None/NaN as None
                def convert_to_string_safe(val):
                    if val is None:
                        return None
                    if pd.isna(val):
                        return None
                    try:
                        str_val = str(val).strip()
                        # If it's a string representation of NaN, return None
                        if str_val.lower() in ('nan', 'none', 'null', ''):
                            return None
                        return str_val
                    except Exception:
                        return None
                
                transformed_df[col] = transformed_df[col].apply(convert_to_string_safe)
        
        logger.info("Converted string columns to object type (preserving None values)")

        # Standardize column names (lowercase with underscores)
        column_mapping = {
            'DOT': 'dot',
            'ACTEL': 'actel',
            'MOIS': 'mois',
            'ANNEE': 'annee',
            'PERIOD_KEY': 'period_key',
            'SUBS_STATUS': 'subs_status',
            'PRODUIT': 'produit',
            'CUST_LEV1': 'cust_lev1',
            'CUST_LEV2': 'cust_lev2',
            'CUST_LEV3': 'cust_lev3',
            'INVOICE_AMT': 'invoice_amt',
            'OPEN_AMT': 'open_amt',
            'TAX_AMT': 'tax_amt',
            'INVOICE_AMT_HT': 'invoice_amt_ht',
            'DISPUTE_AMT': 'dispute_amt',
            'DISPUTE_TAX_AMT': 'dispute_tax_amt',
            'DISPUTE_NET_AMT': 'dispute_net_amt',
            'CREANCE_BRUT': 'creance_brut',
            'CREANCE_NET': 'creance_net',
            'CREANCE_HT': 'creance_ht',
        }

        transformed_df.rename(columns=column_mapping, inplace=True)
        logger.info("Transform complete: Column names standardized")

        return transformed_df

    def _detect_anomalies_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> pd.DataFrame:
        """
        Step 5: Detect empty/null field anomalies in Créance data

        Identifies records with missing critical fields and marks them for review.
        Critical fields: DOT, CREANCE_NET, INVOICE_AMT, CUST_LEV1, PRODUIT
        """
        logger.info("🔍 Starting anomaly detection for empty/null fields")

        anomaly_df = df.copy()
        anomalies_count = 0

        # Define critical fields that should not be empty
        critical_fields = ['dot', 'creance_net', 'invoice_amt', 'cust_lev1', 'produit']

        # Convert column names to lowercase for consistency
        anomaly_df.columns = [col.lower() for col in anomaly_df.columns]

        # Initialize anomaly flag column
        anomaly_df['is_anomaly'] = False
        anomaly_df['anomaly_reason'] = ''

        # Check for missing critical fields
        for critical_field in critical_fields:
            if critical_field in anomaly_df.columns:
                # Identify rows with null/empty values in this critical field
                missing_mask = anomaly_df[critical_field].isna() | (anomaly_df[critical_field].astype(str).str.strip() == '')

                # Update anomaly flag and reason
                anomaly_df.loc[missing_mask, 'is_anomaly'] = True
                anomaly_df.loc[missing_mask, 'anomaly_reason'] = anomaly_df.loc[missing_mask, 'anomaly_reason'].apply(
                    lambda x: f"{x}; Missing {critical_field}" if x else f"Missing {critical_field}"
                )

                anomalies_count += missing_mask.sum()

                if missing_mask.sum() > 0:
                    logger.warning(f"⚠️ Found {missing_mask.sum()} records with missing '{critical_field}'")

        # Additional anomaly checks
        # Check for negative amounts
        amount_fields = ['creance_net', 'creance_brut', 'invoice_amt', 'open_amt']
        for amount_field in amount_fields:
            if amount_field in anomaly_df.columns:
                negative_mask = (anomaly_df[amount_field].astype(float, errors='ignore') < 0)

                if isinstance(negative_mask, pd.Series):
                    anomaly_df.loc[negative_mask, 'is_anomaly'] = True
                    anomaly_df.loc[negative_mask, 'anomaly_reason'] = anomaly_df.loc[negative_mask, 'anomaly_reason'].apply(
                        lambda x: f"{x}; Negative {amount_field}" if x else f"Negative {amount_field}"
                    )

                    if negative_mask.sum() > 0:
                        logger.warning(f"⚠️ Found {negative_mask.sum()} records with negative '{amount_field}'")

        # Log summary
        total_anomalies = anomaly_df['is_anomaly'].sum()
        result['statistics']['anomalies_detected'] = int(total_anomalies)

        logger.info(f"✓ Anomaly detection complete:")
        logger.info(f"  Total anomalies found: {total_anomalies}")
        logger.info(f"  Anomaly rate: {(total_anomalies / len(anomaly_df) * 100):.2f}%")

        if total_anomalies > 0:
            result['warnings'].append(f"Found {total_anomalies} anomalous records during processing")

        return anomaly_df

    def _generate_aggregates_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Step 6: Generate aggregate views for dashboard

        Creates 5 aggregate types:
        1. overview - Global KPIs
        2. by_dot - Aggregated by DOT
        3. by_annee - Aggregated by year
        4. by_produit - Aggregated by product
        5. by_cust_lev2 - Aggregated by customer level 2
        """
        aggregates = []

        # 1. Overview aggregate
        overview = {
            'view_type': 'overview',
            'total_invoice_amt': float(df['invoice_amt'].sum() if 'invoice_amt' in df.columns else 0),
            'total_open_amt': float(df['open_amt'].sum() if 'open_amt' in df.columns else 0),
            'total_tax_amt': float(df['tax_amt'].sum() if 'tax_amt' in df.columns else 0),
            'total_invoice_amt_ht': float(df['invoice_amt_ht'].sum() if 'invoice_amt_ht' in df.columns else 0),
            'total_creance_brut': float(df['creance_brut'].sum() if 'creance_brut' in df.columns else 0),
            'total_creance_net': float(df['creance_net'].sum() if 'creance_net' in df.columns else 0),
            'total_creance_ht': float(df['creance_ht'].sum() if 'creance_ht' in df.columns else 0),
            'nombre_lignes': len(df)
        }
        aggregates.append(overview)

        # 2. By DOT
        if 'dot' in df.columns and 'creance_net' in df.columns:
            by_dot = df.groupby('dot').agg({
                'invoice_amt': 'sum',
                'open_amt': 'sum',
                'creance_brut': 'sum',
                'creance_net': 'sum',
                'creance_ht': 'sum'
            }).reset_index(drop=False)
            by_dot['nombre_lignes'] = df.groupby('dot').size().values
            by_dot['view_type'] = 'by_dot'
            aggregates.extend(by_dot.to_dict('records'))

        # 3. By ANNEE
        if 'annee' in df.columns and 'creance_net' in df.columns:
            by_annee = df.groupby('annee').agg({
                'invoice_amt': 'sum',
                'creance_brut': 'sum',
                'creance_net': 'sum'
            }).reset_index(drop=False)
            by_annee['nombre_lignes'] = df.groupby('annee').size().values
            by_annee['view_type'] = 'by_annee'
            aggregates.extend(by_annee.to_dict('records'))

        # 4. By PRODUIT
        if 'produit' in df.columns and 'creance_net' in df.columns:
            by_produit = df.groupby('produit').agg({
                'invoice_amt': 'sum',
                'creance_brut': 'sum',
                'creance_net': 'sum'
            }).reset_index(drop=False)
            by_produit['nombre_lignes'] = df.groupby('produit').size().values
            by_produit['view_type'] = 'by_produit'
            aggregates.extend(by_produit.to_dict('records'))

        # 5. By CUST_LEV2
        if 'cust_lev2' in df.columns and 'creance_net' in df.columns:
            by_cust = df.groupby('cust_lev2').agg({
                'invoice_amt': 'sum',
                'creance_brut': 'sum',
                'creance_net': 'sum'
            }).reset_index(drop=False)
            by_cust['nombre_lignes'] = df.groupby('cust_lev2').size().values
            by_cust['view_type'] = 'by_cust_lev2'
            aggregates.extend(by_cust.to_dict('records'))

        logger.info(f"Generated {len(aggregates)} aggregate views")
        return aggregates

    def _output_step(self, df: pd.DataFrame, result: Dict[str, Any]) -> str:
        """Step 6: Output processed data to CSV"""
        try:
            output_dir = "output/creance_periodique_dot"
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"creance_periodique_dot_processed_{timestamp}.csv")

            df.to_csv(output_file, index=False, encoding='utf-8')
            logger.info(f"Output saved to: {output_file}")

            return output_file

        except Exception as e:
            logger.error(f"Output step failed: {e}")
            result["warnings"].append(f"Could not save output file: {str(e)}")
            return None

    def save_to_database(
        self,
        clean_df: pd.DataFrame,
        aggregates: List[Dict[str, Any]],
        file_upload_id: Optional[int],
        db_session: Session,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 7: Save processed data to database with DOT matching for RBAC

        Args:
            clean_df: Cleaned DataFrame
            aggregates: List of aggregate view dictionaries
            file_upload_id: File upload ID for tracking
            db_session: Database session
            result: ETL result dictionary

        Returns:
            Dictionary with save statistics
        """
        save_result = {
            "success": False,
            "main_records_saved": 0,
            "aggregates_saved": 0,
            "errors": []
        }

        try:
            # Get DOT mapping for RBAC
            dot_mapping = {}
            dots = db_session.query(DOT).all()
            for dot in dots:
                dot_mapping[dot.name.upper()] = dot.id

            logger.info(f"Loaded {len(dot_mapping)} DOTs for matching")

            # Save main records
            for idx, row in clean_df.iterrows():
                try:
                    # Match DOT name to dot_id
                    dot_name = str(row.get('dot', '')).upper().strip()
                    matched_dot_id = None

                    for stored_dot_name, dot_id in dot_mapping.items():
                        if stored_dot_name in dot_name or dot_name in stored_dot_name:
                            matched_dot_id = dot_id
                            break

                    # Helper function to safely convert to string, handling NaN
                    def safe_str(val, max_len=None):
                        if pd.isna(val) or val is None:
                            return None
                        try:
                            str_val = str(val).strip()
                            if str_val == '' or str_val.lower() in ('nan', 'none', 'null'):
                                return None
                            if max_len:
                                return str_val[:max_len]
                            return str_val
                        except Exception:
                            return None
                    
                    # Create record
                    record = CreancePeriodiqueDot(
                        file_upload_id=file_upload_id,
                        dot_id=matched_dot_id,
                        dot=safe_str(row.get('dot'), 200),
                        actel=safe_str(row.get('actel'), 255),
                        mois=safe_str(row.get('mois'), 2),
                        annee=safe_str(row.get('annee'), 4),
                        period_key=safe_str(row.get('period_key'), 7),
                        subs_status=safe_str(row.get('subs_status'), 50),
                        produit=safe_str(row.get('produit'), 100),
                        cust_lev1=safe_str(row.get('cust_lev1'), 200),
                        cust_lev2=safe_str(row.get('cust_lev2'), 200),
                        cust_lev3=safe_str(row.get('cust_lev3'), 200),
                        invoice_amt=float(row.get('invoice_amt', 0)) if pd.notna(row.get('invoice_amt')) else None,
                        open_amt=float(row.get('open_amt', 0)) if pd.notna(row.get('open_amt')) else None,
                        tax_amt=float(row.get('tax_amt', 0)) if pd.notna(row.get('tax_amt')) else None,
                        invoice_amt_ht=float(row.get('invoice_amt_ht', 0)) if pd.notna(row.get('invoice_amt_ht')) else None,
                        dispute_amt=float(row.get('dispute_amt', 0)) if pd.notna(row.get('dispute_amt')) else None,
                        dispute_tax_amt=float(row.get('dispute_tax_amt', 0)) if pd.notna(row.get('dispute_tax_amt')) else None,
                        dispute_net_amt=float(row.get('dispute_net_amt', 0)) if pd.notna(row.get('dispute_net_amt')) else None,
                        creance_brut=float(row.get('creance_brut', 0)) if pd.notna(row.get('creance_brut')) else None,
                        creance_net=float(row.get('creance_net', 0)) if pd.notna(row.get('creance_net')) else None,
                        creance_ht=float(row.get('creance_ht', 0)) if pd.notna(row.get('creance_ht')) else None,
                    )

                    db_session.add(record)
                    save_result["main_records_saved"] += 1

                except Exception as e:
                    save_result["errors"].append(f"Row {idx}: {str(e)}")

            # Save aggregate views
            for agg in aggregates:
                try:
                    # Match DOT for aggregates that have a dot_name field
                    dot_name = agg.get('dot', '')
                    matched_dot_id = None

                    if dot_name:
                        dot_name_upper = str(dot_name).upper().strip()
                        for stored_dot_name, dot_id in dot_mapping.items():
                            if stored_dot_name in dot_name_upper or dot_name_upper in stored_dot_name:
                                matched_dot_id = dot_id
                                break

                    aggregate_record = CreanceAggregateView(
                        file_upload_id=file_upload_id,
                        dot_id=matched_dot_id,
                        view_type=agg.get('view_type'),
                        dot_name=agg.get('dot'),
                        annee=agg.get('annee'),
                        produit=agg.get('produit'),
                        cust_lev2=agg.get('cust_lev2'),
                        total_invoice_amt=float(agg.get('invoice_amt', 0)) if pd.notna(agg.get('invoice_amt')) else None,
                        total_open_amt=float(agg.get('open_amt', 0)) if pd.notna(agg.get('open_amt')) else None,
                        total_tax_amt=float(agg.get('tax_amt', 0)) if pd.notna(agg.get('tax_amt')) else None,
                        total_invoice_amt_ht=float(agg.get('invoice_amt_ht', 0)) if pd.notna(agg.get('invoice_amt_ht')) else None,
                        total_creance_brut=float(agg.get('creance_brut', 0)) if pd.notna(agg.get('creance_brut')) else None,
                        total_creance_net=float(agg.get('creance_net', 0)) if pd.notna(agg.get('creance_net')) else None,
                        total_creance_ht=float(agg.get('creance_ht', 0)) if pd.notna(agg.get('creance_ht')) else None,
                        nombre_lignes=int(agg.get('nombre_lignes', 0)) if pd.notna(agg.get('nombre_lignes')) else None,
                    )

                    db_session.add(aggregate_record)
                    save_result["aggregates_saved"] += 1

                except Exception as e:
                    save_result["errors"].append(f"Aggregate {agg.get('view_type')}: {str(e)}")

            # Commit all changes
            db_session.commit()
            save_result["success"] = True

            logger.info(f"✓ Database save complete:")
            logger.info(f"  Main records: {save_result['main_records_saved']}")
            logger.info(f"  Aggregates: {save_result['aggregates_saved']}")

        except Exception as e:
            db_session.rollback()
            logger.error(f"Database save failed: {e}", exc_info=True)
            save_result["success"] = False
            save_result["errors"].append(f"Database transaction failed: {str(e)}")

        return save_result
