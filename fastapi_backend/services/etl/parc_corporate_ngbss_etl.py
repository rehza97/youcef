"""
Parc Corporate NGBSS ETL Module
Processes Algérie Télécom corporate subscriber data with specific business rules
Handles DOT mapping, customer filtering, and anomaly detection
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import re

from .base import ETLResult, ETLStep, ETLStepType
from .utils import ETLUtils

logger = logging.getLogger(__name__)


class ParcCorporateNGBSSETL:
    """ETL processor for Parc Corporate NGBSS data"""

    def __init__(self):
        self.kpi_name = "parc_corporate_ngbss"
        self.required_columns = [
            "dot",
            "actel_code",
            "code_customer_l2",
            "code_customer_l3",
            "subscriber_status",
            "telecom_type",
            "offer_name"
        ]

        # Business rules mapping
        self.dot_actel_mapping = {
            "2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B)": "DOT OUARGLA",
            "99|Grand Compte": "DOT SIEGE"
        }

        # Categories to remove
        self.excluded_customer_l3_categories = [5, 57]
        self.excluded_subscriber_status = ["Predeactivated"]
        self.excluded_offer_types = ["Supplementary Offer"]

        # Anomaly patterns
        self.anomaly_patterns = ["Moohtarif"]
        self.excluded_offer_names = ["Moohtarif", "Solutions Hébergements"]

    def run_etl(self, input_paths: List[Path]) -> ETLResult:
        """
        Main ETL entry point for Parc Corporate NGBSS data processing

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
                raise ValueError("No Parc Corporate NGBSS data found in input files")

            result.input_records_count = len(combined_df)

            # Step 2: Clean and standardize
            cleaned_df = self._clean_step(combined_df, result)

            # Step 3: Apply business rules and relationships
            processed_df = self._apply_business_rules_step(cleaned_df, result)

            # Step 4: Filter out excluded records
            filtered_df = self._filter_step(processed_df, result)

            # Step 5: Detect anomalies
            final_df, anomalies_df = self._detect_anomalies_step(filtered_df, result)

            # Step 6: Generate views and output
            self._generate_views_step(final_df, result)

            # Step 7: Output results
            self._output_step(final_df, anomalies_df, result)

            result.output_records_count = len(final_df)
            result.anomaly_records_count = len(anomalies_df)

        except Exception as e:
            error_msg = f"Parc Corporate NGBSS ETL process failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        finally:
            result.complete()

        return result

    def _ingest_step(self, input_paths: List[Path], result: ETLResult) -> pd.DataFrame:
        """Step 1: Ingest Parc Corporate NGBSS files"""
        step = ETLStep(
            step_type=ETLStepType.INGEST,
            name="ingest_parc_corporate_files",
            description="Read and combine Parc Corporate NGBSS files"
        )
        step.start()
        result.add_step(step)

        combined_data = []

        try:
            for file_path in input_paths:
                try:
                    # Read file with appropriate encoding
                    df = ETLUtils.ingest_file(
                        file_path,
                        encoding='utf-8',
                        sep=','  # Assuming CSV format
                    )

                    # Basic column name standardization
                    df.columns = df.columns.str.lower().str.strip()

                    combined_data.append(df)
                    step.records_processed += len(df)
                    logger.info(f"Ingested Parc Corporate file {file_path.name}: {len(df)} records")

                except Exception as e:
                    error_msg = f"Error ingesting {file_path.name}: {str(e)}"
                    step.add_warning(error_msg)

            if not combined_data:
                raise ValueError("No valid Parc Corporate NGBSS files found")

            combined_df = pd.concat(combined_data, ignore_index=True)
            step.complete(len(combined_df))
            return combined_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _clean_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 2: Clean and standardize Parc Corporate data"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="clean_parc_corporate_data",
            description="Clean and standardize Parc Corporate NGBSS data"
        )
        step.start()
        result.add_step(step)

        try:
            cleaned_df = df.copy()
            step.records_processed = len(cleaned_df)

            # Standardize column names
            column_mapping = self._get_column_mapping(cleaned_df.columns)
            cleaned_df = cleaned_df.rename(columns=column_mapping)

            # Clean text fields
            text_columns = ['dot', 'actel_code', 'subscriber_status', 'telecom_type', 'offer_name']
            for col in text_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip()

            # Clean numeric codes
            numeric_code_columns = ['code_customer_l2', 'code_customer_l3']
            for col in numeric_code_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

            step.metadata["cleaning_rules_applied"] = [
                "Column name standardization",
                "Text field cleaning",
                "Numeric code conversion"
            ]

            step.complete(len(cleaned_df))
            return cleaned_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _apply_business_rules_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 3: Apply business rules and relationships"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="apply_business_rules",
            description="Apply DOT-Actel mapping and business relationships"
        )
        step.start()
        result.add_step(step)

        try:
            processed_df = df.copy()
            step.records_processed = len(processed_df)

            # Apply DOT-Actel Code mapping
            if 'actel_code' in processed_df.columns and 'dot' in processed_df.columns:
                for actel_pattern, dot_value in self.dot_actel_mapping.items():
                    mask = processed_df['actel_code'].str.contains(
                        actel_pattern, case=False, na=False, regex=False
                    )
                    processed_df.loc[mask, 'dot'] = dot_value
                    if mask.any():
                        step.add_warning(f"Mapped {mask.sum()} records: {actel_pattern} -> {dot_value}")

            step.metadata["business_rules_applied"] = [
                "DOT-Actel Code mapping",
                f"Applied {len(self.dot_actel_mapping)} mapping rules"
            ]

            step.complete(len(processed_df))
            return processed_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _filter_step(self, df: pd.DataFrame, result: ETLResult) -> pd.DataFrame:
        """Step 4: Filter out excluded records based on business rules"""
        step = ETLStep(
            step_type=ETLStepType.CLEAN,
            name="filter_excluded_records",
            description="Remove records based on business exclusion rules"
        )
        step.start()
        result.add_step(step)

        try:
            filtered_df = df.copy()
            step.records_processed = len(filtered_df)
            initial_count = len(filtered_df)

            # Filter Code Customer L3 categories (5, 57)
            if 'code_customer_l3' in filtered_df.columns:
                before_count = len(filtered_df)
                filtered_df = filtered_df[
                    ~filtered_df['code_customer_l3'].isin(self.excluded_customer_l3_categories)
                ]
                removed = before_count - len(filtered_df)
                if removed > 0:
                    step.add_warning(f"Removed {removed} records with Customer L3 categories {self.excluded_customer_l3_categories}")

            # Filter Subscriber Status (Predeactivated)
            if 'subscriber_status' in filtered_df.columns:
                before_count = len(filtered_df)
                filtered_df = filtered_df[
                    ~filtered_df['subscriber_status'].isin(self.excluded_subscriber_status)
                ]
                removed = before_count - len(filtered_df)
                if removed > 0:
                    step.add_warning(f"Removed {removed} records with status {self.excluded_subscriber_status}")

            # Filter Offer Type (Supplementary Offer)
            if 'offer_type' in filtered_df.columns:
                before_count = len(filtered_df)
                filtered_df = filtered_df[
                    ~filtered_df['offer_type'].isin(self.excluded_offer_types)
                ]
                removed = before_count - len(filtered_df)
                if removed > 0:
                    step.add_warning(f"Removed {removed} records with offer type {self.excluded_offer_types}")

            # Filter Offer Names containing excluded patterns
            if 'offer_name' in filtered_df.columns:
                before_count = len(filtered_df)
                for pattern in self.excluded_offer_names:
                    mask = filtered_df['offer_name'].str.contains(pattern, case=False, na=False)
                    removed_by_pattern = mask.sum()
                    filtered_df = filtered_df[~mask]
                    if removed_by_pattern > 0:
                        step.add_warning(f"Removed {removed_by_pattern} records containing '{pattern}' in offer name")

            total_removed = initial_count - len(filtered_df)
            step.metadata["filtering_summary"] = {
                "initial_records": initial_count,
                "final_records": len(filtered_df),
                "total_removed": total_removed,
                "removal_percentage": round((total_removed / initial_count) * 100, 2) if initial_count > 0 else 0
            }

            step.complete(len(filtered_df))
            return filtered_df

        except Exception as e:
            step.fail(str(e))
            raise

    def _detect_anomalies_step(self, df: pd.DataFrame, result: ETLResult) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Step 5: Detect anomalies in Parc Corporate data"""
        step = ETLStep(
            step_type=ETLStepType.DETECT_ANOMALIES,
            name="detect_parc_corporate_anomalies",
            description="Identify anomalous Parc Corporate records"
        )
        step.start()
        result.add_step(step)

        try:
            step.records_processed = len(df)
            anomalies_list = []

            # Check for Moohtarif patterns in offer names (business anomaly)
            if 'offer_name' in df.columns:
                for pattern in self.anomaly_patterns:
                    anomaly_mask = df['offer_name'].str.contains(pattern, case=False, na=False)
                    anomaly_records = df[anomaly_mask].copy()

                    if not anomaly_records.empty:
                        anomaly_records['anomaly_type'] = f'Offer name contains {pattern}'
                        anomaly_records['anomaly_description'] = f'Business rule violation: Offer name contains "{pattern}"'
                        anomalies_list.append(anomaly_records)
                        step.add_warning(f"Found {len(anomaly_records)} records with '{pattern}' pattern")

            # Standard anomaly detection rules
            anomaly_rules = {
                "missing_dot": {
                    "type": "null_check",
                    "column": "dot"
                },
                "missing_actel_code": {
                    "type": "null_check",
                    "column": "actel_code"
                },
                "invalid_customer_l2": {
                    "type": "range_check",
                    "column": "code_customer_l2",
                    "min": 1,
                    "max": 999999
                },
                "invalid_customer_l3": {
                    "type": "range_check",
                    "column": "code_customer_l3",
                    "min": 1,
                    "max": 999999
                }
            }

            clean_data, system_anomalies = ETLUtils.detect_anomalies(df, anomaly_rules)

            # Combine business anomalies with system anomalies
            if anomalies_list:
                business_anomalies = pd.concat(anomalies_list, ignore_index=True)
                if not system_anomalies.empty:
                    all_anomalies = pd.concat([business_anomalies, system_anomalies], ignore_index=True)
                else:
                    all_anomalies = business_anomalies

                # Remove business anomalies from clean data
                anomaly_indices = business_anomalies.index
                clean_data = clean_data.drop(anomaly_indices, errors='ignore').reset_index(drop=True)
            else:
                all_anomalies = system_anomalies

            step.metadata["anomaly_detection"] = {
                "business_anomalies": len(anomalies_list),
                "system_anomalies": len(system_anomalies),
                "total_anomalies": len(all_anomalies),
                "clean_records": len(clean_data)
            }

            step.complete(len(clean_data))
            return clean_data, all_anomalies

        except Exception as e:
            step.fail(str(e))
            raise

    def _generate_views_step(self, df: pd.DataFrame, result: ETLResult) -> None:
        """Step 6: Generate different views of the data"""
        step = ETLStep(
            step_type=ETLStepType.TRANSFORM,
            name="generate_data_views",
            description="Generate overview, DOT, telecom type, and customer views"
        )
        step.start()
        result.add_step(step)

        try:
            views = {}

            # Overview
            views["overview"] = self._generate_overview(df)

            # By DOT
            if 'dot' in df.columns:
                views["by_dot"] = df.groupby('dot').agg({
                    'dot': 'count',
                    'code_customer_l2': 'nunique',
                    'code_customer_l3': 'nunique'
                }).rename(columns={'dot': 'subscriber_count'}).to_dict('index')

            # By Telecom Type
            if 'telecom_type' in df.columns:
                views["by_telecom_type"] = df.groupby('telecom_type').agg({
                    'telecom_type': 'count',
                    'dot': 'nunique'
                }).rename(columns={'telecom_type': 'subscriber_count'}).to_dict('index')

            # By Customer L2
            if 'code_customer_l2' in df.columns:
                views["by_customer_l2"] = df.groupby('code_customer_l2').size().to_dict()

            # By Customer L3
            if 'code_customer_l3' in df.columns:
                views["by_customer_l3"] = df.groupby('code_customer_l3').size().to_dict()

            # Preview data (first 100 records)
            views["preview_data"] = df.head(100).to_dict('records')

            result.summary_metrics.update(views)

            step.metadata["views_generated"] = list(views.keys())
            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    def _output_step(self, clean_df: pd.DataFrame, anomalies_df: pd.DataFrame, result: ETLResult) -> None:
        """Step 7: Output Parc Corporate NGBSS results"""
        step = ETLStep(
            step_type=ETLStepType.OUTPUT,
            name="output_parc_corporate_results",
            description="Save processed Parc Corporate data and anomalies"
        )
        step.start()
        result.add_step(step)

        try:
            timestamp = datetime.now()
            base_dir = Path("uploads/temp/etl/parc_corporate_ngbss")

            # Save cleaned data
            if not clean_df.empty:
                clean_filename = ETLUtils.generate_timestamped_filename(
                    "parc_corporate_ngbss_cleaned", "xlsx", timestamp
                )
                clean_path = base_dir / clean_filename
                ETLUtils.save_dataframe(clean_df, clean_path, format="excel")
                result.output_files.append(clean_path)

            # Save anomalies
            if not anomalies_df.empty:
                anomaly_dir = Path("uploads/temp/anomalies/parc_corporate_ngbss")
                anomaly_filename = ETLUtils.generate_timestamped_filename(
                    "parc_corporate_ngbss_anomalies", "xlsx", timestamp
                )
                anomaly_path = anomaly_dir / anomaly_filename
                ETLUtils.save_dataframe(anomalies_df, anomaly_path, format="excel")
                result.anomaly_files.append(anomaly_path)

            step.complete()

        except Exception as e:
            step.fail(str(e))
            raise

    def _get_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """Map various column name formats to standard names"""
        mapping = {}
        for col in columns:
            col_lower = col.lower().strip()

            # Map common variations to standard names
            if 'dot' in col_lower:
                mapping[col] = 'dot'
            elif 'actel' in col_lower and 'code' in col_lower:
                mapping[col] = 'actel_code'
            elif 'customer' in col_lower and 'l2' in col_lower:
                mapping[col] = 'code_customer_l2'
            elif 'customer' in col_lower and 'l3' in col_lower:
                mapping[col] = 'code_customer_l3'
            elif 'subscriber' in col_lower and 'status' in col_lower:
                mapping[col] = 'subscriber_status'
            elif 'telecom' in col_lower and 'type' in col_lower:
                mapping[col] = 'telecom_type'
            elif 'offer' in col_lower and 'name' in col_lower:
                mapping[col] = 'offer_name'
            elif 'offer' in col_lower and 'type' in col_lower:
                mapping[col] = 'offer_type'

        return mapping

    def _generate_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate overview statistics"""
        overview = {
            "total_records": len(df),
            "unique_dots": df['dot'].nunique() if 'dot' in df.columns else 0,
            "unique_actel_codes": df['actel_code'].nunique() if 'actel_code' in df.columns else 0,
            "unique_customer_l2": df['code_customer_l2'].nunique() if 'code_customer_l2' in df.columns else 0,
            "unique_customer_l3": df['code_customer_l3'].nunique() if 'code_customer_l3' in df.columns else 0,
            "processing_date": datetime.now().isoformat()
        }

        # Add status distribution if available
        if 'subscriber_status' in df.columns:
            overview["status_distribution"] = df['subscriber_status'].value_counts().to_dict()

        # Add telecom type distribution if available
        if 'telecom_type' in df.columns:
            overview["telecom_type_distribution"] = df['telecom_type'].value_counts().to_dict()

        return overview