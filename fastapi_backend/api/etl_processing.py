from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import os

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from services.permission_service import PermissionService
from services.etl.encaissement_etl import EncaissementETL
from services.etl.subscriber_park_etl import SubscriberParkETL
from services.etl.parc_corporate_ngbss_etl import ParcCorporateNGBSSETL
from services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

etl_processing_router = APIRouter()


@etl_processing_router.post("/encaissement/process")
async def process_encaissement_etl(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process encaissement files through ETL pipeline
    Requires can_run_etl permission - handles data cleaning, anomaly detection, and KPI calculation
    """
    # RBAC: Require can_run_etl permission
    PermissionService.require_permission(current_user, db, "can_run_etl")

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per ETL process"
        )

    logger.info(
        f"ETL processing started by user {current_user.id} with {len(files)} files")

    try:
        # Save uploaded files temporarily
        temp_files = []
        for file in files:
            if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {file.filename}"
                )

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=Path(file.filename).suffix)
            temp_files.append(Path(temp_path))

            try:
                with os.fdopen(temp_fd, 'wb') as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
            except Exception as e:
                os.close(temp_fd)  # Close if writing failed
                raise e

        # Run ETL process
        etl_processor = EncaissementETL()
        etl_result = etl_processor.run_etl(temp_files)

        # Clean up temporary files
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file}: {e}")

        # Send notification
        if background_tasks:
            background_tasks.add_task(
                send_etl_completion_notification,
                current_user.id,
                etl_result.success,
                etl_result.to_summary()
            )

        # Return ETL results
        response = {
            "success": etl_result.success,
            "kpi_name": etl_result.kpi_name,
            "duration_seconds": etl_result.duration_seconds,
            "input_records": etl_result.input_records_count,
            "output_records": etl_result.output_records_count,
            "anomaly_records": etl_result.anomaly_records_count,
            "summary_metrics": etl_result.summary_metrics,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "records_processed": step.records_processed,
                    "records_output": step.records_output,
                    "warnings_count": len(step.warnings),
                    "errors_count": len(step.errors)
                }
                for step in etl_result.steps
            ],
            "output_files": [str(path) for path in etl_result.output_files],
            "anomaly_files": [str(path) for path in etl_result.anomaly_files],
            "warnings": etl_result.warnings[:10],  # Limit warnings in response
            "errors": etl_result.errors[:10],  # Limit errors in response
            "has_warnings": etl_result.has_warnings(),
            "has_errors": etl_result.has_errors()
        }

        logger.info(
            f"ETL processing completed: Success={etl_result.success}, Records={etl_result.output_records_count}")
        return response

    except Exception as e:
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except:
                pass

        logger.error(f"ETL processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"ETL processing failed: {str(e)}")


@etl_processing_router.post("/subscriber-park/process")
async def process_subscriber_park_etl(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process subscriber park CSV files through ETL pipeline
    Requires can_run_etl permission - handles telecom subscriber data cleaning and standardization
    """
    # RBAC: Require can_run_etl permission
    PermissionService.require_permission(current_user, db, "can_run_etl")

    if len(files) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 files allowed per subscriber park ETL process"
        )

    logger.info(
        f"Subscriber Park ETL processing started by user {current_user.id} with {len(files)} files")

    try:
        # Validate file formats (CSV/TSV only for subscriber data)
        temp_files = []
        for file in files:
            if not file.filename.endswith(('.csv', '.tsv', '.txt')):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format for subscriber data: {file.filename}. Use CSV/TSV format."
                )

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=Path(file.filename).suffix)
            temp_files.append(Path(temp_path))

            try:
                with os.fdopen(temp_fd, 'wb') as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
            except Exception as e:
                os.close(temp_fd)
                raise e

        # Run Subscriber Park ETL process
        etl_processor = SubscriberParkETL()
        etl_result = etl_processor.run_etl(temp_files)

        # Clean up temporary files
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file}: {e}")

        # Send notification
        if background_tasks:
            background_tasks.add_task(
                send_etl_completion_notification,
                current_user.id,
                etl_result.success,
                etl_result.to_summary()
            )

        # Return ETL results with subscriber-specific metrics
        response = {
            "success": etl_result.success,
            "kpi_name": etl_result.kpi_name,
            "duration_seconds": etl_result.duration_seconds,
            "input_records": etl_result.input_records_count,
            "output_records": etl_result.output_records_count,
            "anomaly_records": etl_result.anomaly_records_count,
            "summary_metrics": etl_result.summary_metrics,
            "subscriber_insights": {
                "total_subscribers": etl_result.summary_metrics.get("total_subscribers", 0),
                "active_subscribers": etl_result.summary_metrics.get("active_subscribers", 0),
                "unique_dots": etl_result.summary_metrics.get("unique_dots", 0),
                "monthly_revenue": etl_result.summary_metrics.get("total_monthly_revenue", 0),
                "dot_distribution": etl_result.summary_metrics.get("dot_distribution", {}),
                "service_types": etl_result.summary_metrics.get("service_type_distribution", {})
            },
            "steps": [
                {
                    "name": step.name,
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "records_processed": step.records_processed,
                    "records_output": step.records_output,
                    "warnings_count": len(step.warnings),
                    "errors_count": len(step.errors)
                }
                for step in etl_result.steps
            ],
            "output_files": [str(path) for path in etl_result.output_files],
            "anomaly_files": [str(path) for path in etl_result.anomaly_files],
            "warnings": etl_result.warnings[:10],
            "errors": etl_result.errors[:10],
            "has_warnings": etl_result.has_warnings(),
            "has_errors": etl_result.has_errors()
        }

        logger.info(
            f"Subscriber Park ETL processing completed: Success={etl_result.success}, Subscribers={etl_result.output_records_count}")
        return response

    except Exception as e:
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except:
                pass

        logger.error(f"Subscriber Park ETL processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Subscriber Park ETL processing failed: {str(e)}")


