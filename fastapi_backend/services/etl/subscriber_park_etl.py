"""
Subscriber Park Report ETL Module
Processes telecom subscriber park data with specific business rules
Handles Algérie Télécom subscriber data cleaning and standardization
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re

from .base import ETLResult, ETLStep, ETLStepType
from .utils import ETLUtils

logger = logging.getLogger(__name__)


class SubscriberParkETL:
    """ETL processor for Subscriber Park Report data"""

    def __init__(self):
        self.kpi_name = "subscriber_park"
        self.required_columns = [
            "extraction_date_date_d_extraction",
            "dot",
            "actel_code_code_d_actel",
            "customer_code_ncli",
            "service_number_nd",
            "subscriber_status_status_de_l_abonne"
        ]

    def run_etl(self, input_paths: List[Path]) -> ETLResult:
        """
        Main ETL entry point for Subscriber Park data processing

        Args:
            input_paths: List of input file paths to process

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
            # Step 1: Ingest data
            combined_df = self._ingest_step(input_paths, result)
            if combined_df.empty:
                raise ValueError("No subscriber data found in input files")

            result.input_records_count = len(combined_df)

            # Step 2: Clean data
            cleaned_df = self._clean_step(combined_df, result)

            # Step 3: Validate data
            validated_df = self._validate_step(cleaned_df, result)

            # Step 4: Transform data (standardize formats)
            transformed_df = self._transform_step(validated_df, result)

            # Step 5: Detect anomalies
            final_df, anomalies_df = self._detect_anomalies_step(transformed_df, result)

            # Step 6: Output results
            self._output_step(final_df, anomalies_df, result)

            result.output_records_count = len(final_df)
            result.anomaly_records_count = len(anomalies_df)

        except Exception as e:
            error_msg = f"Subscriber Park ETL process failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        finally:
            result.complete()

        return result

    def _ingest_step(self, input_paths: List[Path], result: ETLResult) -> pd.DataFrame:
        """Step 1: Ingest subscriber park CSV files"""
        step = ETLStep(
            step_type=ETLStepType.INGEST,
            name="ingest_subscriber_files",
            description="Read and combine subscriber park CSV files"
        )
        step.start()
        result.add_step(step)

        combined_data = []

        try:
            for file_path in input_paths:
                try:
                    # Read CSV with specific settings for telecom data
                    df = ETLUtils.ingest_file(
                        file_path,
                        encoding='utf-8',
                        sep='\t'  # Tab separated based on your data
                    )
                    combined_data.append(df)
                    step.records_processed += len(df)
                    logger.info(f"Ingested subscriber file {file_path.name}: {len(df)} records")

                except Exception as e:
                    error_msg = f"Error ingesting {file_path.name}: {str(e)}"
                    step.add_warning(error_msg)

            if not combined_data:
                raise ValueError("No valid subscriber park files found")

            combined_df = pd.concat(combined_data, ignore_index=True)
            step.complete(len(combined_df))
            return combined_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 2: Clean subscriber park data"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="clean_subscriber_data",
            description="Apply subscriber park specific cleaning rules"
        )
        step.start()
        result.add_step(step)

        try:
            cleaned_df = df.copy()
            step.records_processed = len(cleaned_df)

            # Clean DOT field - handle empty DOT values
            if 'dot' in cleaned_df.columns:
                # Fill empty DOT values from Actel Code when possible
                cleaned_df['dot'] = cleaned_df.apply(self._resolve_dot_from_actel, axis=1)

            # Clean Actel Code - extract numeric part
            if 'actel_code_code_d_actel' in cleaned_df.columns:
                cleaned_df['actel_code_clean'] = cleaned_df['actel_code_code_d_actel'].apply(
                    self._clean_actel_code
                )

            # Clean rental fees - comma to dot conversion
            if 'rental_fees_frais_d_abonnement' in cleaned_df.columns:
                cleaned_df = ETLUtils.clean_numeric_column(
                    cleaned_df,
                    'rental_fees_frais_d_abonnement',
                    decimal_separator=",",
                    thousands_separator=""
                )

            # Clean customer codes - handle large numbers properly
            numeric_id_columns = [
                'customer_code_ncli',
                'service_number_nd',
                'related_service_number_numero_de_service_correspondant'
            ]

            for col in numeric_id_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].apply(self._clean_customer_code)

            # Clean status fields - standardize
            if 'subscriber_status_status_de_l_abonne' in cleaned_df.columns:
                cleaned_df['subscriber_status_status_de_l_abonne'] = (
                    cleaned_df['subscriber_status_status_de_l_abonne']
                    .str.strip()
                    .str.title()
                )

            step.metadata["cleaning_rules_applied"] = [
                "DOT resolution from Actel codes",
                "Actel code numeric extraction",
                "Decimal separator normalization",
                "Customer code standardization",
                "Status field standardization"
            ]

            step.complete(len(cleaned_df))
            return cleaned_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _validate_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 3: Validate subscriber data quality"""
        step = ETLStep(
            step_type=ETLStepType.VALIDATE,
            name="validate_subscriber_data",
            description="Validate subscriber data structure and quality"
        )
        step.start()
        result.add_step(step)

        try:
            validated_df = df.copy()
            step.records_processed = len(validated_df)

            # Check required columns
            missing_columns = ETLUtils.validate_required_columns(validated_df, self.required_columns)
            if missing_columns:
                step.add_warning(f"Missing columns (using available data): {missing_columns}")

            # Remove rows with null critical values
            critical_columns = ['customer_code_ncli', 'service_number_nd']
            original_count = len(validated_df)

            for col in critical_columns:
                if col in validated_df.columns:
                    before_count = len(validated_df)
                    validated_df = validated_df.dropna(subset=[col])
                    dropped = before_count - len(validated_df)
                    if dropped > 0:
                        step.add_warning(f"Dropped {dropped} rows with null {col}")

            # Validate service numbers format
            if 'service_number_nd' in validated_df.columns:
                invalid_service_numbers = validated_df[
                    ~validated_df['service_number_nd'].astype(str).str.match(r'^\d+$', na=False)
                ]
                if len(invalid_service_numbers) > 0:
                    step.add_warning(f"{len(invalid_service_numbers)} invalid service number formats")

            step.complete(len(validated_df))
            return validated_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _transform_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 4: Transform and standardize subscriber data"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="transform_subscriber_data",
            description="Standardize formats and calculate derived fields"
        )
        step.start()
        result.add_step(step)

        try:
            transformed_df = df.copy()
            step.records_processed = len(transformed_df)

            # Add derived fields
            if 'customer_code_ncli' in transformed_df.columns:
                # Add customer code category based on range
                transformed_df['customer_category'] = transformed_df['customer_code_ncli'].apply(
                    self._categorize_customer_code
                )

            # Standardize DOT names
            if 'dot' in transformed_df.columns:
                transformed_df['dot_standardized'] = transformed_df['dot'].apply(
                    self._standardize_dot_name
                )

            # Calculate days since creation
            if 'creation_date_date_de_creation' in transformed_df.columns:
                transformed_df['creation_date_parsed'] = pd.to_datetime(
                    transformed_df['creation_date_date_de_creation'],
                    errors='coerce'
                )
                transformed_df['days_since_creation'] = (
                    datetime.now() - transformed_df['creation_date_parsed']
                ).dt.days

            # Service type classification
            if 'telecom_type_service_produit' in transformed_df.columns:
                transformed_df['service_category'] = transformed_df['telecom_type_service_produit'].apply(
                    self._classify_service_type
                )

            # Calculate summary metrics for result
            result.summary_metrics = self._calculate_subscriber_summary(transformed_df)

            step.metadata["transformations_applied"] = [
                "customer_category",
                "dot_standardized",
                "days_since_creation",
                "service_category"
            ]

            step.complete(len(transformed_df))
            return transformed_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _detect_anomalies_step(self, df: pd.DataFrame, result: ETLResult) -> tuple:
        """Step 5: Detect subscriber data anomalies"""
        step = ETLStep(
            step_type=ETLStepType.DETECT_ANOMALIES,
            name="detect_subscriber_anomalies",
            description="Identify anomalous subscriber records"
        )
        step.start()
        result.add_step(step)

        try:
            step.records_processed = len(df)

            # Define anomaly detection rules for subscriber data
            anomaly_rules = {
                "invalid_service_number": {
                    "type": "pattern_check",
                    "column": "service_number_nd",
                    "pattern": r"^\d{8,12}$"  # 8-12 digit service numbers
                },
                "future_creation_date": {
                    "type": "range_check",
                    "column": "days_since_creation",
                    "min": 0  # Creation date can't be in future
                },
                "negative_rental_fees": {
                    "type": "range_check",
                    "column": "rental_fees_frais_d_abonnement",
                    "min": 0
                },
                "missing_dot": {
                    "type": "null_check",
                    "column": "dot"
                }
            }

            clean_data, anomalies = ETLUtils.detect_anomalies(df, anomaly_rules)

            step.metadata["anomaly_rules"] = list(anomaly_rules.keys())
            step.complete(len(clean_data))
            return clean_data, anomalies

        except Exception as e:
            step.fail(str(e))
            raise

    def _output_step(self, clean_df: pd.DataFrame, anomalies_df: pd.DataFrame, result: ETLResult) -> None:
        """Step 6: Output subscriber park results"""
        step = ETLStep(
            step_type=ETLStepType.OUTPUT,
            name="output_subscriber_results",
            description="Save processed subscriber data and anomalies"
        )
        step.start()
        result.add_step(step)

        try:
            timestamp = datetime.now()
            base_dir = Path("uploads/temp/etl/subscriber_park")

            # Save cleaned data
            if not clean_df.empty:
                clean_filename = ETLUtils.generate_timestamped_filename(
                    "subscriber_park_cleaned", "xlsx", timestamp
                )
                clean_path = base_dir / clean_filename
                ETLUtils.save_dataframe(clean_df, clean_path, format="excel")
                result.output_files.append(clean_path)

            # Save anomalies
            if not anomalies_df.empty:
                anomaly_dir = Path("uploads/temp/anomalies/subscriber_park")
                anomaly_filename = ETLUtils.generate_timestamped_filename(
                    "subscriber_park_anomalies", "xlsx", timestamp
                )
                anomaly_path = anomaly_dir / anomaly_filename
                ETLUtils.save_dataframe(anomalies_df, anomaly_path, format="excel")
                result.anomaly_files.append(anomaly_path)

            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    # Helper methods for data cleaning

    def _resolve_dot_from_actel(self, row) -> str:
        """Resolve DOT from Actel code when DOT is missing"""
        dot = row.get('dot', '').strip()
        if dot:
            return dot

        actel_code = str(row.get('actel_code_code_d_actel', ''))
        if 'CONSTANTINE' in actel_code.upper():
            return 'CONSTANTINE'
        elif 'HASSI MESSAOUD' in actel_code.upper():
            return 'OUARGLA'  # Hassi Messaoud is under Ouargla DOT
        elif 'ALGER' in actel_code.upper():
            return 'ALGER'
        elif 'ORAN' in actel_code.upper():
            return 'ORAN'

        return 'UNKNOWN'

    def _clean_actel_code(self, actel_code: str) -> str:
        """Extract numeric part from Actel code"""
        if not actel_code or pd.isna(actel_code):
            return ""

        # Extract numeric part (e.g., "O2" -> "2", "2B" -> "2")
        numeric_match = re.search(r'(\d+)', str(actel_code))
        return numeric_match.group(1) if numeric_match else str(actel_code)

    def _clean_customer_code(self, code) -> str:
        """Format customer codes consistently"""
        if pd.isna(code):
            return ""

        try:
            # Convert to float first to handle scientific notation
            if isinstance(code, str) and 'E+' in code.upper():
                return code  # Keep scientific notation as is

            # For regular numbers, format appropriately
            num_val = float(str(code).replace(',', '.'))

            # If number is very large, use scientific notation
            if num_val >= 1e13:
                return f"{num_val:.5E}"
            else:
                return str(int(num_val))

        except (ValueError, TypeError):
            return str(code)

    def _categorize_customer_code(self, code) -> str:
        """Categorize customer based on code range"""
        if pd.isna(code):
            return "Unknown"

        try:
            if isinstance(code, str) and 'E+' in code.upper():
                return "Large Enterprise"

            num_val = float(str(code).replace(',', '.'))
            if num_val >= 7e13:
                return "Large Enterprise"
            elif num_val >= 7e12:
                return "Medium Enterprise"
            else:
                return "Standard Customer"

        except (ValueError, TypeError):
            return "Unknown"

    def _standardize_dot_name(self, dot_name: str) -> str:
        """Standardize DOT names"""
        if not dot_name or pd.isna(dot_name):
            return "UNKNOWN"

        dot_name = str(dot_name).strip().upper()

        # Standardize common DOT names
        if 'CONSTANTINE' in dot_name:
            return 'CONSTANTINE'
        elif 'OUARGLA' in dot_name or 'HASSI MESSAOUD' in dot_name:
            return 'OUARGLA'
        elif 'ALGER' in dot_name:
            return 'ALGER'
        elif 'ORAN' in dot_name:
            return 'ORAN'

        return dot_name

    def _classify_service_type(self, service_type: str) -> str:
        """Classify telecom service types"""
        if not service_type or pd.isna(service_type):
            return "Unknown"

        service_type = str(service_type).upper()

        if 'PSTN' in service_type:
            return "Fixed Line"
        elif 'MOBILE' in service_type or 'GSM' in service_type:
            return "Mobile"
        elif 'INTERNET' in service_type or 'ADSL' in service_type:
            return "Internet"
        elif 'DATA' in service_type:
            return "Data Services"

        return "Other"

    def _calculate_subscriber_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary metrics for subscriber data"""
        metrics = {}

        try:
            metrics["total_subscribers"] = len(df)

            if 'dot_standardized' in df.columns:
                metrics["unique_dots"] = df['dot_standardized'].nunique()
                dot_counts = df['dot_standardized'].value_counts().to_dict()
                metrics["dot_distribution"] = dot_counts

            if 'subscriber_status_status_de_l_abonne' in df.columns:
                status_counts = df['subscriber_status_status_de_l_abonne'].value_counts().to_dict()
                metrics["status_distribution"] = status_counts
                metrics["active_subscribers"] = status_counts.get('Active', 0)

            if 'customer_category' in df.columns:
                category_counts = df['customer_category'].value_counts().to_dict()
                metrics["customer_category_distribution"] = category_counts

            if 'service_category' in df.columns:
                service_counts = df['service_category'].value_counts().to_dict()
                metrics["service_type_distribution"] = service_counts

            if 'rental_fees_frais_d_abonnement' in df.columns:
                fees = df['rental_fees_frais_d_abonnement'].dropna()
                if len(fees) > 0:
                    metrics["avg_rental_fees"] = fees.mean()
                    metrics["total_monthly_revenue"] = fees.sum()

        except Exception as e:
            logger.error(f"Error calculating subscriber summary: {str(e)}")

        return metrics