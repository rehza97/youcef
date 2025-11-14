"""
Encaissement AR DOT ETL Module
Processes Encaissement AR (Accounts Receivable) data with specific business rules
Handles multi-year data processing with automatic duplicate detection, KPI calculations, and database persistence

Business Rules:
1. Remove all AT_SIEGE entries
2. Clean organization names (DOT_ removal, separator normalization)
3. Convert N_FACT to numeric format
4. Sort by Org Name, Typ Fact, N Fact
5. Detect duplicates using composite key (Organisation & N Fact & Typ Fact)
6. Set amounts to 0.00 for duplicate entries
7. Calculate Taux d'encaissement = (Encaissement / Montant TTC) * 100
8. Format numeric columns with thousand separators
9. Save to database with DOT relationships for RBAC

KPIs Calculated:
- Taux d'encaissement par DOT
- Taux d'encaissement par Mois
- Montant TTC total
- Encaissement total
- Montant restant à encaisser
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import re
import json

from .base import ETLResult, ETLStep, ETLStepType, BaseETLProcessor
from .utils import ETLUtils

logger = logging.getLogger(__name__)


class EncaissementARDotETL(BaseETLProcessor):
    """ETL processor for Encaissement AR DOT data"""

    def __init__(self):
        super().__init__()
        self.kpi_name = "encaissement_ar_dot"
        self.required_columns = [
            "organisation",
            "n_fact",
            "typ_fact",
            "date_fact",
            "montant_ht",
            "montant_taxe",
            "montant_ttc",
            "chiffre_aff_exe",
            "encaissement"
        ]

    def run_etl(self, input_paths: List[Path], file_upload_id: Optional[int] = None,
                db_session=None) -> ETLResult:
        """
        Main ETL entry point for Encaissement AR DOT data processing

        Args:
            input_paths: List of input file paths to process (can be multiple years)
            file_upload_id: Optional file upload ID for database tracking
            db_session: Optional SQLAlchemy session for database operations

        Returns:
            ETLResult with processing details and output paths
        """
        result = ETLResult(
            kpi_name=self.kpi_name,
            success=False,
            start_time=datetime.utcnow(),
            input_files=input_paths
        )

        try:
            logger.info(f"🚀 Starting Encaissement AR DOT ETL processing for {len(input_paths)} file(s)")

            # Step 1: Ingest data from all files
            combined_df = self._ingest_step(input_paths, result)
            if combined_df.empty:
                raise ValueError("No Encaissement AR DOT data found in input files")

            result.input_records_count = len(combined_df)
            logger.info(f"📊 Total records ingested: {result.input_records_count}")

            # Step 2: Clean data (remove AT_SIEGE, clean org names)
            cleaned_df = self._clean_step(combined_df, result)

            # Step 3: Validate data
            validated_df = self._validate_step(cleaned_df, result)

            # Step 4: Transform data (sort, detect duplicates, calculate KPIs)
            transformed_df = self._transform_step(validated_df, result)

            # Step 5: Detect anomalies
            final_df, anomalies_df = self._detect_anomalies_step(transformed_df, result)

            # Step 6: Generate aggregated views for visualization
            self._generate_views_step(final_df, result)

            # Step 7: Output results
            self._output_step(final_df, anomalies_df, result)

            # Step 8: Save to database (if session provided)
            if db_session and file_upload_id:
                saved_counts = self.save_to_database(final_df, anomalies_df, file_upload_id, db_session, result)
                result.metadata["database_saved"] = saved_counts

            result.output_records_count = len(final_df)
            result.anomaly_records_count = len(anomalies_df)

            logger.info(f"✅ Encaissement AR DOT ETL completed successfully")
            logger.info(f"   Output records: {result.output_records_count}")
            logger.info(f"   Anomaly records: {result.anomaly_records_count}")

        except Exception as e:
            error_msg = f"Encaissement AR DOT ETL process failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        finally:
            result.complete()

        return result

    def _ingest_step(self, input_paths: List[Path], result: ETLResult) -> pd.DataFrame:
        """Step 1: Ingest and combine Encaissement AR DOT files"""
        step = ETLStep(
            step_type=ETLStepType.INGEST,
            name="ingest_encaissement_files",
            description="Read and combine Encaissement AR files from multiple years"
        )
        step.start()
        result.add_step(step)

        combined_data = []

        try:
            for file_path in input_paths:
                try:
                    logger.info(f"📂 Reading file: {file_path.name}")

                    # Read file with HTML parsing support (some .xls are HTML format)
                    file_ext = file_path.suffix.lower()
                    if file_ext == '.xls':
                        # Try HTML parsing first for .xls files
                        try:
                            # Read HTML tables without header first to find the right table
                            html_tables_raw = pd.read_html(str(file_path), header=None)
                            if html_tables_raw:
                                # Find the table with most columns (likely the data table)
                                best_table = None
                                max_columns = 0
                                best_table_idx = -1
                                for idx, table in enumerate(html_tables_raw):
                                    if len(table.columns) > max_columns:
                                        max_columns = len(table.columns)
                                        best_table = table
                                        best_table_idx = idx
                                
                                if best_table is not None and max_columns >= 15:  # Encaissement files have 20 columns
                                    logger.info(f"✅ Found HTML table {best_table_idx} with {max_columns} columns and {len(best_table)} rows")
                                    
                                    # Find header row (should contain "Organisation")
                                    header_row = None
                                    for idx in range(min(5, len(best_table))):
                                        row_values = [str(val).lower() for val in best_table.iloc[idx].values if pd.notna(val)]
                                        if any('organisation' in val or ('org' in val and 'name' not in val) for val in row_values):
                                            header_row = idx
                                            logger.info(f"✅ Found header row at index {idx}")
                                            break
                                    
                                    if header_row is not None:
                                        df = best_table.iloc[header_row + 1:].copy()
                                        df.columns = best_table.iloc[header_row].astype(str).tolist()
                                        df.reset_index(drop=True, inplace=True)
                                        logger.info(f"✅ Parsed HTML table: {len(df)} data rows with {len(df.columns)} columns")
                                    else:
                                        # Use first row as header
                                        logger.warning("⚠️ No clear header row found, using row 0 as header")
                                        df = best_table.iloc[1:].copy()
                                        df.columns = best_table.iloc[0].astype(str).tolist()
                                        df.reset_index(drop=True, inplace=True)
                                        logger.info(f"✅ Parsed HTML table: {len(df)} data rows")
                                else:
                                    raise ValueError(f"No suitable HTML table found (max columns: {max_columns})")
                            else:
                                raise ValueError("No HTML tables found")
                        except Exception as html_error:
                            logger.warning(f"⚠️ HTML parsing failed: {html_error}, trying Excel...")
                            # Fall back to regular Excel reading
                            try:
                                df = pd.read_excel(file_path, engine='xlrd')
                            except Exception as excel_error:
                                raise ValueError(f"Failed to read as HTML or Excel: HTML error: {html_error}, Excel error: {excel_error}")
                    else:
                        df = ETLUtils.ingest_file(file_path)
                    
                    # Normalize column names to snake_case
                    df = ETLUtils.normalize_headers_to_snake_case(df)
                    
                    # Log normalized columns for debugging
                    logger.info(f"📋 Normalized columns: {list(df.columns)}")

                    # Remove empty rows
                    df = df.dropna(how='all')

                    combined_data.append(df)
                    step.records_processed += len(df)
                    logger.info(f"✅ Ingested {file_path.name}: {len(df)} records")

                except Exception as e:
                    error_msg = f"Error ingesting {file_path.name}: {str(e)}"
                    logger.error(error_msg)
                    step.add_warning(error_msg)

            if not combined_data:
                raise ValueError("No valid Encaissement AR DOT files found")

            # Combine all DataFrames
            combined_df = pd.concat(combined_data, ignore_index=True)

            step.metadata["files_processed"] = len(combined_data)
            step.metadata["files_failed"] = len(input_paths) - len(combined_data)
            step.metadata["total_records"] = len(combined_df)

            step.complete(len(combined_df))
            return combined_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 2: Clean and standardize Encaissement AR data"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="clean_encaissement_data",
            description="Apply Encaissement AR DOT specific cleaning rules"
        )
        step.start()
        result.add_step(step)

        try:
            cleaned_df = df.copy()
            step.records_processed = len(cleaned_df)
            original_count = len(cleaned_df)

            # Columns are already normalized to snake_case in _ingest_step
            # But we may need to map some variations to ensure exact match
            # Check if we have the required columns, if not try mapping
            column_mapping = {}
            required_cols_lower = [col.lower() for col in self.required_columns]
            existing_cols_lower = [col.lower() for col in cleaned_df.columns]
            
            # Only map if we're missing required columns
            missing_cols = [col for col in self.required_columns if col.lower() not in existing_cols_lower]
            if missing_cols:
                logger.warning(f"⚠️ Some required columns missing after normalization: {missing_cols}")
                logger.info(f"   Existing columns: {list(cleaned_df.columns)}")
                # Try to map variations
                column_mapping = self._map_column_names(cleaned_df.columns)
                if column_mapping:
                    cleaned_df = cleaned_df.rename(columns=column_mapping)
                    logger.info(f"📋 Applied column mapping: {column_mapping}")
            else:
                logger.info(f"✅ All required columns present after normalization")

            # RULE 1: Remove AT_SIEGE entries
            if 'organisation' in cleaned_df.columns:
                at_siege_mask = cleaned_df['organisation'].str.contains('AT_SIEGE', case=False, na=False)
                at_siege_count = at_siege_mask.sum()

                cleaned_df = cleaned_df[~at_siege_mask].reset_index(drop=True)

                if at_siege_count > 0:
                    logger.info(f"🗑️ Removed {at_siege_count} AT_SIEGE entries")
                    step.add_warning(f"Removed {at_siege_count} AT_SIEGE entries as per business rules")

            # RULE 2: Clean organization names
            if 'organisation' in cleaned_df.columns:
                cleaned_df['organisation'] = cleaned_df['organisation'].apply(self._clean_organisation_name)
                logger.info("✅ Cleaned organisation names (DOT_ removal, separator normalization)")

            # RULE 3: Convert N_FACT to numeric format (without decimals)
            if 'n_fact' in cleaned_df.columns:
                cleaned_df['n_fact'] = pd.to_numeric(
                    cleaned_df['n_fact'].astype(str).str.replace(r'[^\d]', '', regex=True),
                    errors='coerce'
                ).fillna(0).astype(int)
                logger.info("✅ Converted N_FACT to numeric format")

            # Clean numeric columns
            numeric_columns = ['montant_ht', 'montant_taxe', 'montant_ttc', 'chiffre_aff_exe', 'encaissement']
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0)

            # Parse date_fact column with dayfirst=True for French date format (dd/mm/yyyy)
            if 'date_fact' in cleaned_df.columns:
                cleaned_df['date_fact'] = pd.to_datetime(cleaned_df['date_fact'], errors='coerce', dayfirst=True)
                # Extract month for aggregation
                cleaned_df['mois'] = cleaned_df['date_fact'].dt.to_period('M').astype(str)
                logger.info("✅ Parsed date_fact and extracted month")

            # Parse date_rglt column - handle French month names (e.g., "12 mars 25", "30 oct. 24")
            if 'date_rglt' in cleaned_df.columns:
                # French month mapping
                french_months = {
                    'janv': '01', 'janvier': '01',
                    'févr': '02', 'février': '02', 'fev': '02', 'fevr': '02',
                    'mars': '03',
                    'avr': '04', 'avril': '04',
                    'mai': '05',
                    'juin': '06',
                    'juil': '07', 'juillet': '07',
                    'août': '08', 'aout': '08',
                    'sept': '09', 'septembre': '09',
                    'oct': '10', 'octobre': '10',
                    'nov': '11', 'novembre': '11',
                    'déc': '12', 'décembre': '12', 'dec': '12'
                }

                def parse_french_date(date_str):
                    """Parse French date strings like '12 mars 25' or '30 oct. 24'"""
                    if pd.isna(date_str):
                        return pd.NaT

                    date_str = str(date_str).strip().lower()

                    # Try standard parsing first
                    try:
                        parsed = pd.to_datetime(date_str, errors='coerce', dayfirst=True)
                        if pd.notna(parsed):
                            return parsed
                    except:
                        pass

                    # Try French month replacement
                    for french, numeric in french_months.items():
                        if french in date_str:
                            # Replace French month with numeric
                            date_str = date_str.replace(french, numeric)
                            # Remove dots and extra spaces
                            date_str = date_str.replace('.', '').replace('  ', ' ')
                            try:
                                # Try parsing as dd mm yy
                                parsed = pd.to_datetime(date_str, errors='coerce', dayfirst=True)
                                if pd.notna(parsed):
                                    return parsed
                            except:
                                pass

                    return pd.NaT

                cleaned_df['date_rglt'] = cleaned_df['date_rglt'].apply(parse_french_date)
                logger.info("✅ Parsed date_rglt with French month name support")

            step.metadata["cleaning_rules_applied"] = [
                "Remove AT_SIEGE entries",
                "Clean organization names (DOT_ removal, separator normalization)",
                "Convert N_FACT to numeric",
                "Parse and normalize numeric columns",
                "Extract month from date_fact",
                "Parse date_rglt"
            ]
            step.metadata["records_removed"] = original_count - len(cleaned_df)

            step.complete(len(cleaned_df))
            return cleaned_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _validate_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 3: Validate data quality and required fields"""
        step = ETLStep(
            step_type=ETLStepType.VALIDATE,
            name="validate_data",
            description="Validate required columns and data quality"
        )
        step.start()
        result.add_step(step)

        try:
            validated_df = df.copy()
            step.records_processed = len(validated_df)

            # Check required columns
            missing_columns = ETLUtils.validate_required_columns(validated_df, self.required_columns)
            if missing_columns:
                error_msg = f"Missing required columns: {missing_columns}"
                logger.error(error_msg)
                step.fail(error_msg)
                return validated_df

            # Remove rows with null critical values
            critical_columns = ['organisation', 'n_fact', 'typ_fact']
            original_count = len(validated_df)

            for col in critical_columns:
                if col in validated_df.columns:
                    validated_df = validated_df.dropna(subset=[col])

            dropped_count = original_count - len(validated_df)
            if dropped_count > 0:
                step.add_warning(f"Dropped {dropped_count} rows with null critical values")

            step.metadata["validation_checks"] = [
                "Required columns present",
                "Critical fields not null"
            ]

            step.complete(len(validated_df))
            return validated_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _transform_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 4: Transform data and calculate KPIs"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="transform_calculate_kpis",
            description="Sort, detect duplicates, and calculate Taux d'encaissement"
        )
        step.start()
        result.add_step(step)

        try:
            transformed_df = df.copy()
            step.records_processed = len(transformed_df)

            # RULE 4: Sort by Organisation, Typ Fact, N Fact
            sort_columns = []
            if 'organisation' in transformed_df.columns:
                sort_columns.append('organisation')
            if 'typ_fact' in transformed_df.columns:
                sort_columns.append('typ_fact')
            if 'n_fact' in transformed_df.columns:
                sort_columns.append('n_fact')

            if sort_columns:
                transformed_df = transformed_df.sort_values(by=sort_columns).reset_index(drop=True)
                logger.info(f"✅ Sorted by: {', '.join(sort_columns)}")

            # RULE 5: Create composite key (Organisation & N Fact & Typ Fact)
            transformed_df['composite_key'] = (
                transformed_df['organisation'].astype(str) + '&' +
                transformed_df['n_fact'].astype(str) + '&' +
                transformed_df['typ_fact'].astype(str)
            )

            # RULE 6: Detect duplicates and set amounts to 0.00
            duplicates_mask = transformed_df.duplicated(subset='composite_key', keep='first')
            duplicate_count = duplicates_mask.sum()

            if duplicate_count > 0:
                # Set amounts to 0.00 for duplicates (including encaissement - critical for collection tracking)
                amount_columns = ['montant_ht', 'montant_taxe', 'montant_ttc', 'chiffre_aff_exe', 'encaissement']
                for col in amount_columns:
                    if col in transformed_df.columns:
                        transformed_df.loc[duplicates_mask, col] = 0.00

                # Mark duplicates for tracking
                transformed_df['is_duplicate'] = duplicates_mask

                logger.info(f"🔍 Found {duplicate_count} duplicate entries (set all amounts to 0.00)")
                logger.info(f"   ✅ Encaissement amounts zeroed out for duplicates to prevent double-counting")
                step.add_warning(f"Found {duplicate_count} duplicate entries based on composite key")
                step.add_warning(f"Encaissement amounts zeroed out for all duplicate entries")

            # RULE 7: Calculate Taux d'encaissement
            if 'montant_ttc' in transformed_df.columns and 'encaissement' in transformed_df.columns:
                transformed_df['taux_encaissement'] = np.where(
                    transformed_df['montant_ttc'] > 0,
                    (transformed_df['encaissement'] / transformed_df['montant_ttc'] * 100).round(2),
                    0.00
                )

                # Handle infinite values
                transformed_df['taux_encaissement'] = transformed_df['taux_encaissement'].replace(
                    [np.inf, -np.inf], 0.00
                )

                logger.info("✅ Calculated Taux d'encaissement")

            # Calculate additional KPIs
            transformed_df['montant_restant'] = (
                transformed_df['montant_ttc'] - transformed_df['encaissement']
            ).round(2)

            # Calculate summary metrics for result
            result.summary_metrics = self._calculate_summary_metrics(transformed_df)

            step.metadata["kpis_calculated"] = [
                "taux_encaissement",
                "montant_restant",
                "composite_key (for duplicate detection)"
            ]
            step.metadata["duplicates_found"] = int(duplicate_count)

            step.complete(len(transformed_df))
            return transformed_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _detect_anomalies_step(self, df: pd.DataFrame, result: ETLResult) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Step 5: Detect anomalies based on business rules"""
        step = ETLStep(
            step_type=ETLStepType.DETECT_ANOMALIES,
            name="detect_anomalies",
            description="Identify anomalous Encaissement records"
        )
        step.start()
        result.add_step(step)

        try:
            step.records_processed = len(df)

            # Define anomaly detection rules
            anomaly_rules = {
                "negative_montant_ttc": {
                    "type": "range_check",
                    "column": "montant_ttc",
                    "min": 0
                },
                "negative_encaissement": {
                    "type": "range_check",
                    "column": "encaissement",
                    "min": 0
                },
                "excessive_taux_encaissement": {
                    "type": "range_check",
                    "column": "taux_encaissement",
                    "min": 0,
                    "max": 150  # Allow some margin for over-collection
                },
                "zero_n_fact": {
                    "type": "range_check",
                    "column": "n_fact",
                    "min": 1
                }
            }

            clean_data, anomalies = ETLUtils.detect_anomalies(df, anomaly_rules)

            step.metadata["anomaly_rules"] = list(anomaly_rules.keys())
            step.metadata["anomalies_found"] = len(anomalies)

            step.complete(len(clean_data))
            return clean_data, anomalies

        except Exception as e:
            step.fail(str(e))
            raise

    def _generate_views_step(self, df: pd.DataFrame, result: ETLResult) -> None:
        """Step 6: Generate aggregated views for visualizations"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="generate_visualization_views",
            description="Generate aggregated views for dashboard visualizations"
        )
        step.start()
        result.add_step(step)

        try:
            views = {}

            # OVERVIEW - Global KPIs
            views["overview"] = {
                "total_montant_ttc": float(df['montant_ttc'].sum()),
                "total_encaissement": float(df['encaissement'].sum()),
                "total_montant_restant": float(df['montant_restant'].sum()),
                "taux_encaissement_global": float(
                    (df['encaissement'].sum() / df['montant_ttc'].sum() * 100) if df['montant_ttc'].sum() > 0 else 0
                ),
                "nombre_factures": int(df['n_fact'].count()),
                "nombre_organisations": int(df['organisation'].nunique())
            }

            # View 1: By Month (for combined bar chart)
            if 'mois' in df.columns:
                monthly_agg = df.groupby('mois').agg({
                    'montant_ttc': 'sum',
                    'encaissement': 'sum',
                    'montant_restant': 'sum'
                }).reset_index()

                monthly_agg['taux_encaissement'] = (
                    (monthly_agg['encaissement'] / monthly_agg['montant_ttc'] * 100)
                    .fillna(0)
                    .round(2)
                )

                views["by_month"] = monthly_agg.to_dict('records')

            # View 2: By DOT/Organisation (for DOT taux chart)
            if 'organisation' in df.columns:
                dot_agg = df.groupby('organisation').agg({
                    'montant_ttc': 'sum',
                    'encaissement': 'sum',
                    'montant_restant': 'sum',
                    'n_fact': 'count'
                }).reset_index()

                dot_agg['taux_encaissement'] = (
                    (dot_agg['encaissement'] / dot_agg['montant_ttc'] * 100)
                    .fillna(0)
                    .round(2)
                )

                # Sort by taux_encaissement descending
                dot_agg = dot_agg.sort_values('taux_encaissement', ascending=False)

                views["by_dot"] = dot_agg.to_dict('records')

            # View 3: Monthly encaissement distribution (for pie chart)
            if 'mois' in df.columns:
                monthly_enc = df.groupby('mois')['encaissement'].sum().reset_index()
                monthly_enc['percentage'] = (
                    (monthly_enc['encaissement'] / monthly_enc['encaissement'].sum() * 100)
                    .fillna(0)
                    .round(2)
                )
                views["monthly_distribution"] = monthly_enc.to_dict('records')

            result.summary_metrics.update(views)

            step.metadata["views_generated"] = list(views.keys())
            step.complete()

            logger.info(f"📊 Generated {len(views)} visualization views")

        except Exception as e:
            step.fail(str(e))
            raise

    def _output_step(self, clean_df: pd.DataFrame, anomalies_df: pd.DataFrame, result: ETLResult) -> None:
        """Step 7: Output Encaissement AR DOT results"""
        step = ETLStep(
            step_type=ETLStepType.OUTPUT,
            name="output_results",
            description="Save processed Encaissement data and anomalies to files"
        )
        step.start()
        result.add_step(step)

        try:
            timestamp = datetime.now()
            base_dir = Path("uploads/temp/etl/encaissement_ar_dot")

            # Save cleaned data
            if not clean_df.empty:
                clean_filename = ETLUtils.generate_timestamped_filename(
                    "encaissement_ar_dot_cleaned", "xlsx", timestamp
                )
                clean_path = base_dir / clean_filename
                ETLUtils.save_dataframe(clean_df, clean_path, format="excel")
                result.output_files.append(clean_path)
                logger.info(f"💾 Saved cleaned data: {clean_path}")

            # Save anomalies
            if not anomalies_df.empty:
                anomaly_dir = Path("uploads/temp/anomalies/encaissement_ar_dot")
                anomaly_filename = ETLUtils.generate_timestamped_filename(
                    "encaissement_ar_dot_anomalies", "xlsx", timestamp
                )
                anomaly_path = anomaly_dir / anomaly_filename
                ETLUtils.save_dataframe(anomalies_df, anomaly_path, format="excel")
                result.anomaly_files.append(anomaly_path)
                logger.info(f"⚠️ Saved anomalies: {anomaly_path}")

            step.metadata["files_created"] = len(result.output_files) + len(result.anomaly_files)
            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    def save_to_database(self, clean_df: pd.DataFrame, anomalies_df: pd.DataFrame,
                        file_upload_id: int, db_session, result: ETLResult) -> Dict[str, int]:
        """
        Save processed data to database with DOT relationships for RBAC

        Args:
            clean_df: Cleaned encaissement data
            anomalies_df: Anomaly records
            file_upload_id: ID of uploaded file
            db_session: SQLAlchemy database session
            result: ETLResult containing aggregated views

        Returns:
            Dictionary with counts of saved records
        """
        from models.encaissement import EncaissementARDot, EncaissementAnomaly, EncaissementAggregateView
        from models.dot import DOT

        logger.info(f"💾 Saving Encaissement AR DOT data to database...")

        saved_counts = {
            "main_records": 0,
            "anomalies": 0,
            "aggregates": 0
        }

        try:
            # Get DOT mapping for RBAC
            dot_mapping = {}
            dots = db_session.query(DOT).all()
            for dot in dots:
                dot_mapping[dot.name.upper()] = dot.id

            # Save main records
            for idx, row in clean_df.iterrows():
                # Match DOT
                org_name = str(row.get('organisation', '')).upper()
                matched_dot_id = None
                for dot_name, dot_id in dot_mapping.items():
                    if dot_name in org_name or org_name in dot_name:
                        matched_dot_id = dot_id
                        break

                # Create record
                record = EncaissementARDot(
                    file_upload_id=file_upload_id,
                    dot_id=matched_dot_id,
                    organisation=row.get('organisation'),
                    source=row.get('source'),
                    n_fact=int(row.get('n_fact', 0)) if pd.notna(row.get('n_fact')) else None,
                    typ_fact=row.get('typ_fact'),
                    date_fact=row.get('date_fact') if pd.notna(row.get('date_fact')) else None,
                    mois=row.get('mois') if pd.notna(row.get('mois')) else None,
                    client=row.get('client') if pd.notna(row.get('client')) else None,
                    n_client=row.get('n_client') if pd.notna(row.get('n_client')) else None,
                    obj_fact=row.get('obj_fact') if pd.notna(row.get('obj_fact')) else None,
                    periode=row.get('periode') if pd.notna(row.get('periode')) else None,
                    ref=row.get('ref') if pd.notna(row.get('ref')) else None,
                    termine_flag=row.get('termine_flag') if pd.notna(row.get('termine_flag')) else None,
                    creer_par=row.get('creer_par') if pd.notna(row.get('creer_par')) else None,
                    montant_ht=float(row.get('montant_ht', 0)) if pd.notna(row.get('montant_ht')) else None,
                    montant_taxe=float(row.get('montant_taxe', 0)) if pd.notna(row.get('montant_taxe')) else None,
                    montant_ttc=float(row.get('montant_ttc', 0)) if pd.notna(row.get('montant_ttc')) else None,
                    chiffre_aff_exe=float(row.get('chiffre_aff_exe', 0)) if pd.notna(row.get('chiffre_aff_exe')) else None,
                    encaissement=float(row.get('encaissement', 0)) if pd.notna(row.get('encaissement')) else None,
                    n_rglt=row.get('n_rglt') if pd.notna(row.get('n_rglt')) else None,
                    date_rglt=row.get('date_rglt') if pd.notna(row.get('date_rglt')) else None,
                    facture_avoir_annulation=row.get('facture_avoir_annulation') if pd.notna(row.get('facture_avoir_annulation')) else None,
                    taux_encaissement=float(row.get('taux_encaissement', 0)) if pd.notna(row.get('taux_encaissement')) else None,
                    montant_restant=float(row.get('montant_restant', 0)) if pd.notna(row.get('montant_restant')) else None,
                    composite_key=row.get('composite_key'),
                    is_duplicate=bool(row.get('is_duplicate', False)),
                    is_anomaly=False
                )
                db_session.add(record)
                saved_counts["main_records"] += 1

            # Save anomalies
            if not anomalies_df.empty:
                for idx, row in anomalies_df.iterrows():
                    # Match DOT
                    org_name = str(row.get('organisation', '')).upper()
                    matched_dot_id = None
                    for dot_name, dot_id in dot_mapping.items():
                        if dot_name in org_name or org_name in dot_name:
                            matched_dot_id = dot_id
                            break

                    anomaly = EncaissementAnomaly(
                        file_upload_id=file_upload_id,
                        dot_id=matched_dot_id,
                        organisation=row.get('organisation'),
                        n_fact=int(row.get('n_fact', 0)) if pd.notna(row.get('n_fact')) else None,
                        typ_fact=row.get('typ_fact'),
                        montant_ttc=float(row.get('montant_ttc', 0)) if pd.notna(row.get('montant_ttc')) else None,
                        encaissement=float(row.get('encaissement', 0)) if pd.notna(row.get('encaissement')) else None,
                        anomaly_type=row.get('anomaly_type', 'Unknown'),
                        anomaly_reason=row.get('anomaly_reason'),
                        original_data=json.dumps(row.to_dict(), default=str)
                    )
                    db_session.add(anomaly)
                    saved_counts["anomalies"] += 1

            # Save aggregated views
            if 'by_month' in result.summary_metrics:
                for month_data in result.summary_metrics['by_month']:
                    aggregate = EncaissementAggregateView(
                        file_upload_id=file_upload_id,
                        dot_id=None,
                        view_type='by_month',
                        mois=month_data.get('mois'),
                        total_montant_ttc=float(month_data.get('montant_ttc', 0)),
                        total_encaissement=float(month_data.get('encaissement', 0)),
                        total_montant_restant=float(month_data.get('montant_restant', 0)),
                        taux_encaissement=float(month_data.get('taux_encaissement', 0))
                    )
                    db_session.add(aggregate)
                    saved_counts["aggregates"] += 1

            if 'by_dot' in result.summary_metrics:
                for dot_data in result.summary_metrics['by_dot']:
                    # Match DOT
                    org_name = str(dot_data.get('organisation', '')).upper()
                    matched_dot_id = None
                    for dot_name, dot_id in dot_mapping.items():
                        if dot_name in org_name or org_name in dot_name:
                            matched_dot_id = dot_id
                            break

                    aggregate = EncaissementAggregateView(
                        file_upload_id=file_upload_id,
                        dot_id=matched_dot_id,
                        view_type='by_dot',
                        organisation=dot_data.get('organisation'),
                        total_montant_ttc=float(dot_data.get('montant_ttc', 0)),
                        total_encaissement=float(dot_data.get('encaissement', 0)),
                        total_montant_restant=float(dot_data.get('montant_restant', 0)),
                        taux_encaissement=float(dot_data.get('taux_encaissement', 0)),
                        nombre_factures=int(dot_data.get('n_fact', 0))
                    )
                    db_session.add(aggregate)
                    saved_counts["aggregates"] += 1

            # Save overview
            if 'overview' in result.summary_metrics:
                overview = result.summary_metrics['overview']
                aggregate = EncaissementAggregateView(
                    file_upload_id=file_upload_id,
                    dot_id=None,
                    view_type='overview',
                    total_montant_ttc=float(overview.get('total_montant_ttc', 0)),
                    total_encaissement=float(overview.get('total_encaissement', 0)),
                    total_montant_restant=float(overview.get('total_montant_restant', 0)),
                    taux_encaissement=float(overview.get('taux_encaissement_global', 0)),
                    nombre_factures=int(overview.get('nombre_factures', 0))
                )
                db_session.add(aggregate)
                saved_counts["aggregates"] += 1

            # Commit all changes
            db_session.commit()

            logger.info(f"✅ Saved to database: {saved_counts['main_records']} records, "
                       f"{saved_counts['anomalies']} anomalies, {saved_counts['aggregates']} aggregates")

            return saved_counts

        except Exception as e:
            db_session.rollback()
            logger.error(f"❌ Error saving to database: {str(e)}")
            raise

    def _clean_organisation_name(self, org_name: str) -> str:
        """Clean organization name according to business rules"""
        if not org_name or pd.isna(org_name):
            return ""

        org_name = str(org_name).strip()

        # Remove DOT_ prefix
        org_name = org_name.replace("DOT_", "")

        # Replace separators (- and _) with spaces
        org_name = org_name.replace("-", " ").replace("_", " ")

        # Remove extra whitespace
        org_name = " ".join(org_name.split())

        return org_name

    def _map_column_names(self, columns: List[str]) -> Dict[str, str]:
        """Map various column name variations to standard names"""
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()

            # Standard mappings
            if 'organisation' in col_lower or ('org' in col_lower and 'name' in col_lower):
                mapping[col] = 'organisation'
            elif 'source' in col_lower:
                mapping[col] = 'source'
            elif 'n' in col_lower and 'fact' in col_lower and 'typ' not in col_lower:
                mapping[col] = 'n_fact'
            elif 'typ' in col_lower and 'fact' in col_lower:
                mapping[col] = 'typ_fact'
            elif 'date' in col_lower and 'fact' in col_lower:
                mapping[col] = 'date_fact'
            elif 'client' in col_lower and 'n' not in col_lower:
                mapping[col] = 'client'
            elif 'n' in col_lower and 'client' in col_lower:
                mapping[col] = 'n_client'
            elif 'obj' in col_lower and 'fact' in col_lower:
                mapping[col] = 'obj_fact'
            elif 'periode' in col_lower:
                mapping[col] = 'periode'
            elif 'ref' in col_lower and 'fact' not in col_lower:
                mapping[col] = 'ref'
            elif 'termine' in col_lower:
                mapping[col] = 'termine_flag'
            elif 'creer' in col_lower:
                mapping[col] = 'creer_par'
            elif 'montant' in col_lower and 'ht' in col_lower:
                mapping[col] = 'montant_ht'
            elif 'montant' in col_lower and ('taxe' in col_lower or 'tax' in col_lower):
                mapping[col] = 'montant_taxe'
            elif 'montant' in col_lower and 'ttc' in col_lower:
                mapping[col] = 'montant_ttc'
            elif 'chiffre' in col_lower and 'aff' in col_lower:
                mapping[col] = 'chiffre_aff_exe'
            elif 'encaissement' in col_lower:
                mapping[col] = 'encaissement'
            elif 'n' in col_lower and 'rglt' in col_lower:
                mapping[col] = 'n_rglt'
            elif 'date' in col_lower and 'rglt' in col_lower:
                mapping[col] = 'date_rglt'
            elif 'facture' in col_lower and 'avoir' in col_lower:
                mapping[col] = 'facture_avoir_annulation'

        return mapping

    def _calculate_summary_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary metrics for the Encaissement AR data"""
        metrics = {}

        try:
            metrics["total_organisations"] = int(df['organisation'].nunique()) if 'organisation' in df.columns else 0
            metrics["total_factures"] = int(df['n_fact'].count()) if 'n_fact' in df.columns else 0
            metrics["total_montant_ttc"] = float(df['montant_ttc'].sum()) if 'montant_ttc' in df.columns else 0.0
            metrics["total_encaissement"] = float(df['encaissement'].sum()) if 'encaissement' in df.columns else 0.0
            metrics["total_montant_restant"] = float(df['montant_restant'].sum()) if 'montant_restant' in df.columns else 0.0

            if 'taux_encaissement' in df.columns:
                metrics["avg_taux_encaissement"] = float(df['taux_encaissement'].mean())
                metrics["median_taux_encaissement"] = float(df['taux_encaissement'].median())

            # Top and bottom performers
            if 'taux_encaissement' in df.columns and 'organisation' in df.columns:
                org_performance = df.groupby('organisation')['taux_encaissement'].mean().sort_values(ascending=False)
                metrics["best_performing_dot"] = str(org_performance.index[0]) if len(org_performance) > 0 else None
                metrics["worst_performing_dot"] = str(org_performance.index[-1]) if len(org_performance) > 0 else None

            # Monthly stats
            if 'mois' in df.columns:
                metrics["nombre_mois"] = int(df['mois'].nunique())
                monthly_avg = df.groupby('mois')['encaissement'].sum().mean()
                metrics["avg_monthly_encaissement"] = float(monthly_avg)

        except Exception as e:
            logger.error(f"Error calculating summary metrics: {str(e)}")

        return metrics