@etl_processing_router.post("/parc-corporate-ngbss/process")
async def process_parc_corporate_ngbss_etl(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process Parc Corporate NGBSS files through ETL pipeline
    Requires can_run_etl permission - handles Algérie Télécom corporate data with business rules
    """
    # RBAC: Require can_run_etl permission
    PermissionService.require_permission(current_user, db, "can_run_etl")

    if len(files) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 files allowed per Parc Corporate NGBSS ETL process"
        )

    logger.info(
        f"Parc Corporate NGBSS ETL processing started by user {current_user.id} with {len(files)} files")

    try:
        # Validate file formats (CSV/Excel only for corporate data)
        temp_files = []
        for file in files:
            if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format for Parc Corporate data: {file.filename}. Use CSV/Excel format."
                )

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=Path(file.filename).suffix)
            temp_files.append(Path(temp_path))

            try:
                with os.fdopen(temp_fd, 'wb') as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
            except Exception as e:
                os.close(temp_fd)
                raise e

        # Run Parc Corporate NGBSS ETL process
        etl_processor = ParcCorporateNGBSSETL()
        etl_result = etl_processor.run_etl(temp_files)

        # Clean up temporary files
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file}: {e}")

        # Send notification
        if background_tasks:
            background_tasks.add_task(
                send_etl_completion_notification,
                current_user.id,
                etl_result.success,
                etl_result.to_summary()
            )

        # Return ETL results with Parc Corporate specific insights
        response = {
            "success": etl_result.success,
            "kpi_name": etl_result.kpi_name,
            "duration_seconds": etl_result.duration_seconds,
            "input_records": etl_result.input_records_count,
            "output_records": etl_result.output_records_count,
            "anomaly_records": etl_result.anomaly_records_count,
            "summary_metrics": etl_result.summary_metrics,
            "business_insights": {
                "overview": etl_result.summary_metrics.get("overview", {}),
                "by_dot": etl_result.summary_metrics.get("by_dot", {}),
                "by_telecom_type": etl_result.summary_metrics.get("by_telecom_type", {}),
                "by_customer_l2": etl_result.summary_metrics.get("by_customer_l2", {}),
                "by_customer_l3": etl_result.summary_metrics.get("by_customer_l3", {}),
                "data_filters_applied": [
                    "Customer L3 categories 5, 57 removed",
                    "Predeactivated subscribers removed",
                    "Supplementary offers removed",
                    "Moohtarif and Solutions Hébergements removed"
                ],
                "dot_mappings_applied": [
                    "2B|Centre Algérie Télécom HASSI MESSAOUD → OUARGLA",
                    "99|Grand Compte → SIEGE"
                ]
            },
            "steps": [
                {
                    "name": step.name,
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "records_processed": step.records_processed,
                    "records_output": step.records_output,
                    "warnings_count": len(step.warnings),
                    "errors_count": len(step.errors),
                    "metadata": step.metadata
                }
                for step in etl_result.steps
            ],
            "output_files": [str(path) for path in etl_result.output_files],
            "anomaly_files": [str(path) for path in etl_result.anomaly_files],
            "warnings": etl_result.warnings[:10],
            "errors": etl_result.errors[:10],
            "has_warnings": etl_result.has_warnings(),
            "has_errors": etl_result.has_errors()
        }

        logger.info(
            f"Parc Corporate NGBSS ETL processing completed: Success={etl_result.success}, Records={etl_result.output_records_count}")
        return response

    except Exception as e:
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except:
                pass

        logger.error(f"Parc Corporate NGBSS ETL processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Parc Corporate NGBSS ETL processing failed: {str(e)}")


@etl_processing_router.get("/encaissement/results/{file_path:path}")
async def download_etl_result(
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download ETL result files (Requires can_view_etl_results permission)"""
    # RBAC: Require can_view_etl_results permission
    PermissionService.require_permission(current_user, db, "can_view_etl_results")

    # Validate file path is within allowed directories
    allowed_dirs = [
        "uploads/temp/etl/",
        "uploads/temp/anomalies/"
    ]

    if not any(file_path.startswith(dir) for dir in allowed_dirs):
        raise HTTPException(
            status_code=403,
            detail="Access denied: File not in allowed directory"
        )

    full_path = Path(file_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@etl_processing_router.get("/encaissement/history")
async def get_etl_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ETL processing history (Requires can_view_etl_results permission)"""
    # RBAC: Require can_view_etl_results permission
    PermissionService.require_permission(current_user, db, "can_view_etl_results")

    # In a real implementation, this would query a database table
    # For now, return a placeholder response
    return {
        "message": "ETL history endpoint - would return processing history from database",
        "limit": limit,
        "total_processes": 0,
        "processes": []
    }


@etl_processing_router.get("/parc-corporate-ngbss/views/{result_file:path}")
async def get_parc_corporate_data_views(
    result_file: str,
    # overview, by_dot, by_telecom_type, by_customer_l2, by_customer_l3, preview_data
    view_type: str = "overview",
    dot_filter: str = None,
    actel_filter: str = None,
    subscriber_filter: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get different views of processed Parc Corporate NGBSS data with filtering
    Supports: overview, by_dot, by_telecom_type, by_customer_l2, by_customer_l3, preview_data
    """
    # RBAC: Require can_view_etl_results permission
    PermissionService.require_permission(current_user, db, "can_view_etl_results")

    # Validate file path
    allowed_dirs = ["uploads/temp/etl/parc_corporate_ngbss/"]

    if not any(result_file.startswith(dir) for dir in allowed_dirs):
        raise HTTPException(
            status_code=403,
            detail="Access denied: File not in allowed directory"
        )

    file_path = Path(result_file)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    try:
        # Read processed data
        import pandas as pd

        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        logger.info(f"Loaded {len(df)} records from {file_path.name}")

        # Apply filters
        filtered_df = df.copy()

        if dot_filter and 'dot' in filtered_df.columns:
            if dot_filter.lower() != 'all':
                filtered_df = filtered_df[
                    filtered_df['dot'].str.contains(
                        dot_filter, case=False, na=False)
                ]

        if actel_filter and 'actel_code' in filtered_df.columns:
            if actel_filter.lower() != 'all':
                filtered_df = filtered_df[
                    filtered_df['actel_code'].str.contains(
                        actel_filter, case=False, na=False)
                ]

        if subscriber_filter and 'subscriber_status' in filtered_df.columns:
            if subscriber_filter.lower() != 'all':
                filtered_df = filtered_df[
                    filtered_df['subscriber_status'].str.contains(
                        subscriber_filter, case=False, na=False)
                ]

        # Generate requested view
        if view_type == "overview":
            result = {
                "view_type": "overview",
                "total_records": len(filtered_df),
                "unique_dots": filtered_df['dot'].nunique() if 'dot' in filtered_df.columns else 0,
                "unique_actel_codes": filtered_df['actel_code'].nunique() if 'actel_code' in filtered_df.columns else 0,
                "unique_customer_l2": filtered_df['code_customer_l2'].nunique() if 'code_customer_l2' in filtered_df.columns else 0,
                "unique_customer_l3": filtered_df['code_customer_l3'].nunique() if 'code_customer_l3' in filtered_df.columns else 0,
                "status_distribution": filtered_df['subscriber_status'].value_counts().to_dict() if 'subscriber_status' in filtered_df.columns else {},
                "telecom_type_distribution": filtered_df['telecom_type'].value_counts().to_dict() if 'telecom_type' in filtered_df.columns else {},
                "filters_applied": {
                    "dot": dot_filter,
                    "actel": actel_filter,
                    "subscriber": subscriber_filter
                }
            }

        elif view_type == "by_dot":
            if 'dot' in filtered_df.columns:
                dot_stats = filtered_df.groupby('dot').agg({
                    'dot': 'count',
                    'code_customer_l2': lambda x: x.nunique() if 'code_customer_l2' in filtered_df.columns else 0,
                    'code_customer_l3': lambda x: x.nunique() if 'code_customer_l3' in filtered_df.columns else 0
                }).rename(columns={'dot': 'subscriber_count'})

                # Apply pagination
                start_idx = offset
                end_idx = offset + limit
                paginated_stats = dot_stats.iloc[start_idx:end_idx]

                result = {
                    "view_type": "by_dot",
                    "total_dots": len(dot_stats),
                    "showing": len(paginated_stats),
                    "offset": offset,
                    "limit": limit,
                    "data": paginated_stats.to_dict('index'),
                    "filters_applied": {
                        "dot": dot_filter,
                        "actel": actel_filter,
                        "subscriber": subscriber_filter
                    }
                }
            else:
                result = {"error": "DOT column not found in data"}

        elif view_type == "by_telecom_type":
            if 'telecom_type' in filtered_df.columns:
                telecom_stats = filtered_df.groupby('telecom_type').agg({
                    'telecom_type': 'count',
                    'dot': lambda x: x.nunique() if 'dot' in filtered_df.columns else 0
                }).rename(columns={'telecom_type': 'subscriber_count'})

                # Apply pagination
                start_idx = offset
                end_idx = offset + limit
                paginated_stats = telecom_stats.iloc[start_idx:end_idx]

                result = {
                    "view_type": "by_telecom_type",
                    "total_types": len(telecom_stats),
                    "showing": len(paginated_stats),
                    "offset": offset,
                    "limit": limit,
                    "data": paginated_stats.to_dict('index'),
                    "filters_applied": {
                        "dot": dot_filter,
                        "actel": actel_filter,
                        "subscriber": subscriber_filter
                    }
                }
            else:
                result = {"error": "Telecom Type column not found in data"}

        elif view_type == "by_customer_l2":
            if 'code_customer_l2' in filtered_df.columns:
                l2_stats = filtered_df['code_customer_l2'].value_counts().head(
                    limit)

                result = {
                    "view_type": "by_customer_l2",
                    "total_customer_l2_codes": filtered_df['code_customer_l2'].nunique(),
                    "showing": len(l2_stats),
                    "top_codes": l2_stats.to_dict(),
                    "filters_applied": {
                        "dot": dot_filter,
                        "actel": actel_filter,
                        "subscriber": subscriber_filter
                    }
                }
            else:
                result = {"error": "Customer L2 column not found in data"}

        elif view_type == "by_customer_l3":
            if 'code_customer_l3' in filtered_df.columns:
                l3_stats = filtered_df['code_customer_l3'].value_counts().head(
                    limit)

                result = {
                    "view_type": "by_customer_l3",
                    "total_customer_l3_codes": filtered_df['code_customer_l3'].nunique(),
                    "showing": len(l3_stats),
                    "top_codes": l3_stats.to_dict(),
                    "filters_applied": {
                        "dot": dot_filter,
                        "actel": actel_filter,
                        "subscriber": subscriber_filter
                    }
                }
            else:
                result = {"error": "Customer L3 column not found in data"}

        elif view_type == "preview_data":
            # Apply pagination to preview data
            start_idx = offset
            end_idx = offset + limit
            paginated_df = filtered_df.iloc[start_idx:end_idx]

            result = {
                "view_type": "preview_data",
                "total_records": len(filtered_df),
                "showing": len(paginated_df),
                "offset": offset,
                "limit": limit,
                "columns": list(filtered_df.columns),
                "data": paginated_df.to_dict('records'),
                "filters_applied": {
                    "dot": dot_filter,
                    "actel": actel_filter,
                    "subscriber": subscriber_filter
                }
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid view_type: {view_type}. Supported: overview, by_dot, by_telecom_type, by_customer_l2, by_customer_l3, preview_data"
            )

        return result

    except Exception as e:
        logger.error(f"Error generating data view {view_type}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating data view: {str(e)}")


@etl_processing_router.post("/validate-etl-files")
async def validate_etl_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate files before ETL processing (Requires can_run_etl permission)"""
    # RBAC: Require can_run_etl permission
    PermissionService.require_permission(current_user, db, "can_run_etl")

    validation_results = []

    for file in files:
        result = {
            "filename": file.filename,
            "valid": True,
            "issues": []
        }

        # Check file extension
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            result["valid"] = False
            result["issues"].append(
                f"Unsupported file format: {Path(file.filename).suffix}")

        # Check file size - No size limit
        try:
            content = await file.read()
            file_size_mb = len(content) / 1024 / 1024

            # File size check removed - no limits

            # Reset file position
            await file.seek(0)

        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"Error reading file: {str(e)}")

        validation_results.append(result)

    valid_files = sum(1 for r in validation_results if r["valid"])
    logger.info(
        f"File validation completed: {valid_files}/{len(files)} files valid")

    return {
        "total_files": len(files),
        "valid_files": valid_files,
        "invalid_files": len(files) - valid_files,
        "results": validation_results
    }


async def send_etl_completion_notification(user_id: int, success: bool, summary: Dict[str, Any]):
    """Background task to send ETL completion notification"""
    from database.connection import SessionLocal

    db = SessionLocal()
    notification_service = NotificationService()

    try:
        title = "ETL Processing Complete" if success else "ETL Processing Failed"
        message = (
            f"Encaissement ETL processing {'completed successfully' if success else 'failed'}. "
            f"Processed {summary.get('input_records_count', 0)} records, "
            f"output {summary.get('output_records_count', 0)} clean records, "
            f"detected {summary.get('anomaly_records_count', 0)} anomalies."
        )

        await notification_service.create_notification(
            db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type="etl_completion",
            data={
                "success": success,
                "summary": summary
            }
        )

        logger.info(f"ETL completion notification sent to user {user_id}")

    except Exception as e:
        logger.error(f"Failed to send ETL notification: {str(e)}")

    finally:
        db.close()
