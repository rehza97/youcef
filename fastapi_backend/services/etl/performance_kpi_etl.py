"""
Performance KPI ETL Module
Processes performance and operational data for DOT organizations
Handles data cleaning, anomaly detection, and performance metric calculations
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .base import ETLResult, ETLStep, ETLStepType
from .utils import ETLUtils

logger = logging.getLogger(__name__)


class PerformanceKpiETL:
    """ETL processor for Performance KPI data"""

    def __init__(self):
        self.kpi_name = "performance_kpi"
        self.required_columns = [
            "org_name",
            "period",
            "target_value",
            "actual_value",
            "metric_type"
        ]

    def run_etl(self, input_paths: List[Path]) -> ETLResult:
        """
        Main ETL entry point for Performance KPI data processing

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

            result.input_records_count = len(combined_df)

            # Step 2: Clean data
            cleaned_df = self._clean_step(combined_df, result)

            # Step 3: Validate data
            validated_df = self._validate_step(cleaned_df, result)

            # Step 4: Transform data (calculate KPIs)
            transformed_df = self._transform_step(validated_df, result)

            # Step 5: Detect anomalies
            final_df, anomalies_df = self._detect_anomalies_step(transformed_df, result)

            # Step 6: Output results
            self._output_step(final_df, anomalies_df, result)

            result.output_records_count = len(final_df)
            result.anomaly_records_count = len(anomalies_df)

        except Exception as e:
            error_msg = f"Performance KPI ETL process failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        finally:
            result.complete()

        return result

    def _ingest_step(self, input_paths: List[Path], result: ETLResult) -> pd.DataFrame:
        """Step 1: Ingest and combine input files"""
        step = ETLStep(
            step_type=ETLStepType.INGEST,
            name="ingest_performance_files",
            description="Read and combine performance data files"
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
                    logger.info(f"Ingested performance file {file_path.name}: {len(df)} records")

                except Exception as e:
                    error_msg = f"Error ingesting {file_path.name}: {str(e)}"
                    step.add_warning(error_msg)

            if not combined_data:
                raise ValueError("No valid performance data files found")

            combined_df = pd.concat(combined_data, ignore_index=True)
            step.complete(len(combined_df))
            return combined_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 2: Clean and standardize performance data"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="clean_performance_data",
            description="Apply performance KPI specific cleaning rules"
        )
        step.start()
        result.add_step(step)

        try:
            cleaned_df = df.copy()
            step.records_processed = len(cleaned_df)

            # Standardize organization names
            if 'org_name' in cleaned_df.columns:
                cleaned_df['org_name'] = cleaned_df['org_name'].apply(self._clean_org_name)
                cleaned_df = cleaned_df[cleaned_df['org_name'].str.strip() != '']

            # Clean numeric columns
            numeric_columns = ['target_value', 'actual_value']
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df = ETLUtils.clean_numeric_column(
                        cleaned_df, col, decimal_separator=",", thousands_separator=""
                    )

            # Standardize metric types
            if 'metric_type' in cleaned_df.columns:
                cleaned_df['metric_type'] = cleaned_df['metric_type'].str.strip().str.upper()

            # Standardize period format
            if 'period' in cleaned_df.columns:
                cleaned_df['period'] = cleaned_df['period'].astype(str).str.strip()

            step.complete(len(cleaned_df))
            return cleaned_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _validate_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 3: Validate performance data quality"""
        step = ETLStep(
            step_type=ETLStepType.VALIDATE,
            name="validate_performance_data",
            description="Validate performance data structure and quality"
        )
        step.start()
        result.add_step(step)

        try:
            validated_df = df.copy()
            step.records_processed = len(validated_df)

            # Check required columns
            missing_columns = ETLUtils.validate_required_columns(validated_df, self.required_columns)
            if missing_columns:
                step.fail(f"Missing required columns: {missing_columns}")
                return validated_df

            # Remove rows with null critical values
            critical_columns = ['org_name', 'period', 'metric_type']
            original_count = len(validated_df)

            for col in critical_columns:
                if col in validated_df.columns:
                    validated_df = validated_df.dropna(subset=[col])

            dropped_count = original_count - len(validated_df)
            if dropped_count > 0:
                step.add_warning(f"Dropped {dropped_count} rows with null critical values")

            # Validate metric types
            if 'metric_type' in validated_df.columns:
                valid_metrics = ['REVENUE', 'EFFICIENCY', 'QUALITY', 'CUSTOMER_SATISFACTION']
                invalid_metrics = validated_df[~validated_df['metric_type'].isin(valid_metrics)]
                if len(invalid_metrics) > 0:
                    step.add_warning(f"{len(invalid_metrics)} records with invalid metric types")

            step.complete(len(validated_df))
            return validated_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _transform_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 4: Transform data and calculate performance KPIs"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="calculate_performance_kpis",
            description="Calculate performance ratios and derived metrics"
        )
        step.start()
        result.add_step(step)

        try:
            transformed_df = df.copy()
            step.records_processed = len(transformed_df)

            # Calculate performance ratio
            if 'target_value' in transformed_df.columns and 'actual_value' in transformed_df.columns:
                transformed_df['performance_ratio'] = np.where(
                    transformed_df['target_value'] > 0,
                    (transformed_df['actual_value'] / transformed_df['target_value']).round(3),
                    0
                )

                # Calculate performance percentage
                transformed_df['performance_percentage'] = (
                    transformed_df['performance_ratio'] * 100
                ).round(2)

                # Performance status
                transformed_df['performance_status'] = np.where(
                    transformed_df['performance_ratio'] >= 1.0, 'ACHIEVED',
                    np.where(transformed_df['performance_ratio'] >= 0.8, 'PARTIAL', 'UNDERPERFORMED')
                )

            # Calculate variance
            transformed_df['variance'] = transformed_df['actual_value'] - transformed_df['target_value']
            transformed_df['variance_percentage'] = np.where(
                transformed_df['target_value'] > 0,
                (transformed_df['variance'] / transformed_df['target_value'] * 100).round(2),
                0
            )

            # Calculate summary metrics for result
            result.summary_metrics = self._calculate_performance_summary(transformed_df)

            step.complete(len(transformed_df))
            return transformed_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _detect_anomalies_step(self, df: pd.DataFrame, result: ETLResult) -> tuple:
        """Step 5: Detect performance anomalies"""
        step = ETLStep(
            step_type=ETLStepType.DETECT_ANOMALIES,
            name="detect_performance_anomalies",
            description="Identify anomalous performance records"
        )
        step.start()
        result.add_step(step)

        try:
            step.records_processed = len(df)

            # Define anomaly detection rules for performance data
            anomaly_rules = {
                "negative_target": {
                    "type": "range_check",
                    "column": "target_value",
                    "min": 0
                },
                "negative_actual": {
                    "type": "range_check",
                    "column": "actual_value",
                    "min": 0
                },
                "extreme_overperformance": {
                    "type": "range_check",
                    "column": "performance_ratio",
                    "min": 0,
                    "max": 5.0  # 500% performance seems excessive
                },
                "extreme_underperformance": {
                    "type": "range_check",
                    "column": "performance_ratio",
                    "min": 0.05  # Less than 5% achievement
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
        """Step 6: Output performance results"""
        step = ETLStep(
            step_type=ETLStepType.OUTPUT,
            name="output_performance_results",
            description="Save performance data and anomalies"
        )
        step.start()
        result.add_step(step)

        try:
            timestamp = datetime.now()
            base_dir = Path("uploads/temp/etl/performance_kpi")

            # Save cleaned data
            if not clean_df.empty:
                clean_filename = ETLUtils.generate_timestamped_filename(
                    "performance_kpi_cleaned", "xlsx", timestamp
                )
                clean_path = base_dir / clean_filename
                ETLUtils.save_dataframe(clean_df, clean_path, format="excel")
                result.output_files.append(clean_path)

            # Save anomalies
            if not anomalies_df.empty:
                anomaly_dir = Path("uploads/temp/anomalies/performance_kpi")
                anomaly_filename = ETLUtils.generate_timestamped_filename(
                    "performance_kpi_anomalies", "xlsx", timestamp
                )
                anomaly_path = anomaly_dir / anomaly_filename
                ETLUtils.save_dataframe(anomalies_df, anomaly_path, format="excel")
                result.anomaly_files.append(anomaly_path)

            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_org_name(self, org_name: str) -> str:
        """Clean organization name for performance data"""
        if not org_name or pd.isna(org_name):
            return ""

        org_name = str(org_name).strip()
        org_name = org_name.replace("DOT_", "")
        org_name = org_name.replace("-", " ").replace("_", " ")
        org_name = " ".join(org_name.split())

        return org_name

    def _calculate_performance_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary metrics for performance data"""
        metrics = {}

        try:
            metrics["total_records"] = len(df)
            metrics["total_organisations"] = df['org_name'].nunique() if 'org_name' in df.columns else 0
            metrics["unique_metrics"] = df['metric_type'].nunique() if 'metric_type' in df.columns else 0

            if 'performance_ratio' in df.columns:
                metrics["avg_performance_ratio"] = df['performance_ratio'].mean()
                metrics["median_performance_ratio"] = df['performance_ratio'].median()

            if 'performance_status' in df.columns:
                status_counts = df['performance_status'].value_counts().to_dict()
                metrics["achieved_count"] = status_counts.get('ACHIEVED', 0)
                metrics["partial_count"] = status_counts.get('PARTIAL', 0)
                metrics["underperformed_count"] = status_counts.get('UNDERPERFORMED', 0)

            # Best and worst performers
            if 'performance_ratio' in df.columns and 'org_name' in df.columns:
                org_performance = df.groupby('org_name')['performance_ratio'].mean().sort_values(ascending=False)
                if len(org_performance) > 0:
                    metrics["best_performer"] = org_performance.index[0]
                    metrics["worst_performer"] = org_performance.index[-1]

        except Exception as e:
            logger.error(f"Error calculating performance summary: {str(e)}")

        return metrics