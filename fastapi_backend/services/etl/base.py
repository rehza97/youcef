"""
Base ETL classes and types for KPI processing
Provides common structure and result types for all ETL modules
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ETLStepType(Enum):
    """Types of ETL processing steps"""
    INGEST = "ingest"
    CLEAN = "clean"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    DETECT_ANOMALIES = "detect_anomalies"
    OUTPUT = "output"


@dataclass
class ETLStep:
    """Represents a single step in the ETL process"""
    step_type: ETLStepType
    name: str
    description: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str = "pending"  # pending, running, completed, failed
    records_processed: int = 0
    records_output: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        """Mark step as started"""
        self.start_time = datetime.utcnow()
        self.status = "running"
        logger.info(f"ETL Step started: {self.name}")

    def complete(self, records_output: int = None):
        """Mark step as completed"""
        self.end_time = datetime.utcnow()
        self.status = "completed"
        if self.start_time:
            self.duration_seconds = (
                self.end_time - self.start_time).total_seconds()
        if records_output is not None:
            self.records_output = records_output
        logger.info(
            f"ETL Step completed: {self.name} (Duration: {self.duration_seconds:.2f}s)")

    def fail(self, error_message: str):
        """Mark step as failed"""
        self.end_time = datetime.utcnow()
        self.status = "failed"
        if self.start_time:
            self.duration_seconds = (
                self.end_time - self.start_time).total_seconds()
        self.errors.append(error_message)
        logger.error(f"ETL Step failed: {self.name} - {error_message}")

    def add_warning(self, warning: str):
        """Add a warning to the step"""
        self.warnings.append(warning)
        logger.warning(f"ETL Step warning in {self.name}: {warning}")


@dataclass
class ETLResult:
    """Result of an ETL process execution"""
    kpi_name: str
    success: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Input information
    input_files: List[Path] = field(default_factory=list)
    input_records_count: int = 0

    # Processing steps
    steps: List[ETLStep] = field(default_factory=list)

    # Output information
    output_files: List[Path] = field(default_factory=list)
    output_records_count: int = 0

    # Anomaly detection
    anomaly_files: List[Path] = field(default_factory=list)
    anomaly_records_count: int = 0

    # Summary metrics
    summary_metrics: Dict[str, Any] = field(default_factory=dict)

    # Overall warnings and errors
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self):
        """Mark ETL process as completed"""
        self.end_time = datetime.utcnow()
        self.duration_seconds = (
            self.end_time - self.start_time).total_seconds()

        # Determine overall success based on steps
        failed_steps = [step for step in self.steps if step.status == "failed"]
        self.success = len(failed_steps) == 0

        # Collect all warnings and errors from steps
        for step in self.steps:
            self.warnings.extend(step.warnings)
            self.errors.extend(step.errors)

        logger.info(
            f"ETL process completed: {self.kpi_name} (Success: {self.success}, Duration: {self.duration_seconds:.2f}s)")

    def add_step(self, step: ETLStep):
        """Add a processing step to the result"""
        self.steps.append(step)

    def get_step(self, step_name: str) -> Optional[ETLStep]:
        """Get a specific step by name"""
        return next((step for step in self.steps if step.name == step_name), None)

    def get_steps_by_type(self, step_type: ETLStepType) -> List[ETLStep]:
        """Get all steps of a specific type"""
        return [step for step in self.steps if step.step_type == step_type]

    def has_errors(self) -> bool:
        """Check if there are any errors in the process"""
        return len(self.errors) > 0 or any(step.status == "failed" for step in self.steps)

    def has_warnings(self) -> bool:
        """Check if there are any warnings in the process"""
        return len(self.warnings) > 0 or any(len(step.warnings) > 0 for step in self.steps)

    def to_summary(self) -> Dict[str, Any]:
        """Generate a summary dictionary of the ETL result"""
        return {
            "kpi_name": self.kpi_name,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "input_files_count": len(self.input_files),
            "input_records_count": self.input_records_count,
            "output_files_count": len(self.output_files),
            "output_records_count": self.output_records_count,
            "anomaly_files_count": len(self.anomaly_files),
            "anomaly_records_count": self.anomaly_records_count,
            "steps_total": len(self.steps),
            "steps_completed": len([s for s in self.steps if s.status == "completed"]),
            "steps_failed": len([s for s in self.steps if s.status == "failed"]),
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "has_errors": self.has_errors(),
            "has_warnings": self.has_warnings(),
            "summary_metrics": self.summary_metrics
        }


class BaseETLProcessor:
    """Base class for all ETL processors"""

    def __init__(self):
        self.kpi_name = ""
        self.required_columns = []
        self.anomalies = []
        self.max_rows_limit = 10000  # Default limit for testing

    def limit_dataframe_rows(self, df, max_rows: int = None):
        """Limit dataframe to maximum number of rows for testing"""
        import pandas as pd

        if max_rows is None:
            max_rows = self.max_rows_limit

        if len(df) > max_rows:
            logger.info(
                f"Limiting dataframe from {len(df)} to {max_rows} rows for testing")
            return df.head(max_rows)
        return df
