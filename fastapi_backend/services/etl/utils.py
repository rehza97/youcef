"""
ETL Utilities - Common helper functions for KPI processing
Provides shared functionality across all ETL modules
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime
import re
import logging
import os

logger = logging.getLogger(__name__)


class ETLUtils:
    """Common utility functions for ETL processing"""

    @staticmethod
    def normalize_headers_to_snake_case(df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame headers to snake_case"""
        new_columns = []
        for col in df.columns:
            # Convert to string and handle special characters
            col_str = str(col).strip()

            # Replace spaces, hyphens, and other separators with underscores
            col_str = re.sub(r'[\s\-\.]+', '_', col_str)

            # Remove special characters except underscores
            col_str = re.sub(r'[^\w]', '', col_str)

            # Convert to lowercase
            col_str = col_str.lower()

            # Remove multiple consecutive underscores
            col_str = re.sub(r'_+', '_', col_str)

            # Remove leading/trailing underscores
            col_str = col_str.strip('_')

            new_columns.append(col_str)

        df.columns = new_columns
        logger.debug(f"Headers normalized: {list(df.columns)}")
        return df

    @staticmethod
    def ingest_file(file_path: Path, **kwargs) -> pd.DataFrame:
        """
        Ingest file with proper format detection and normalization
        Supports CSV and Excel files with chunked reading for large files
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        file_extension = file_path.suffix.lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file_path, **kwargs)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, **kwargs)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")

            # Normalize headers
            df = ETLUtils.normalize_headers_to_snake_case(df)

            logger.info(f"File ingested: {file_path.name} ({len(df)} rows, {len(df.columns)} columns)")
            return df

        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {str(e)}")
            raise

    @staticmethod
    def detect_anomalies(
        df: pd.DataFrame,
        rules: Dict[str, Any],
        reason_column: str = "anomaly_reason"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Detect anomalies based on rules and return clean data and anomalies

        Args:
            df: Input DataFrame
            rules: Dictionary of anomaly detection rules
            reason_column: Column name to store anomaly reasons

        Returns:
            Tuple of (clean_data, anomalies)
        """
        anomalies_list = []
        clean_indices = set(df.index)

        for rule_name, rule_config in rules.items():
            rule_type = rule_config.get('type')
            column = rule_config.get('column')

            if column not in df.columns:
                logger.warning(f"Column '{column}' not found for rule '{rule_name}'")
                continue

            try:
                if rule_type == 'null_check':
                    anomaly_indices = df[df[column].isnull()].index
                    reason = f"Null value in {column}"

                elif rule_type == 'range_check':
                    min_val = rule_config.get('min')
                    max_val = rule_config.get('max')

                    condition = pd.Series([True] * len(df), index=df.index)
                    if min_val is not None:
                        condition &= (df[column] >= min_val)
                    if max_val is not None:
                        condition &= (df[column] <= max_val)

                    anomaly_indices = df[~condition].index
                    reason = f"Value out of range in {column} (min: {min_val}, max: {max_val})"

                elif rule_type == 'pattern_check':
                    pattern = rule_config.get('pattern')
                    anomaly_indices = df[~df[column].astype(str).str.match(pattern, na=False)].index
                    reason = f"Pattern mismatch in {column}"

                elif rule_type == 'duplicate_check':
                    anomaly_indices = df[df.duplicated(subset=column, keep='first')].index
                    reason = f"Duplicate value in {column}"

                else:
                    logger.warning(f"Unknown rule type '{rule_type}' for rule '{rule_name}'")
                    continue

                # Add anomalies to list
                for idx in anomaly_indices:
                    anomaly_row = df.loc[idx].copy()
                    anomaly_row[reason_column] = reason
                    anomalies_list.append(anomaly_row)
                    clean_indices.discard(idx)

                logger.debug(f"Rule '{rule_name}' found {len(anomaly_indices)} anomalies")

            except Exception as e:
                logger.error(f"Error processing rule '{rule_name}': {str(e)}")
                continue

        # Create clean data and anomalies DataFrames
        clean_data = df.loc[list(clean_indices)] if clean_indices else pd.DataFrame()
        anomalies = pd.DataFrame(anomalies_list) if anomalies_list else pd.DataFrame()

        logger.info(f"Anomaly detection complete: {len(clean_data)} clean records, {len(anomalies)} anomalies")

        return clean_data, anomalies

    @staticmethod
    def ensure_output_directory(output_path: Path) -> Path:
        """Ensure output directory exists and return the path"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    @staticmethod
    def generate_timestamped_filename(base_name: str, extension: str, timestamp: datetime = None) -> str:
        """Generate a timestamped filename for outputs"""
        if timestamp is None:
            timestamp = datetime.now()

        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp_str}.{extension}"

    @staticmethod
    def save_dataframe(
        df: pd.DataFrame,
        output_path: Path,
        format: str = "auto",
        **kwargs
    ) -> Path:
        """
        Save DataFrame to file with format detection

        Args:
            df: DataFrame to save
            output_path: Output file path
            format: Output format ('csv', 'excel', or 'auto' for auto-detection)
            **kwargs: Additional arguments for pandas save methods
        """
        output_path = ETLUtils.ensure_output_directory(output_path)

        if format == "auto":
            format = "excel" if output_path.suffix.lower() in ['.xlsx', '.xls'] else "csv"

        try:
            if format == "csv":
                df.to_csv(output_path, index=False, **kwargs)
            elif format == "excel":
                df.to_excel(output_path, index=False, **kwargs)
            else:
                raise ValueError(f"Unsupported output format: {format}")

            logger.info(f"DataFrame saved to: {output_path} ({len(df)} rows)")
            return output_path

        except Exception as e:
            logger.error(f"Error saving DataFrame to {output_path}: {str(e)}")
            raise

    @staticmethod
    def calculate_summary_stats(df: pd.DataFrame, numeric_columns: List[str] = None) -> Dict[str, Any]:
        """Calculate summary statistics for a DataFrame"""
        if numeric_columns is None:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        stats = {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": len(numeric_columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
        }

        # Column-specific statistics
        for col in numeric_columns:
            if col in df.columns:
                stats[f"{col}_mean"] = df[col].mean()
                stats[f"{col}_median"] = df[col].median()
                stats[f"{col}_std"] = df[col].std()
                stats[f"{col}_min"] = df[col].min()
                stats[f"{col}_max"] = df[col].max()
                stats[f"{col}_null_count"] = df[col].isnull().sum()

        return stats

    @staticmethod
    def clean_numeric_column(
        df: pd.DataFrame,
        column: str,
        decimal_separator: str = ".",
        thousands_separator: str = ","
    ) -> pd.DataFrame:
        """
        Clean and convert a column to numeric format
        Handles common formatting issues in numeric data
        """
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            return df

        original_count = len(df)

        # Convert to string first
        df[column] = df[column].astype(str)

        # Replace thousands separator
        if thousands_separator and thousands_separator != decimal_separator:
            df[column] = df[column].str.replace(thousands_separator, '')

        # Replace decimal separator with standard dot if needed
        if decimal_separator != ".":
            df[column] = df[column].str.replace(decimal_separator, '.')

        # Remove any remaining non-numeric characters except dots and minus signs
        df[column] = df[column].str.replace(r'[^\d\.\-]', '', regex=True)

        # Convert to numeric, coercing errors to NaN
        df[column] = pd.to_numeric(df[column], errors='coerce')

        null_count = df[column].isnull().sum()
        logger.debug(f"Numeric conversion for '{column}': {null_count}/{original_count} values became NaN")

        return df

    @staticmethod
    def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> List[str]:
        """Validate that required columns exist in DataFrame"""
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
        return missing_columns