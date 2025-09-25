"""
Encaissement KPI ETL Module
Processes encaissement (collection) data with specific business rules
Handles data cleaning, anomaly detection, and KPI calculations
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .base import ETLResult, ETLStep, ETLStepType, BaseETLProcessor
from .utils import ETLUtils

logger = logging.getLogger(__name__)


class EncaissementETL(BaseETLProcessor):
    """ETL processor for Encaissement KPI data"""

    def __init__(self):
        super().__init__()
        self.kpi_name = "encaissement"
        self.required_columns = [
            "org_name",
            "n_fact",
            "montant_ttc",
            "encaissement"
        ]

    def run_etl(self, input_paths: List[Path]) -> ETLResult:
        """
        Main ETL entry point for Encaissement data processing

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
                raise ValueError("No data found in input files")

            # Limit rows for testing
            combined_df = self.limit_dataframe_rows(combined_df)
            result.input_records_count = len(combined_df)

            # Step 2: Clean data
            cleaned_df = self._clean_step(combined_df, result)

            # Step 3: Validate data
            validated_df = self._validate_step(cleaned_df, result)

            # Step 4: Transform data (calculate KPIs)
            transformed_df = self._transform_step(validated_df, result)

            # Step 5: Detect anomalies
            final_df, anomalies_df = self._detect_anomalies_step(
                transformed_df, result)

            # Step 6: Output results
            self._output_step(final_df, anomalies_df, result)

            result.output_records_count = len(final_df)
            result.anomaly_records_count = len(anomalies_df)

        except Exception as e:
            error_msg = f"ETL process failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        finally:
            result.complete()

        return result

    def _ingest_step(self, input_paths: List[Path], result: ETLResult) -> pd.DataFrame:
        """Step 1: Ingest and combine input files"""
        step = ETLStep(
            step_type=ETLStepType.INGEST,
            name="ingest_files",
            description="Read and combine input files with header normalization"
        )
        step.start()
        result.add_step(step)

        combined_data = []

        try:
            for file_path in input_paths:
                try:
                    df = ETLUtils.ingest_file(file_path)
                    combined_data.append(df)
                    step.records_processed += len(df)
                    logger.info(
                        f"Ingested {file_path.name}: {len(df)} records")

                except Exception as e:
                    error_msg = f"Error ingesting {file_path.name}: {str(e)}"
                    step.add_warning(error_msg)

            if not combined_data:
                raise ValueError("No valid data files found")

            # Combine all DataFrames
            combined_df = pd.concat(combined_data, ignore_index=True)

            step.metadata["files_processed"] = len(combined_data)
            step.metadata["files_failed"] = len(
                input_paths) - len(combined_data)

            step.complete(len(combined_df))
            return combined_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 2: Clean and standardize data"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="clean_data",
            description="Apply encaissement-specific cleaning rules"
        )
        step.start()
        result.add_step(step)

        try:
            cleaned_df = df.copy()
            step.records_processed = len(cleaned_df)

            # Clean organization names (specific to encaissement business rules)
            if 'org_name' in cleaned_df.columns:
                original_count = len(cleaned_df)

                # Remove AT_SIEGE entries
                cleaned_df = cleaned_df[~cleaned_df['org_name'].str.contains(
                    'AT_SIEGE', na=False)]
                at_siege_removed = original_count - len(cleaned_df)
                if at_siege_removed > 0:
                    step.add_warning(
                        f"Removed {at_siege_removed} AT_SIEGE entries")

                # Clean org name format
                cleaned_df['org_name'] = cleaned_df['org_name'].apply(
                    self._clean_org_name)

                # Remove empty org names
                cleaned_df = cleaned_df[cleaned_df['org_name'].str.strip(
                ) != '']
                empty_removed = len(cleaned_df) - \
                    (original_count - at_siege_removed)
                if empty_removed < 0:
                    step.add_warning(
                        f"Removed {abs(empty_removed)} empty org names")

            # Clean numeric columns
            numeric_columns = ['montant_ttc', 'encaissement']
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df = ETLUtils.clean_numeric_column(
                        cleaned_df, col, decimal_separator=",", thousands_separator=""
                    )

            step.metadata["cleaning_rules_applied"] = [
                "Remove AT_SIEGE entries",
                "Clean org names",
                "Convert numeric columns"
            ]

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
            missing_columns = ETLUtils.validate_required_columns(
                validated_df, self.required_columns)
            if missing_columns:
                step.fail(f"Missing required columns: {missing_columns}")
                return validated_df

            # Remove rows with null values in critical columns
            critical_columns = ['org_name', 'n_fact']
            original_count = len(validated_df)

            for col in critical_columns:
                if col in validated_df.columns:
                    validated_df = validated_df.dropna(subset=[col])

            dropped_count = original_count - len(validated_df)
            if dropped_count > 0:
                step.add_warning(
                    f"Dropped {dropped_count} rows with null critical values")

            # Validate data types
            validation_issues = []

            if 'n_fact' in validated_df.columns:
                non_numeric_facts = validated_df[pd.to_numeric(
                    validated_df['n_fact'], errors='coerce').isna()]
                if len(non_numeric_facts) > 0:
                    validation_issues.append(
                        f"{len(non_numeric_facts)} invalid n_fact values")

            if validation_issues:
                for issue in validation_issues:
                    step.add_warning(issue)

            step.metadata["validation_checks"] = [
                "Required columns present",
                "Critical fields not null",
                "Data type validation"
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
            description="Calculate encaissement rate and other KPIs"
        )
        step.start()
        result.add_step(step)

        try:
            transformed_df = df.copy()
            step.records_processed = len(transformed_df)

            # Calculate encaissement rate
            if 'montant_ttc' in transformed_df.columns and 'encaissement' in transformed_df.columns:
                transformed_df['taux_encaissement'] = np.where(
                    transformed_df['montant_ttc'] > 0,
                    (transformed_df['encaissement'] /
                     transformed_df['montant_ttc'] * 100).round(2),
                    0
                )

                # Handle infinite values
                transformed_df['taux_encaissement'] = transformed_df['taux_encaissement'].replace(
                    [np.inf, -np.inf], 0
                )

            # Add derived metrics
            transformed_df['montant_restant'] = transformed_df['montant_ttc'] - \
                transformed_df['encaissement']

            # Calculate summary metrics for result
            result.summary_metrics = self._calculate_summary_metrics(
                transformed_df)

            step.metadata["kpis_calculated"] = [
                "taux_encaissement",
                "montant_restant"
            ]

            step.complete(len(transformed_df))
            return transformed_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _detect_anomalies_step(self, df: pd.DataFrame, result: ETLResult) -> tuple:
        """Step 5: Detect anomalies based on business rules"""
        step = ETLStep(
            step_type=ETLStepType.DETECT_ANOMALIES,
            name="detect_anomalies",
            description="Identify anomalous records based on business rules"
        )
        step.start()
        result.add_step(step)

        try:
            step.records_processed = len(df)

            # Define anomaly detection rules for encaissement data
            anomaly_rules = {
                "negative_montant": {
                    "type": "range_check",
                    "column": "montant_ttc",
                    "min": 0
                },
                "negative_encaissement": {
                    "type": "range_check",
                    "column": "encaissement",
                    "min": 0
                },
                "excessive_encaissement_rate": {
                    "type": "range_check",
                    "column": "taux_encaissement",
                    "min": 0,
                    "max": 120  # Allow some margin for over-collection
                },
                "zero_facts": {
                    "type": "range_check",
                    "column": "n_fact",
                    "min": 1
                }
            }

            clean_data, anomalies = ETLUtils.detect_anomalies(
                df, anomaly_rules)

            step.metadata["anomaly_rules"] = list(anomaly_rules.keys())
            step.metadata["anomalies_found"] = len(anomalies)

            step.complete(len(clean_data))
            return clean_data, anomalies

        except Exception as e:
            step.fail(str(e))
            raise

    def _output_step(self, clean_df: pd.DataFrame, anomalies_df: pd.DataFrame, result: ETLResult) -> None:
        """Step 6: Output cleaned data and anomalies"""
        step = ETLStep(
            step_type=ETLStepType.OUTPUT,
            name="output_results",
            description="Save cleaned data and anomalies to files"
        )
        step.start()
        result.add_step(step)

        try:
            timestamp = datetime.now()
            base_dir = Path("uploads/temp/etl/encaissement")

            # Save cleaned data
            if not clean_df.empty:
                clean_filename = ETLUtils.generate_timestamped_filename(
                    "encaissement_cleaned", "xlsx", timestamp
                )
                clean_path = base_dir / clean_filename
                ETLUtils.save_dataframe(clean_df, clean_path, format="excel")
                result.output_files.append(clean_path)

            # Save anomalies
            if not anomalies_df.empty:
                anomaly_dir = Path("uploads/temp/anomalies/encaissement")
                anomaly_filename = ETLUtils.generate_timestamped_filename(
                    "encaissement_anomalies", "xlsx", timestamp
                )
                anomaly_path = anomaly_dir / anomaly_filename
                ETLUtils.save_dataframe(
                    anomalies_df, anomaly_path, format="excel")
                result.anomaly_files.append(anomaly_path)

            step.metadata["files_created"] = len(
                result.output_files) + len(result.anomaly_files)
            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_org_name(self, org_name: str) -> str:
        """Clean organization name according to business rules"""
        if not org_name or pd.isna(org_name):
            return ""

        org_name = str(org_name).strip()

        # Remove DOT_ prefix
        org_name = org_name.replace("DOT_", "")

        # Replace separators with spaces
        org_name = org_name.replace("-", " ").replace("_", " ")

        # Remove extra whitespace
        org_name = " ".join(org_name.split())

        return org_name

    def _calculate_summary_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary metrics for the encaissement data"""
        metrics = {}

        try:
            metrics["total_organisations"] = df['org_name'].nunique()
            metrics["total_factures"] = df['n_fact'].sum(
            ) if 'n_fact' in df.columns else 0
            metrics["total_montant_ttc"] = df['montant_ttc'].sum(
            ) if 'montant_ttc' in df.columns else 0
            metrics["total_encaissement"] = df['encaissement'].sum(
            ) if 'encaissement' in df.columns else 0

            if 'taux_encaissement' in df.columns:
                metrics["avg_encaissement_rate"] = df['taux_encaissement'].mean()
                metrics["median_encaissement_rate"] = df['taux_encaissement'].median()

            # Top and bottom performers
            if 'taux_encaissement' in df.columns and 'org_name' in df.columns:
                org_performance = df.groupby(
                    'org_name')['taux_encaissement'].mean().sort_values(ascending=False)
                metrics["best_performing_org"] = org_performance.index[0] if len(
                    org_performance) > 0 else None
                metrics["worst_performing_org"] = org_performance.index[-1] if len(
                    org_performance) > 0 else None

        except Exception as e:
            logger.error(f"Error calculating summary metrics: {str(e)}")

        return metrics
