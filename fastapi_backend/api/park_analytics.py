"""
Park Analytics API - Real data endpoints for dashboard visualizations
Based on Parc Corporate NGBSS data with DOT-based permissions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import logging
import pandas as pd
import io
import zipfile

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.park import Park
from models.park_2b import Park2B
from models.dot import DOT
from models.user_module_dot import MODULE_PARC_CORPORATE_NGBSS
from services.dot_service import DOTService
from services.permission_service import PermissionService
from services.kpi_cache_service import kpi_cache_service
from services.processing_websocket import processing_ws_manager
from services.park_anomaly_rules import apply_default_anomaly_exclusion, apply_anomaly_only
import asyncio
import uuid
import threading
import tempfile
import os

logger = logging.getLogger(__name__)

park_analytics_router = APIRouter()

# Store active export tasks
export_tasks = {}

# French number format for Parc exports (space thousands, comma decimal)
PARC_NUMERIC_COLS = ["Rental Fees"]


def _format_french_number(x):
    """Format number with French formatting: space thousands, comma decimal."""
    if pd.isna(x) or not isinstance(x, (int, float)):
        return x
    formatted = f"{x:,.2f}"
    if "." in formatted:
        int_part, dec_part = formatted.rsplit(".", 1)
        int_part_clean = int_part.replace(",", "")
        int_part_formatted = ""
        for i, digit in enumerate(reversed(int_part_clean)):
            if i > 0 and i % 3 == 0:
                int_part_formatted = " " + int_part_formatted
            int_part_formatted = digit + int_part_formatted
        return int_part_formatted + "," + dec_part
    int_part_clean = formatted.replace(",", "")
    int_part_formatted = ""
    for i, digit in enumerate(reversed(int_part_clean)):
        if i > 0 and i % 3 == 0:
            int_part_formatted = " " + int_part_formatted
        int_part_formatted = digit + int_part_formatted
    return int_part_formatted + ",00"


def _apply_french_number_format_df(df, numeric_cols):
    """Return a copy of df with numeric columns formatted as French (space thousands, comma decimal)."""
    df_f = df.copy()
    for col in numeric_cols:
        if col in df_f.columns:
            df_f[col] = df_f[col].apply(_format_french_number)
    return df_f


def _write_parc_excel_french(df, buffer, sheet_name, numeric_cols=PARC_NUMERIC_COLS):
    """Write df to buffer as Excel with French number format (# ##0,00)."""
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        french_number_format = "# ##0,00"
        for col_idx, col_name in enumerate(df.columns, start=1):
            if col_name in numeric_cols:
                for row_idx in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    if cell.value is not None and cell.value != "":
                        cell.number_format = french_number_format


def _write_parc_csv_french(df, buffer, numeric_cols=PARC_NUMERIC_COLS):
    """Write df to buffer as CSV with French number format and semicolon separator."""
    df_f = _apply_french_number_format_df(df, numeric_cols)
    df_f.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")


def _run_export_background(task_id: str, export_params: dict):
    """Background worker for export with progress updates"""
    from database.connection import SessionLocal

    db = SessionLocal()

    try:
        # Send initial progress
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "started",
            "progress": 0,
            "message": "Starting export..."
        }))

        export_tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "file_path": None,
            "filename": None,
            "error": None,
            "start_time": datetime.utcnow().isoformat()
        }

        # Extract parameters
        format = export_params["format"]
        export_type = export_params["export_type"]
        user_id = export_params["user_id"]

        # Apply filters and build query
        query = db.query(Park)
        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id, module=MODULE_PARC_CORPORATE_NGBSS)

        if accessible_dots:
            query = query.filter(Park.dot_id.in_(accessible_dots))
        else:
            raise Exception("No accessible data")

        # Apply all filters
        query = apply_filters_to_query(
            query=query,
            dot_ids=export_params.get("dot_ids"),
            actel_codes=export_params.get("actel_codes"),
            subscriber_statuses=export_params.get("subscriber_statuses"),
            telecom_types=export_params.get("telecom_types"),
            offer_names=export_params.get("offer_names"),
            offer_types=export_params.get("offer_types"),
            customer_l2_codes=export_params.get("customer_l2_codes"),
            customer_l3_codes=export_params.get("customer_l3_codes"),
            search=export_params.get("search"),
            date_from=export_params.get("date_from"),
            date_to=export_params.get("date_to"),
            include_exclusion_2b=export_params.get("include_exclusion_2b", False)
        )

        # Progress: Query built
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "processing",
            "progress": 10,
            "message": "Fetching data..."
        }))
        export_tasks[task_id]["progress"] = 10

        # Helper to convert parks to records with progress
        def parks_to_records_with_progress(parks_list, start_progress, end_progress, label=""):
            records = []
            total = len(parks_list)
            for idx, park in enumerate(parks_list):
                if idx % 1000 == 0:
                    progress = start_progress + ((idx / total) * (end_progress - start_progress))
                    asyncio.run(processing_ws_manager.send_task_update(task_id, {
                        "status": "processing",
                        "progress": int(progress),
                        "message": f"{label}Processing record {idx:,} of {total:,}..."
                    }))
                    export_tasks[task_id]["progress"] = int(progress)

                try:
                    records.append({
                        "DOT ID": park.dot_id or "",
                        "DOT Name": park.dot.name if park.dot else "",
                        "Customer Code": park.customer_code or "",
                        "Service Number": park.service_number or "",
                        "Related Service Number": park.related_service_number or "",
                        "Customer Name": park.customer_full_name or "",
                        "Username": park.username or "",
                        "Actel Code": park.actel_code or "",
                        "Subscriber Status": park.subscriber_status or "",
                        "Telecom Type": park.telecom_type or "",
                        "Offer Name": park.offer_name or "",
                        "Offer Type": park.offer_type or "",
                        "Rental Fees": float(park.rental_fees) if park.rental_fees else 0.0,
                        "Customer L1 Code": park.customer_l1_code or "",
                        "Customer L1 Description": park.customer_l1_description or "",
                        "Customer L2 Code": park.customer_l2_code or "",
                        "Customer L2 Description": park.customer_l2_description or "",
                        "Customer L3 Code": park.customer_l3_code or "",
                        "Customer L3 Description": park.customer_l3_description or "",
                        "CSR Name": park.csr_name or "",
                        "Department Name": park.department_name or "",
                        "State": park.state or "",
                        "Province": park.province or "",
                        "Area": park.area or "",
                        "District": park.district or "",
                        "City": park.city or "",
                        "Town": park.town or "",
                        "Postal Code": park.postal_code or "",
                        "Street": park.street or "",
                        "Street Number": park.street_number or "",
                        "Building No": park.building_no or "",
                        "Unit": park.unit or "",
                        "Floor": park.floor or "",
                        "House No": park.house_no or "",
                        "Grid": park.grid or "",
                        "Additional Address Info": park.additional_address_info or "",
                        "Contact Number": park.contact_number or "",
                        "ICCID": park.iccid or "",
                        "IMSI": park.imsi or "",
                        "Status Date": park.status_date.isoformat() if park.status_date else "",
                        "Creation Date": park.creation_date.isoformat() if park.creation_date else "",
                        "Active Date": park.active_date.isoformat() if park.active_date else "",
                        "Expiry Date": park.expiry_date.isoformat() if park.expiry_date else "",
                        "Extraction Date": park.extraction_date.isoformat() if park.extraction_date else "",
                        "Created At": park.created_at.isoformat() if park.created_at else "",
                        "Updated At": park.updated_at.isoformat() if park.updated_at else ""
                    })
                except Exception as e:
                    logger.error(f"Error processing park record {park.id}: {e}")
                    continue
            return records

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # Handle "all" export type (ZIP with 3 files: normal, anomalies, 2B)
        if export_type == "all":
            # Normal parks (exclude anomalies) - query already has anomaly filter from apply_filters_to_query
            normal_parks = query.all()

            if len(normal_parks) == 0:
                raise Exception("No data found with applied filters")

            # Get anomaly data - query for anomalies only (bypass anomaly exclusion)
            anomaly_query = db.query(Park)
            if accessible_dots:
                anomaly_query = anomaly_query.filter(Park.dot_id.in_(accessible_dots))
            
            # Apply filters WITHOUT anomaly exclusion
            anomaly_query = apply_filters_to_query(
                query=anomaly_query,
                dot_ids=export_params.get("dot_ids"),
                actel_codes=export_params.get("actel_codes"),
                subscriber_statuses=export_params.get("subscriber_statuses"),
                telecom_types=export_params.get("telecom_types"),
                offer_names=export_params.get("offer_names"),
                offer_types=export_params.get("offer_types"),
                customer_l2_codes=export_params.get("customer_l2_codes"),
                customer_l3_codes=export_params.get("customer_l3_codes"),
                search=export_params.get("search"),
                date_from=export_params.get("date_from"),
                date_to=export_params.get("date_to"),
                include_exclusion_2b=False,
                exclude_anomalies=False  # Don't exclude anomalies
            )
            
            # Filter to get ONLY anomalies (flag + safety-net rules)
            anomaly_query = apply_anomaly_only(anomaly_query, Park)
            anomaly_parks = anomaly_query.all()

            # Process normal data (10-50%)
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 20,
                "message": f"Processing {len(normal_parks):,} normal records..."
            }))

            normal_records = parks_to_records_with_progress(normal_parks, 20, 50, "[Normal] ")
            normal_df = pd.DataFrame(normal_records)

            # Process anomaly data (50-65%)
            if anomaly_parks:
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 50,
                    "message": f"Processing {len(anomaly_parks):,} anomaly records..."
                }))
                anomaly_records = parks_to_records_with_progress(anomaly_parks, 50, 65, "[Anomaly] ")
                anomaly_df = pd.DataFrame(anomaly_records)
            else:
                anomaly_df = pd.DataFrame()

            # Process 2B data for Facturation Groupée (65-80%)
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 65,
                "message": "Processing Facturation Groupée (2B records)..."
            }))

            # Query parks_2b table with same filters (with eager loading for dot relationship)
            from sqlalchemy.orm import joinedload
            parks_2b_query = db.query(Park2B).options(joinedload(Park2B.dot))
            if accessible_dots:
                parks_2b_query = parks_2b_query.filter(Park2B.dot_id.in_(accessible_dots))

            # Apply same filters to parks_2b
            parks_2b_query = apply_filters_to_query(
                query=parks_2b_query,
                dot_ids=export_params.get("dot_ids"),
                actel_codes=export_params.get("actel_codes"),
                subscriber_statuses=export_params.get("subscriber_statuses"),
                telecom_types=export_params.get("telecom_types"),
                offer_names=export_params.get("offer_names"),
                offer_types=export_params.get("offer_types"),
                customer_l2_codes=export_params.get("customer_l2_codes"),
                customer_l3_codes=export_params.get("customer_l3_codes"),
                search=export_params.get("search"),
                date_from=export_params.get("date_from"),
                date_to=export_params.get("date_to"),
                include_exclusion_2b=False
            )

            # Use pandas read_sql for faster processing of large 2B dataset
            logger.info("🔄 Using optimized pandas query for 2B records...")
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 70,
                "message": "Loading Facturation Groupée data (optimized)..."
            }))

            # Get the SQL query string and execute with pandas for better performance
            from sqlalchemy import select
            parks_2b_count = parks_2b_query.count()
            logger.info(f"📊 Found {parks_2b_count:,} 2B records to export")

            if parks_2b_count > 0:
                # For large datasets, use pandas read_sql which is much faster
                facturation_df = pd.read_sql(
                    parks_2b_query.statement,
                    db.bind
                )

                # Add DOT names by joining (pandas is faster for this)
                dot_names = pd.read_sql(
                    "SELECT id, name FROM dots",
                    db.bind
                )
                facturation_df = facturation_df.merge(
                    dot_names,
                    left_on='dot_id',
                    right_on='id',
                    how='left',
                    suffixes=('', '_dot')
                )

                # Rename columns to match export format
                facturation_df = facturation_df.rename(columns={
                    'name': 'DOT Name',
                    'dot_id': 'DOT ID',
                    'customer_code': 'Customer Code',
                    'service_number': 'Service Number',
                    'related_service_number': 'Related Service Number',
                    'customer_full_name': 'Customer Name',
                    'username': 'Username',
                    'actel_code': 'Actel Code',
                    'subscriber_status': 'Subscriber Status',
                    'telecom_type': 'Telecom Type',
                    'offer_name': 'Offer Name',
                    'offer_type': 'Offer Type',
                    'rental_fees': 'Rental Fees',
                    'customer_l1_code': 'Customer L1 Code',
                    'customer_l1_description': 'Customer L1 Description',
                    'customer_l2_code': 'Customer L2 Code',
                    'customer_l2_description': 'Customer L2 Description',
                    'customer_l3_code': 'Customer L3 Code',
                    'customer_l3_description': 'Customer L3 Description',
                    'csr_name': 'CSR Name',
                    'department_name': 'Department Name',
                    'state': 'State',
                    'province': 'Province',
                    'area': 'Area',
                    'district': 'District',
                    'city': 'City',
                    'town': 'Town',
                    'postal_code': 'Postal Code',
                    'street': 'Street',
                    'street_number': 'Street Number',
                    'building_no': 'Building No',
                    'unit': 'Unit',
                    'floor': 'Floor',
                    'house_no': 'House No',
                    'grid': 'Grid',
                    'additional_address_info': 'Additional Address Info',
                    'iccid': 'ICCID',
                    'imsi': 'IMSI',
                    'contact_number': 'Contact Number',
                    'expiry_date': 'Expiry Date',
                    'status_date': 'Status Date',
                    'creation_date': 'Creation Date',
                    'active_date': 'Active Date'
                })

                logger.info(f"✅ Loaded {len(facturation_df):,} 2B records using pandas")
            else:
                facturation_df = pd.DataFrame()
                logger.info("ℹ️ No 2B records found")

            # Create ZIP file (80-95%)
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 80,
                "message": "Creating ZIP file..."
            }))
            logger.info("📦 Starting ZIP file creation...")

            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                file_ext = "xlsx" if format == "excel" else "csv"
                normal_filename = f"Parc_Corporate_NGBSS_{timestamp}.{file_ext}"

                # Write normal file (80-85%)
                logger.info(f"📝 Writing normal data ({len(normal_parks):,} records) to {file_ext}...")
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 82,
                    "message": f"Writing normal data ({len(normal_parks):,} records)..."
                }))
                normal_buffer = io.BytesIO()
                if format == "excel":
                    _write_parc_excel_french(normal_df, normal_buffer, "Parc Data")
                else:
                    _write_parc_csv_french(normal_df, normal_buffer)
                zip_file.writestr(normal_filename, normal_buffer.getvalue())
                logger.info(f"✅ Normal file written")

                # Write anomaly file (85-88%)
                logger.info(f"📝 Writing anomaly data ({len(anomaly_parks):,} records)...")
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 85,
                    "message": f"Writing anomalies ({len(anomaly_parks):,} records)..."
                }))
                if len(anomaly_parks) > 0:
                    anomaly_filename = f"Anomalie_Parc_NGBSS_{timestamp}.{file_ext}"
                    anomaly_buffer = io.BytesIO()
                    if format == "excel":
                        _write_parc_excel_french(anomaly_df, anomaly_buffer, "Parc Data")
                    else:
                        _write_parc_csv_french(anomaly_df, anomaly_buffer)
                    zip_file.writestr(anomaly_filename, anomaly_buffer.getvalue())
                    logger.info(f"✅ Anomaly file written")
                else:
                    zip_file.writestr("NO_ANOMALIES_FOUND.txt", "No anomalies found with the applied filters.")

                # Write Facturation Groupée file (88-95%)
                facturation_count = len(facturation_df)
                logger.info(f"📝 Writing Facturation Groupée ({facturation_count:,} 2B records) to {file_ext}...")
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 88,
                    "message": f"Writing Facturation Groupée ({facturation_count:,} 2B records)... This may take a few minutes."
                }))
                if facturation_count > 0:
                    facturation_filename = f"Facturation_Groupee_2B_{timestamp}.{file_ext}"
                    facturation_buffer = io.BytesIO()
                    if format == "excel":
                        # Optimize for large 2B datasets
                        if facturation_count > 100000:
                            logger.info(f"⏳ Large 2B dataset ({facturation_count:,} records). Optimizing before Excel write...")
                            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                                "status": "processing",
                                "progress": 90,
                                "message": f"Preparing {facturation_count:,} 2B records for Excel... (this may take several minutes)"
                            }))
                            # Optimize DataFrame
                            for col in facturation_df.select_dtypes(include=['object']).columns:
                                facturation_df[col] = facturation_df[col].astype(str)
                        
                        logger.info("⏳ Converting 2B data to Excel format...")
                        asyncio.run(processing_ws_manager.send_task_update(task_id, {
                            "status": "processing",
                            "progress": 91,
                            "message": f"Writing {facturation_count:,} 2B records to Excel... Please wait."
                        }))
                        _write_parc_excel_french(
                            facturation_df, facturation_buffer, "Facturation 2B"
                        )
                        logger.info("✅ Excel conversion complete")
                    else:
                        # CSV - French format, semicolon separator
                        _write_parc_csv_french(facturation_df, facturation_buffer)
                    logger.info("💾 Writing to ZIP...")
                    zip_file.writestr(facturation_filename, facturation_buffer.getvalue())
                    logger.info(f"✅ Facturation Groupée file written")
                else:
                    zip_file.writestr("NO_2B_RECORDS_FOUND.txt", "No 2B records found with the applied filters.")

            filename = f"Parc_Export_{timestamp}.zip"
            export_tasks[task_id].update({
                "file_path": temp_file.name,
                "filename": filename,
                "normal_count": len(normal_parks),
                "anomaly_count": len(anomaly_parks),
                "facturation_2b_count": len(facturation_df)
            })

        else:
            # Single file export
            if export_type == "2b":
                # Export 2B records (Facturation Groupée) - use fast pandas read_sql method
                from sqlalchemy.orm import joinedload
                parks_2b_query = db.query(Park2B).options(joinedload(Park2B.dot))
                if accessible_dots:
                    parks_2b_query = parks_2b_query.filter(Park2B.dot_id.in_(accessible_dots))

                # Apply same filters to parks_2b
                parks_2b_query = apply_filters_to_query(
                    query=parks_2b_query,
                    dot_ids=export_params.get("dot_ids"),
                    actel_codes=export_params.get("actel_codes"),
                    subscriber_statuses=export_params.get("subscriber_statuses"),
                    telecom_types=export_params.get("telecom_types"),
                    offer_names=export_params.get("offer_names"),
                    offer_types=export_params.get("offer_types"),
                    customer_l2_codes=export_params.get("customer_l2_codes"),
                    customer_l3_codes=export_params.get("customer_l3_codes"),
                    search=export_params.get("search"),
                    date_from=export_params.get("date_from"),
                    date_to=export_params.get("date_to"),
                    include_exclusion_2b=False
                )

                parks_2b_count = parks_2b_query.count()
                if parks_2b_count == 0:
                    raise Exception("No 2B records found with applied filters")

                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 40,
                    "message": f"Loading {parks_2b_count:,} 2B records (optimized method)..."
                }))

                # Use pandas read_sql for MUCH faster processing (same as "all" export)
                logger.info(f"🔄 Using optimized pandas query for {parks_2b_count:,} 2B records...")
                df = pd.read_sql(parks_2b_query.statement, db.bind)

                # Add DOT names by joining (pandas is faster for this)
                dot_names = pd.read_sql("SELECT id, name FROM dots", db.bind)
                df = df.merge(dot_names, left_on='dot_id', right_on='id', how='left', suffixes=('', '_dot'))

                # Rename columns to match export format (same as "all" export)
                df = df.rename(columns={
                    'name': 'DOT Name',
                    'dot_id': 'DOT ID',
                    'customer_code': 'Customer Code',
                    'service_number': 'Service Number',
                    'related_service_number': 'Related Service Number',
                    'customer_full_name': 'Customer Name',
                    'username': 'Username',
                    'actel_code': 'Actel Code',
                    'subscriber_status': 'Subscriber Status',
                    'telecom_type': 'Telecom Type',
                    'offer_name': 'Offer Name',
                    'offer_type': 'Offer Type',
                    'rental_fees': 'Rental Fees',
                    'customer_l1_code': 'Customer L1 Code',
                    'customer_l1_description': 'Customer L1 Description',
                    'customer_l2_code': 'Customer L2 Code',
                    'customer_l2_description': 'Customer L2 Description',
                    'customer_l3_code': 'Customer L3 Code',
                    'customer_l3_description': 'Customer L3 Description',
                    'csr_name': 'CSR Name',
                    'department_name': 'Department Name',
                    'state': 'State',
                    'province': 'Province',
                    'area': 'Area',
                    'district': 'District',
                    'city': 'City',
                    'town': 'Town',
                    'postal_code': 'Postal Code',
                    'street': 'Street',
                    'street_number': 'Street Number',
                    'building_no': 'Building No',
                    'unit': 'Unit',
                    'floor': 'Floor',
                    'house_no': 'House No',
                    'grid': 'Grid',
                    'additional_address_info': 'Additional Address Info',
                    'iccid': 'ICCID',
                    'imsi': 'IMSI',
                    'contact_number': 'Contact Number',
                    'expiry_date': 'Expiry Date',
                    'status_date': 'Status Date',
                    'creation_date': 'Creation Date',
                    'active_date': 'Active Date',
                    'extraction_date': 'Extraction Date',
                    'created_at': 'Created At',
                    'updated_at': 'Updated At'
                })

                # Format date columns to ISO format (matching normal export)
                date_columns = ['Status Date', 'Creation Date', 'Active Date', 'Expiry Date', 'Extraction Date', 'Created At', 'Updated At']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%dT%H:%M:%S').fillna('')

                parks = []  # Skip parks_to_records_with_progress for 2B (already have DataFrame)

            elif export_type == "anomalies":
                # Export only records marked as anomalies during processing
                query = db.query(Park)
                if accessible_dots:
                    query = query.filter(Park.dot_id.in_(accessible_dots))

                # Apply filters WITHOUT the anomaly exclusion (exclude_anomalies=False)
                query = apply_filters_to_query(
                    query=query,
                    dot_ids=export_params.get("dot_ids"),
                    actel_codes=export_params.get("actel_codes"),
                    subscriber_statuses=export_params.get("subscriber_statuses"),
                    telecom_types=export_params.get("telecom_types"),
                    offer_names=export_params.get("offer_names"),
                    offer_types=export_params.get("offer_types"),
                    customer_l2_codes=export_params.get("customer_l2_codes"),
                    customer_l3_codes=export_params.get("customer_l3_codes"),
                    search=export_params.get("search"),
                    date_from=export_params.get("date_from"),
                    date_to=export_params.get("date_to"),
                    include_exclusion_2b=False,
                    exclude_anomalies=False  # Don't exclude anomalies
                )

                # Filter to get ONLY anomalies (supports both persisted flag + rule safety net)
                query = apply_anomaly_only(query, Park)
                parks = query.all()
            else:
                # Normal export
                parks = query.all()

            # Process exports: 2B already has DataFrame, others need processing
            if export_type == "2b":
                # DataFrame already created from pandas read_sql (fast method)
                if len(df) == 0:
                    raise Exception("No 2B records found with applied filters")
                logger.info(f"✅ 2B DataFrame ready with {len(df):,} records (fast method)")
            else:
                # Normal and anomalies: process using ORM iteration
                if len(parks) == 0:
                    raise Exception("No data found with applied filters")

                # Process records (50-80%)
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": 50,
                    "message": f"Processing {len(parks):,} records..."
                }))
                records = parks_to_records_with_progress(parks, 50, 80, "")
                df = pd.DataFrame(records)

            # Create file (80-95%)
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 80,
                "message": "Creating export file..."
            }))

            if export_type == "anomalies":
                base_filename = f"Anomalie_Parc_NGBSS_{timestamp}"
            elif export_type == "2b":
                base_filename = f"Facturation_Groupee_2B_{timestamp}"
            else:
                base_filename = f"Parc_Corporate_NGBSS_{timestamp}"

            # Use correct file extension: .xlsx for excel, .csv for csv
            file_ext = "xlsx" if format == "excel" else "csv"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}')

            # Optimize writing for large datasets
            total_records = len(df)
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "processing",
                "progress": 85,
                "message": f"Writing {total_records:,} records to file..."
            }))

            sheet_name = "Facturation 2B" if export_type == "2b" else "Parc Data"
            if format == "excel":
                if total_records > 100000:
                    logger.info(f"📝 Large Excel dataset ({total_records:,} records). Optimizing before writing...")
                    asyncio.run(processing_ws_manager.send_task_update(task_id, {
                        "status": "processing",
                        "progress": 87,
                        "message": f"Preparing {total_records:,} records for Excel export... (this may take several minutes for large files)"
                    }))
                    for col in df.select_dtypes(include=['object']).columns:
                        df[col] = df[col].astype(str)
                    asyncio.run(processing_ws_manager.send_task_update(task_id, {
                        "status": "processing",
                        "progress": 90,
                        "message": f"Writing {total_records:,} records to Excel file... Please wait."
                    }))
                else:
                    asyncio.run(processing_ws_manager.send_task_update(task_id, {
                        "status": "processing",
                        "progress": 88,
                        "message": f"Writing {total_records:,} records to Excel..."
                    }))
                excel_buffer = io.BytesIO()
                _write_parc_excel_french(df, excel_buffer, sheet_name)
                with open(temp_file.name, "wb") as f:
                    f.write(excel_buffer.getvalue())
                if total_records > 100000:
                    logger.info(f"✅ Excel file written successfully ({total_records:,} records)")
                filename = f"{base_filename}.xlsx"
            else:
                if total_records > 500000:
                    asyncio.run(processing_ws_manager.send_task_update(task_id, {
                        "status": "processing",
                        "progress": 88,
                        "message": f"Writing {total_records:,} records to CSV..."
                    }))
                df_f = _apply_french_number_format_df(df, PARC_NUMERIC_COLS)
                df_f.to_csv(temp_file.name, index=False, sep=";", encoding="utf-8-sig")
                filename = f"{base_filename}.csv"

            export_tasks[task_id].update({
                "file_path": temp_file.name,
                "filename": filename,
                "record_count": len(df)
            })

        # Completed
        export_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "end_time": datetime.utcnow().isoformat()
        })

        # Build completion message
        if export_type == "all":
            files_msg = f"3 files: Normal ({export_tasks[task_id]['normal_count']:,}), Anomalies ({export_tasks[task_id]['anomaly_count']:,}), Facturation 2B ({export_tasks[task_id]['facturation_2b_count']:,})"
        else:
            record_count = export_tasks[task_id].get('record_count', 0)
            files_msg = f"Export completed: {record_count:,} records"

        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "completed",
            "progress": 100,
            "message": files_msg,
            "filename": filename,
            "download_url": f"/api/park-analytics/export-download/{task_id}"
        }))

    except Exception as e:
        logger.error(f"Export error for task {task_id}: {e}", exc_info=True)
        export_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "end_time": datetime.utcnow().isoformat()
        })

        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "failed",
            "progress": 0,
            "message": f"Export failed: {str(e)}"
        }))

    finally:
        db.close()


def get_combined_parks_query(db: Session, include_exclusion_2b: bool = False, **filter_params):
    """Helper to get combined results from parks and parks_2b tables

    Args:
        db: Database session
        include_exclusion_2b: If True, include records from parks_2b table
        **filter_params: Filter parameters to apply to both queries

    Returns:
        List of park records (either from parks only, or parks + parks_2b)
    """
    # Build query for main parks table
    parks_query = db.query(Park)
    parks_query = apply_filters_to_query(parks_query, **filter_params, include_exclusion_2b=False)

    if not include_exclusion_2b:
        # Return only parks table results
        return parks_query.all()

    # Also query from parks_2b table
    parks_2b_query = db.query(Park2B)
    parks_2b_query = apply_filters_to_query(parks_2b_query, **filter_params, include_exclusion_2b=False)

    # Combine results
    parks_results = parks_query.all()
    parks_2b_results = parks_2b_query.all()

    return parks_results + parks_2b_results


def apply_filters_to_query(
    query,
    dot_ids: Optional[str] = None,
    actel_codes: Optional[str] = None,
    subscriber_statuses: Optional[str] = None,
    telecom_types: Optional[str] = None,
    offer_names: Optional[str] = None,
    offer_types: Optional[str] = None,
    customer_l2_codes: Optional[str] = None,
    customer_l3_codes: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    include_exclusion_2b: Optional[bool] = None,
    exclude_anomalies: bool = True
):
    """Helper function to apply filters to a query

    Works with both Park and Park2B models since they have the same structure

    Args:
        exclude_anomalies: If True (default), filter out anomalies from results.
                          Set to False for anomaly-only exports.
    """
    # Get the model class from the query
    # This allows the function to work with both Park and Park2B
    model = query.column_descriptions[0]['entity']

    # Log all filter parameters
    filters_dict = {
        "dot_ids": dot_ids,
        "actel_codes": actel_codes,
        "subscriber_statuses": subscriber_statuses,
        "telecom_types": telecom_types,
        "offer_names": offer_names,
        "offer_types": offer_types,
        "customer_l2_codes": customer_l2_codes,
        "customer_l3_codes": customer_l3_codes,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "include_exclusion_2b": include_exclusion_2b
    }
    # Only log non-empty filters
    active_filters = {k: v for k, v in filters_dict.items() if v}
    if active_filters:
        logger.info(f"🔍 Applying filters to {model.__name__}: {active_filters}")

    # Apply multiple value filters (comma-separated)
    if dot_ids:
        dot_id_list = [int(id.strip())
                       for id in dot_ids.split(',') if id.strip()]
        query = query.filter(model.dot_id.in_(dot_id_list))

    if actel_codes:
        actel_list = [code.strip()
                      for code in actel_codes.split(',') if code.strip()]
        query = query.filter(model.actel_code.in_(actel_list))

    if subscriber_statuses:
        status_list = [status.strip()
                       for status in subscriber_statuses.split(',') if status.strip()]
        query = query.filter(model.subscriber_status.in_(status_list))

    if telecom_types:
        telecom_list = [ttype.strip()
                        for ttype in telecom_types.split(',') if ttype.strip()]
        query = query.filter(model.telecom_type.in_(telecom_list))

    if offer_names:
        offer_list = [offer.strip()
                      for offer in offer_names.split(',') if offer.strip()]
        # Use case-insensitive matching to handle variations like "Moohtarif" vs "moohtarif"
        offer_conditions = [model.offer_name.ilike(offer) for offer in offer_list]
        query = query.filter(or_(*offer_conditions))

    if offer_types:
        offer_type_list = [otype.strip()
                           for otype in offer_types.split(',') if otype.strip()]
        query = query.filter(model.offer_type.in_(offer_type_list))

    if customer_l2_codes:
        l2_list = [code.strip()
                   for code in customer_l2_codes.split(',') if code.strip()]
        query = query.filter(model.customer_l2_code.in_(l2_list))

    if customer_l3_codes:
        l3_list = [code.strip()
                   for code in customer_l3_codes.split(',') if code.strip()]
        query = query.filter(model.customer_l3_code.in_(l3_list))

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                model.customer_code.ilike(search_term),
                model.service_number.ilike(search_term),
                model.customer_full_name.ilike(search_term),
                model.username.ilike(search_term)
            )
        )

    # Apply date range filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(model.created_at >= from_date)
        except ValueError:
            pass  # Ignore invalid date format

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(model.created_at <= to_date)
        except ValueError:
            pass  # Ignore invalid date format

    # Note: 2B records are now stored in a separate parks_2b table
    # They are excluded by default (not in parks table)
    # The include_exclusion_2b parameter is handled at the query level
    # by querying from both tables when needed

    # Filter out anomalies from visualizations and analytics (unless explicitly disabled)
    # Anomalies should only be visible in the anomaly export
    if exclude_anomalies:
        query = apply_default_anomaly_exclusion(query, model)
        logger.info(f"🚫 Filtering out anomalies for {model.__name__} (exclude_anomalies={exclude_anomalies})")

    return query


@park_analytics_router.get("/overview")
async def get_park_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)"),
    # 2B Exclusion filter
    include_exclusion_2b: Optional[bool] = Query(
        False, description="Include records with customer_l1_code = '2B' (excluded by default)")
):
    """Get overview analytics for Parc Corporate NGBSS with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /overview - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_overview_analytics(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {
            "total_active_subscribers": 0,
            "total_dots": 0,
            "recent_activity": 0,
            "last_updated": None,
            "total_subscribers": 0,
            "inactive_subscribers": 0,
            "suspended_subscribers": 0,
            "total_revenue": 0.0,
            "filters_applied": True
        }

    # Apply filters to parks query
    parks_query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Calculate metrics from parks table
    total_subscribers = parks_query.count()
    active_subscribers = parks_query.filter(
        Park.subscriber_status.in_(
            ["Active", "ACTIVE", "active", "ACTIF", "actif"])
    ).count()
    inactive_subscribers = parks_query.filter(
        Park.subscriber_status.in_(
            ["Inactive", "INACTIVE", "inactive", "INACTIF", "inactif"])
    ).count()
    suspended_subscribers = parks_query.filter(
        Park.subscriber_status.in_(
            ["Suspended", "SUSPENDED", "suspended", "SUSPENDU", "suspendu"])
    ).count()
    revenue_result = parks_query.with_entities(func.sum(Park.rental_fees)).scalar()
    total_revenue = float(revenue_result) if revenue_result else 0.0
    last_record = parks_query.order_by(Park.created_at.desc()).first()
    last_update = last_record.created_at.isoformat() if last_record else None
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = parks_query.filter(Park.created_at >= seven_days_ago).count()

    # If include_exclusion_2b is True, also query parks_2b table and combine metrics
    if include_exclusion_2b:
        parks_2b_query = db.query(Park2B)
        if accessible_dots:
            parks_2b_query = parks_2b_query.filter(Park2B.dot_id.in_(accessible_dots))
        parks_2b_query = apply_filters_to_query(
            parks_2b_query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
            offer_names, offer_types, customer_l2_codes, customer_l3_codes,
            search, date_from, date_to, include_exclusion_2b=False
        )

        # Calculate metrics from parks_2b table
        total_subscribers_2b = parks_2b_query.count()
        active_subscribers_2b = parks_2b_query.filter(
            Park2B.subscriber_status.in_(
                ["Active", "ACTIVE", "active", "ACTIF", "actif"])
        ).count()
        inactive_subscribers_2b = parks_2b_query.filter(
            Park2B.subscriber_status.in_(
                ["Inactive", "INACTIVE", "inactive", "INACTIF", "inactif"])
        ).count()
        suspended_subscribers_2b = parks_2b_query.filter(
            Park2B.subscriber_status.in_(
                ["Suspended", "SUSPENDED", "suspended", "SUSPENDU", "suspendu"])
        ).count()
        revenue_result_2b = parks_2b_query.with_entities(func.sum(Park2B.rental_fees)).scalar()
        total_revenue_2b = float(revenue_result_2b) if revenue_result_2b else 0.0
        last_record_2b = parks_2b_query.order_by(Park2B.created_at.desc()).first()
        if last_record_2b and (not last_record or last_record_2b.created_at > last_record.created_at):
            last_update = last_record_2b.created_at.isoformat()
        recent_activity_2b = parks_2b_query.filter(Park2B.created_at >= seven_days_ago).count()

        # Combine metrics
        total_subscribers += total_subscribers_2b
        active_subscribers += active_subscribers_2b
        inactive_subscribers += inactive_subscribers_2b
        suspended_subscribers += suspended_subscribers_2b
        total_revenue += total_revenue_2b
        recent_activity += recent_activity_2b

    # Get accessible DOTs count - only count DOTs from Parc Corporate NGBSS module
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    
    # Filter to only count DOTs that actually belong to this module (exclude global DOTs)
    if accessible_dots:
        module_dots = db.query(DOT).filter(
            DOT.id.in_(accessible_dots),
            DOT.module == MODULE_PARC_CORPORATE_NGBSS
        ).all()
        total_dots = len(module_dots)
    else:
        total_dots = 0

    return {
        "total_active_subscribers": active_subscribers,  # ✅ Match frontend expectation
        "total_dots": total_dots,                        # ✅ Match frontend expectation
        "recent_activity": recent_activity,              # ✅ Match frontend expectation
        "last_updated": last_update,                     # ✅ Match frontend expectation
        "total_subscribers": total_subscribers,
        "inactive_subscribers": inactive_subscribers,
        "suspended_subscribers": suspended_subscribers,
        "total_revenue": round(total_revenue, 2),
        "filters_applied": True
    }


@park_analytics_router.get("/by-telecom-type")
async def get_by_telecom_type(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)"),
    # 2B Exclusion filter
    include_exclusion_2b: Optional[bool] = Query(
        False, description="Include records from parks_2b table")
):
    """Get distribution by Telecom Type with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-telecom-type - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters to parks query
    parks_query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Get telecom type distribution from parks
    parks_distribution = parks_query.filter(
        Park.telecom_type.isnot(None)
    ).with_entities(
        Park.telecom_type,
        func.count(Park.id).label('count')
    ).group_by(Park.telecom_type).all()

    # Combine with parks_2b if needed
    distribution_dict = {item.telecom_type or "UNKNOWN": item.count for item in parks_distribution}
    
    if include_exclusion_2b:
        parks_2b_query = db.query(Park2B)
        if accessible_dots:
            parks_2b_query = parks_2b_query.filter(Park2B.dot_id.in_(accessible_dots))
        parks_2b_query = apply_filters_to_query(
            parks_2b_query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
            offer_names, offer_types, customer_l2_codes, customer_l3_codes,
            search, date_from, date_to, include_exclusion_2b=False
        )
        parks_2b_distribution = parks_2b_query.filter(
            Park2B.telecom_type.isnot(None)
        ).with_entities(
            Park2B.telecom_type,
            func.count(Park2B.id).label('count')
        ).group_by(Park2B.telecom_type).all()
        
        # Merge distributions
        for item in parks_2b_distribution:
            key = item.telecom_type or "UNKNOWN"
            distribution_dict[key] = distribution_dict.get(key, 0) + item.count

    total_count = sum(distribution_dict.values())
    distribution = [
        {
            "type": key,
            "count": count,
            "percentage": round((count / total_count * 100) if total_count > 0 else 0, 2)
        }
        for key, count in sorted(distribution_dict.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-subscriber-status")
async def get_by_subscriber_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get subscriber status distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-subscriber-status - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_subscriber_status_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Get subscriber status distribution
    status_distribution = query.filter(
        Park.subscriber_status.isnot(None)
    ).with_entities(
        Park.subscriber_status,
        func.count(Park.id).label('count')
    ).group_by(Park.subscriber_status).order_by(func.count(Park.id).desc()).all()

    total_count = sum([item.count for item in status_distribution])

    distribution = []
    for item in status_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "status": item.subscriber_status or "UNKNOWN",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.post("/cache/invalidate")
async def invalidate_kpi_cache(
    current_user: User = Depends(get_current_user),
    user_only: bool = Query(
        False, description="Invalidate only current user's cache")
):
    """Invalidate KPI cache for faster data refresh"""

    if user_only:
        kpi_cache_service.invalidate_user_cache(current_user.id)
        return {"message": f"Cache invalidated for user {current_user.id}"}
    else:
        kpi_cache_service.invalidate_all_cache()
        return {"message": "All KPI cache invalidated"}


@park_analytics_router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """Get KPI cache statistics"""
    return kpi_cache_service.get_cache_stats()


@park_analytics_router.get("/by-customer-l2")
async def get_by_customer_l2(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get customer L2 distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-customer-l2 - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_customer_l2_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Get customer L2 distribution
    l2_distribution = query.filter(
        Park.customer_l2_code.isnot(None)
    ).with_entities(
        Park.customer_l2_code,
        Park.customer_l2_description,
        func.count(Park.id).label('count')
    ).group_by(Park.customer_l2_code, Park.customer_l2_description).order_by(func.count(Park.id).desc()).limit(50).all()

    total_count = sum([item.count for item in l2_distribution])

    distribution = []
    for item in l2_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            # ✅ Match cached service format
            "code": item.customer_l2_code or "UNKNOWN",
            # ✅ Match cached service format
            "description": item.customer_l2_description or "N/A",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-customer-l3")
async def get_by_customer_l3(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get customer L3 distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-customer-l3 - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_customer_l3_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Get customer L3 distribution
    l3_distribution = query.filter(
        Park.customer_l3_code.isnot(None)
    ).with_entities(
        Park.customer_l3_code,
        Park.customer_l3_description,
        func.count(Park.id).label('count')
    ).group_by(Park.customer_l3_code, Park.customer_l3_description).order_by(func.count(Park.id).desc()).limit(100).all()

    total_count = sum([item.count for item in l3_distribution])

    distribution = []
    for item in l3_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            # ✅ Match cached service format
            "code": item.customer_l3_code or "UNKNOWN",
            # ✅ Match cached service format
            "description": item.customer_l3_description or "N/A",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-dot")
async def get_by_dot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get distribution by DOT with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-dot - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if not accessible_dots:
        return {"distribution": [], "total": 0}

    # Build base query for filtering
    park_query = db.query(Park).filter(Park.dot_id.in_(accessible_dots))

    # Apply filters to park query
    park_query = apply_filters_to_query(
        park_query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to, include_exclusion_2b=False
    )

    # Get DOT distribution with filtered parks
    dot_distribution = db.query(
        DOT.name,
        DOT.id,
        func.count(Park.id).label('count')
    ).outerjoin(
        Park, and_(DOT.id == Park.dot_id, Park.id.in_(
            park_query.with_entities(Park.id)))
    ).filter(
        DOT.id.in_(accessible_dots)
    ).group_by(
        DOT.id, DOT.name
    ).order_by(func.count(Park.id).desc()).all()

    total_count = sum([item.count for item in dot_distribution])

    distribution = []
    for item in dot_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "dot_name": item.name,
            "dot_id": item.id,
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/filters")
async def get_available_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available filter values for dropdowns"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {
            "dots": [],
            "actel_codes": [],
            "subscriber_statuses": [],
            "telecom_types": [],
            "offer_names": [],
            "offer_types": [],
            "customer_l2_codes": [],
            "customer_l3_codes": []
        }

    # IMPORTANT: Filter out anomalies from filter dropdowns
    # Anomalies should not appear in filter options
    query = apply_default_anomaly_exclusion(query, Park)

    # Get DOTs - filter by Parc Corporate NGBSS module
    dots = db.query(DOT).filter(
        DOT.id.in_(accessible_dots),
        DOT.module == MODULE_PARC_CORPORATE_NGBSS
    ).all()

    # Get unique values for filters
    # Get Actel Codes with their associated DOT IDs
    actel_codes_with_dots = query.filter(
        Park.actel_code.isnot(None),
        Park.dot_id.isnot(None)
    ).with_entities(
        Park.actel_code, Park.dot_id
    ).distinct().limit(200).all()
    
    # Build mapping of DOT ID to Actel Codes
    dot_actel_mapping = {}
    all_actel_codes = set()
    for actel_code, dot_id in actel_codes_with_dots:
        if actel_code and dot_id:
            all_actel_codes.add(actel_code)
            if dot_id not in dot_actel_mapping:
                dot_actel_mapping[dot_id] = []
            if actel_code not in dot_actel_mapping[dot_id]:
                dot_actel_mapping[dot_id].append(actel_code)
    
    subscriber_statuses = query.filter(Park.subscriber_status.isnot(
        None)).with_entities(Park.subscriber_status).distinct().all()
    telecom_types = query.filter(Park.telecom_type.isnot(
        None)).with_entities(Park.telecom_type).distinct().all()

    # Get offer names with case-insensitive deduplication
    # No limit - get all unique offer names
    offer_names_raw = query.filter(Park.offer_name.isnot(None)).with_entities(
        Park.offer_name).distinct().all()

    # Deduplicate by case-insensitive comparison
    offer_name_map = {}
    for (offer_name,) in offer_names_raw:
        if offer_name:
            lower_name = offer_name.lower()
            if lower_name not in offer_name_map:
                offer_name_map[lower_name] = offer_name

    offer_names = [(name,) for name in sorted(offer_name_map.values())]

    offer_types = query.filter(Park.offer_type.isnot(None)).with_entities(
        Park.offer_type).distinct().all()
    
    # Get relationships between Subscriber Status, Telecom Type, and Offer Name
    # No limit - get all relationships to build complete mappings
    status_telecom_offer_relationships = query.filter(
        Park.subscriber_status.isnot(None),
        Park.telecom_type.isnot(None),
        Park.offer_name.isnot(None)
    ).with_entities(
        Park.subscriber_status, Park.telecom_type, Park.offer_name
    ).distinct().all()
    
    # Build mappings for filtering
    # Map: subscriber_status -> set of telecom_types
    status_to_telecom = {}
    # Map: subscriber_status -> set of offer_names
    status_to_offers = {}
    # Map: telecom_type -> set of subscriber_statuses
    telecom_to_status = {}
    # Map: telecom_type -> set of offer_names
    telecom_to_offers = {}
    # Map: offer_name -> set of subscriber_statuses
    offer_to_status = {}
    # Map: offer_name -> set of telecom_types
    offer_to_telecom = {}
    
    for status, telecom, offer in status_telecom_offer_relationships:
        if status and telecom and offer:
            # Status -> Telecom
            if status not in status_to_telecom:
                status_to_telecom[status] = set()
            status_to_telecom[status].add(telecom)
            
            # Status -> Offer
            if status not in status_to_offers:
                status_to_offers[status] = set()
            status_to_offers[status].add(offer)
            
            # Telecom -> Status
            if telecom not in telecom_to_status:
                telecom_to_status[telecom] = set()
            telecom_to_status[telecom].add(status)
            
            # Telecom -> Offer
            if telecom not in telecom_to_offers:
                telecom_to_offers[telecom] = set()
            telecom_to_offers[telecom].add(offer)
            
            # Offer -> Status
            if offer not in offer_to_status:
                offer_to_status[offer] = set()
            offer_to_status[offer].add(status)
            
            # Offer -> Telecom
            if offer not in offer_to_telecom:
                offer_to_telecom[offer] = set()
            offer_to_telecom[offer].add(telecom)
    customer_l2_codes = query.filter(Park.customer_l2_code.isnot(None)).with_entities(
        Park.customer_l2_code, Park.customer_l2_description).distinct().limit(50).all()
    
    # Get Customer L2 and L3 codes with their relationships
    l2_l3_relationships = query.filter(
        Park.customer_l2_code.isnot(None),
        Park.customer_l3_code.isnot(None)
    ).with_entities(
        Park.customer_l2_code, Park.customer_l3_code, Park.customer_l3_description
    ).distinct().limit(200).all()
    
    # Build mapping of L2 Code to L3 Codes
    l2_l3_mapping = {}
    all_l3_codes = set()
    for l2_code, l3_code, l3_description in l2_l3_relationships:
        if l2_code and l3_code:
            all_l3_codes.add((l3_code, l3_description))
            if l2_code not in l2_l3_mapping:
                l2_l3_mapping[l2_code] = []
            # Check if this L3 code is already in the list for this L2 code
            if not any(item["code"] == l3_code for item in l2_l3_mapping[l2_code]):
                l2_l3_mapping[l2_code].append({
                    "code": l3_code,
                    "description": l3_description or "N/A"
                })
    
    # Get all unique L3 codes (for when no L2 is selected)
    customer_l3_codes = query.filter(Park.customer_l3_code.isnot(None)).with_entities(
        Park.customer_l3_code, Park.customer_l3_description).distinct().limit(50).all()

    return {
        "dots": [{"id": dot.id, "name": dot.name} for dot in dots],
        "actel_codes": sorted(list(all_actel_codes)),
        "dot_actel_mapping": {str(dot_id): codes for dot_id, codes in dot_actel_mapping.items()},
        "subscriber_statuses": [status[0] for status in subscriber_statuses if status[0]],
        "telecom_types": [type[0] for type in telecom_types if type[0]],
        "offer_names": [name[0] for name in offer_names if name[0]],
        "offer_types": [type[0] for type in offer_types if type[0]],
        "customer_l2_codes": [{"code": item[0], "description": item[1]} for item in customer_l2_codes if item[0]],
        "customer_l3_codes": [{"code": item[0], "description": item[1]} for item in customer_l3_codes if item[0]],
        "l2_l3_mapping": {str(l2_code): l3_list for l2_code, l3_list in l2_l3_mapping.items()},
        "status_telecom_mapping": {status: list(telecoms) for status, telecoms in status_to_telecom.items()},
        "status_offer_mapping": {status: list(offers) for status, offers in status_to_offers.items()},
        "telecom_status_mapping": {telecom: list(statuses) for telecom, statuses in telecom_to_status.items()},
        "telecom_offer_mapping": {telecom: list(offers) for telecom, offers in telecom_to_offers.items()},
        "offer_status_mapping": {offer: list(statuses) for offer, statuses in offer_to_status.items()},
        "offer_telecom_mapping": {offer: list(telecoms) for offer, telecoms in offer_to_telecom.items()}
    }


@park_analytics_router.get("/preview-data")
async def get_preview_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Get sample park records for dashboard preview with filtering support

    Returns up to `limit` park records from accessible DOTs with full details.
    All filters are applied to the preview data.

    Parameters:
        limit: Number of records to return (1-100, default 10)
        offset: Number of records to skip for pagination (default 0)
        All filter parameters are supported

    Returns:
        Dictionary with:
        - records: List of park records with key fields
        - total_available: Total records accessible to user (after filters)
        - preview_limit: Actual limit applied
        - preview_offset: Offset applied

    Example:
        GET /api/park-analytics/preview-data?limit=20&offset=0&dot_ids=1,2
    """
    
    # Log received filter parameters
    logger.info(
        f"📋 GET /preview-data - User {current_user.id} - Limit: {limit}, Offset: {offset} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    try:
        # Apply DOT-based permission filtering
        query = db.query(Park)
        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)

        if not accessible_dots:
            logger.warning(f"User {current_user.id} has no accessible DOTs")
            return {
                "records": [],
                "total_available": 0,
                "preview_limit": limit,
                "preview_offset": offset,
                "message": "No accessible data"
            }

        query = query.filter(Park.dot_id.in_(accessible_dots))

        # Apply all filters using the shared helper function
        query = apply_filters_to_query(
            query=query,
            dot_ids=dot_ids,
            actel_codes=actel_codes,
            subscriber_statuses=subscriber_statuses,
            telecom_types=telecom_types,
            offer_names=offer_names,
            offer_types=offer_types,
            customer_l2_codes=customer_l2_codes,
            customer_l3_codes=customer_l3_codes,
            search=search,
            date_from=date_from,
            date_to=date_to,
            include_exclusion_2b=False
        )

        # Get total count for pagination info (after filters, including anomaly exclusion)
        total_count = query.count()
        logger.info(f"📊 Preview data query: {total_count:,} records (anomalies excluded)")

        # Apply pagination
        records = query.order_by(Park.created_at.desc()) \
            .offset(offset) \
            .limit(limit) \
            .all()
        
        # Verify no anomalies in results (safety check)
        anomaly_count = sum(1 for r in records if r.is_anomaly)
        if anomaly_count > 0:
            logger.warning(f"⚠️ WARNING: Found {anomaly_count} anomalies in preview data results! This should not happen.")

        # Format response with all fields
        preview_records = []
        for record in records:
            preview_records.append({
                "id": record.id,
                "file_upload_id": record.file_upload_id,
                "extraction_date": record.extraction_date.isoformat() if record.extraction_date else None,
                "dot_id": record.dot_id,
                "dot_name": record.dot.name if record.dot else "",
                "actel_code": record.actel_code or "",
                "customer_l1_code": record.customer_l1_code or "",
                "customer_l1_description": record.customer_l1_description or "",
                "customer_l2_code": record.customer_l2_code or "",
                "customer_l2_description": record.customer_l2_description or "",
                "customer_l3_code": record.customer_l3_code or "",
                "customer_l3_description": record.customer_l3_description or "",
                "telecom_type": record.telecom_type or "",
                "offer_type": record.offer_type or "",
                "offer_name": record.offer_name or "",
                "rental_fees": float(record.rental_fees) if record.rental_fees else 0.0,
                "customer_code": record.customer_code or "",
                "service_number": record.service_number or "",
                "related_service_number": record.related_service_number or "",
                "username": record.username or "",
                "subscriber_status": record.subscriber_status or "",
                "status_date": record.status_date.isoformat() if record.status_date else None,
                "creation_date": record.creation_date.isoformat() if record.creation_date else None,
                "active_date": record.active_date.isoformat() if record.active_date else None,
                "csr_name": record.csr_name or "",
                "department_name": record.department_name or "",
                "state": record.state or "",
                "area": record.area or "",
                "town": record.town or "",
                "grid": record.grid or "",
                "street": record.street or "",
                "street_number": record.street_number or "",
                "building_no": record.building_no or "",
                "unit": record.unit or "",
                "floor": record.floor or "",
                "house_no": record.house_no or "",
                "additional_address_info": record.additional_address_info or "",
                "customer_full_name": record.customer_full_name or "",
                "province": record.province or "",
                "district": record.district or "",
                "city": record.city or "",
                "postal_code": record.postal_code or "",
                "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
                "iccid": record.iccid or "",
                "imsi": record.imsi or "",
                "contact_number": record.contact_number or "",
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })

        logger.info(
            f"User {current_user.id} retrieved {len(preview_records)} preview records "
            f"(offset={offset}, limit={limit}, total={total_count})"
        )

        return {
            "records": preview_records,
            "total_available": total_count,
            "preview_limit": limit,
            "preview_offset": offset,
            "records_returned": len(preview_records)
        }

    except Exception as e:
        logger.error(f"Error retrieving preview data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving preview data: {str(e)}"
        )


@park_analytics_router.get("/preview-data/column-values")
async def get_park_column_values(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    column: str = Query(..., description="Column name to get unique values for"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of values to return (None = unlimited)"),
    # Filter parameters to respect active filters
    dot_ids: Optional[str] = Query(None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(None, description="Comma-separated Customer L3 codes"),
    search: Optional[str] = Query(None, description="Search filter"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Get unique values for a specific column in parks table.
    Used for populating Excel-like dropdown filters.
    Supports ALL columns in the parks table.
    Only returns values from parks accessible to the user based on DOT permissions.
    Respects active filters - only returns values that exist in filtered results.
    Returns ALL unique values by default (no limit).
    """
    PermissionService.require_permission(
        current_user, db, "can_view_encaissement_data")
    
    try:
        # Apply DOT-based permission filtering
        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
        
        if not accessible_dots:
            return {
                "column": column,
                "values": [],
                "count": 0
            }
        
        # Start with base query filtered by accessible DOTs
        base_query = db.query(Park).filter(Park.dot_id.in_(accessible_dots))
        
        # Apply all active filters to the base query
        # This ensures we only get values that exist in the filtered dataset
        # exclude_anomalies=True by default - anomalies should NOT appear in Excel-like filter dropdowns
        base_query = apply_filters_to_query(
            query=base_query,
            dot_ids=dot_ids,
            actel_codes=actel_codes,
            subscriber_statuses=subscriber_statuses,
            telecom_types=telecom_types,
            offer_names=offer_names,
            offer_types=offer_types,
            customer_l2_codes=customer_l2_codes,
            customer_l3_codes=customer_l3_codes,
            search=search,
            date_from=date_from,
            date_to=date_to,
            include_exclusion_2b=False,
            exclude_anomalies=True  # Explicitly exclude anomalies from Excel-like filter dropdowns
        )
        
        logger.info(f"🔍 Column values query for '{column}': filtering out anomalies (exclude_anomalies=True)")
        
        # Map column names to actual model attributes
        column_map = {
            "id": Park.id,
            "file_upload_id": Park.file_upload_id,
            "extraction_date": Park.extraction_date,
            "dot_id": Park.dot_id,
            "actel_code": Park.actel_code,
            "customer_l1_code": Park.customer_l1_code,
            "customer_l1_description": Park.customer_l1_description,
            "customer_l2_code": Park.customer_l2_code,
            "customer_l2_description": Park.customer_l2_description,
            "customer_l3_code": Park.customer_l3_code,
            "customer_l3_description": Park.customer_l3_description,
            "telecom_type": Park.telecom_type,
            "offer_type": Park.offer_type,
            "offer_name": Park.offer_name,
            "rental_fees": Park.rental_fees,
            "customer_code": Park.customer_code,
            "service_number": Park.service_number,
            "related_service_number": Park.related_service_number,
            "username": Park.username,
            "subscriber_status": Park.subscriber_status,
            "status_date": Park.status_date,
            "creation_date": Park.creation_date,
            "active_date": Park.active_date,
            "csr_name": Park.csr_name,
            "department_name": Park.department_name,
            "state": Park.state,
            "area": Park.area,
            "town": Park.town,
            "grid": Park.grid,
            "street": Park.street,
            "street_number": Park.street_number,
            "building_no": Park.building_no,
            "unit": Park.unit,
            "floor": Park.floor,
            "house_no": Park.house_no,
            "additional_address_info": Park.additional_address_info,
            "customer_full_name": Park.customer_full_name,
            "province": Park.province,
            "district": Park.district,
            "city": Park.city,
            "postal_code": Park.postal_code,
            "expiry_date": Park.expiry_date,
            "iccid": Park.iccid,
            "imsi": Park.imsi,
            "contact_number": Park.contact_number,
            "created_at": Park.created_at,
            "updated_at": Park.updated_at,
        }
        
        # Special handling for dot_name (need to join with DOT table)
        if column == "dot_name":
            # Use the filtered base_query to get distinct DOT names
            query = base_query.join(DOT, DOT.id == Park.dot_id) \
                .with_entities(DOT.name) \
                .filter(DOT.name.isnot(None)) \
                .distinct() \
                .order_by(DOT.name.asc())
            # Apply limit only if specified
            if limit is not None:
                query = query.limit(limit)
            values = query.all()
        elif column not in column_map:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{column}' not found. Available columns: {list(column_map.keys()) + ['dot_name']}"
            )
        else:
            # Get unique values from the filtered query
            # Use the filtered base_query to ensure we only get values that exist in filtered results
            query = base_query.with_entities(column_map[column]) \
                .filter(column_map[column].isnot(None)) \
                .distinct() \
                .order_by(column_map[column].asc())
            # Apply limit only if specified
            if limit is not None:
                query = query.limit(limit)
            values = query.all()
        
        # Convert to list of strings, filtering out None
        unique_values = []
        for v in values:
            if v[0] is not None:
                # Format based on type
                if isinstance(v[0], (datetime, date)):
                    unique_values.append(v[0].isoformat())
                elif isinstance(v[0], bool):
                    unique_values.append("Oui" if v[0] else "Non")
                elif isinstance(v[0], (int, float)):
                    unique_values.append(str(v[0]))
                else:
                    unique_values.append(str(v[0]))
        
        return {
            "column": column,
            "values": unique_values,
            "count": len(unique_values)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting column values for {column}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@park_analytics_router.post("/export-async")
async def export_data_async(
    format: str = Query("csv", regex="^(csv|excel)$"),
    export_type: str = Query("normal", regex="^(normal|anomalies|2b|all)$", description="Export type: normal, anomalies, 2b (Facturation Groupée), or all (returns ZIP with all 3 files)"),
    # Single value filters (for backward compatibility)
    dot_filter: Optional[str] = Query(None),
    actel_code_filter: Optional[str] = Query(None),
    subscriber_status_filter: Optional[str] = Query(None),
    telecom_type_filter: Optional[str] = Query(None),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start async export with progress tracking - returns task_id for monitoring"""

    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Store export parameters
    export_params = {
        "format": format,
        "export_type": export_type,
        "dot_filter": dot_filter,
        "actel_code_filter": actel_code_filter,
        "subscriber_status_filter": subscriber_status_filter,
        "telecom_type_filter": telecom_type_filter,
        "dot_ids": dot_ids,
        "actel_codes": actel_codes,
        "subscriber_statuses": subscriber_statuses,
        "telecom_types": telecom_types,
        "offer_names": offer_names,
        "offer_types": offer_types,
        "customer_l2_codes": customer_l2_codes,
        "customer_l3_codes": customer_l3_codes,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "user_id": current_user.id
    }

    # Start background export
    thread = threading.Thread(
        target=_run_export_background,
        args=(task_id, export_params),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "task_id": task_id,
        "message": "Export started in background"
    }


@park_analytics_router.get("/export-status/{task_id}")
async def get_export_status(task_id: str):
    """Get export task status"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = export_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "filename": task.get("filename"),
        "error": task.get("error"),
        "start_time": task.get("start_time"),
        "end_time": task.get("end_time"),
        "normal_count": task.get("normal_count"),
        "anomaly_count": task.get("anomaly_count"),
        "record_count": task.get("record_count"),
        "download_url": f"/api/park-analytics/export-download/{task_id}" if task["status"] == "completed" else None
    }


@park_analytics_router.get("/export-download/{task_id}")
async def download_export_file(task_id: str):
    """Download completed export file"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = export_tasks[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Export not completed yet")

    if not task.get("file_path") or not os.path.exists(task["file_path"]):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Determine media type
    filename = task["filename"]
    if filename.endswith('.zip'):
        media_type = "application/zip"
    elif filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "text/csv"

    # Return file
    def iterfile():
        with open(task["file_path"], mode="rb") as file:
            yield from file

    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@park_analytics_router.get("/export")
async def export_data(
    format: str = Query("csv", regex="^(csv|excel)$"),
    export_type: str = Query("normal", regex="^(normal|anomalies|2b|all)$", description="Export type: normal, anomalies, 2b (Facturation Groupée), or all (returns ZIP with all 3 files)"),
    # Single value filters (for backward compatibility)
    dot_filter: Optional[str] = Query(None),
    actel_code_filter: Optional[str] = Query(None),
    subscriber_status_filter: Optional[str] = Query(None),
    telecom_type_filter: Optional[str] = Query(None),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export Parc Corporate NGBSS data with filtering - returns Excel/CSV file or ZIP with both normal and anomalies (synchronous)"""

    # Log received filter parameters
    logger.info(
        f"📤 GET /export - User {current_user.id} - Type: {export_type} - Format: {format} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id, module=MODULE_PARC_CORPORATE_NGBSS)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        raise HTTPException(status_code=403, detail="No accessible data")

    # Apply single value filters (backward compatibility) - merge into dot_ids if needed
    if dot_filter:
        if dot_ids:
            # Merge with existing dot_ids
            dot_id_list = [int(id.strip()) for id in dot_ids.split(',') if id.strip()]
            if int(dot_filter) not in dot_id_list:
                dot_id_list.append(int(dot_filter))
            dot_ids = ','.join(map(str, dot_id_list))
        else:
            dot_ids = dot_filter

    # Apply all filters using the shared helper function for consistency
    query = apply_filters_to_query(
        query=query,
        dot_ids=dot_ids,
        actel_codes=actel_codes,
        subscriber_statuses=subscriber_statuses,
        telecom_types=telecom_types,
        offer_names=offer_names,
        offer_types=offer_types,
        customer_l2_codes=customer_l2_codes,
        customer_l3_codes=customer_l3_codes,
        search=search,
        date_from=date_from,
        date_to=date_to,
        include_exclusion_2b=False
    )

    # Apply backward compatibility single value filters (if not already handled)
    if actel_code_filter and not actel_codes:
        query = query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
    if subscriber_status_filter and not subscriber_statuses:
        query = query.filter(Park.subscriber_status == subscriber_status_filter)
    if telecom_type_filter and not telecom_types:
        query = query.filter(Park.telecom_type == telecom_type_filter)

    # Helper function to convert parks to records
    def parks_to_records(parks_list):
        records = []
        for park in parks_list:
            try:
                records.append({
                    # Core identifiers
                    "DOT ID": park.dot_id or "",
                    "DOT Name": park.dot.name if park.dot else "",
                    "Customer Code": park.customer_code or "",
                    "Service Number": park.service_number or "",
                    "Related Service Number": park.related_service_number or "",
                    "Customer Name": park.customer_full_name or "",
                    "Username": park.username or "",
                    "Actel Code": park.actel_code or "",

                    # Subscriber and telecom info
                    "Subscriber Status": park.subscriber_status or "",
                    "Telecom Type": park.telecom_type or "",
                    "Offer Name": park.offer_name or "",
                    "Offer Type": park.offer_type or "",
                    "Rental Fees": float(park.rental_fees) if park.rental_fees else 0.0,

                    # Customer hierarchy
                    "Customer L1 Code": park.customer_l1_code or "",
                    "Customer L1 Description": park.customer_l1_description or "",
                    "Customer L2 Code": park.customer_l2_code or "",
                    "Customer L2 Description": park.customer_l2_description or "",
                    "Customer L3 Code": park.customer_l3_code or "",
                    "Customer L3 Description": park.customer_l3_description or "",

                    # CSR and department
                    "CSR Name": park.csr_name or "",
                    "Department Name": park.department_name or "",

                    # Address information
                    "State": park.state or "",
                    "Province": park.province or "",
                    "Area": park.area or "",
                    "District": park.district or "",
                    "City": park.city or "",
                    "Town": park.town or "",
                    "Postal Code": park.postal_code or "",
                    "Street": park.street or "",
                    "Street Number": park.street_number or "",
                    "Building No": park.building_no or "",
                    "Unit": park.unit or "",
                    "Floor": park.floor or "",
                    "House No": park.house_no or "",
                    "Grid": park.grid or "",
                    "Additional Address Info": park.additional_address_info or "",

                    # Contact and technical info
                    "Contact Number": park.contact_number or "",
                    "ICCID": park.iccid or "",
                    "IMSI": park.imsi or "",

                    # Dates
                    "Status Date": park.status_date.isoformat() if park.status_date else "",
                    "Creation Date": park.creation_date.isoformat() if park.creation_date else "",
                    "Active Date": park.active_date.isoformat() if park.active_date else "",
                    "Expiry Date": park.expiry_date.isoformat() if park.expiry_date else "",
                    "Extraction Date": park.extraction_date.isoformat() if park.extraction_date else "",

                    # Metadata
                    "Created At": park.created_at.isoformat() if park.created_at else "",
                    "Updated At": park.updated_at.isoformat() if park.updated_at else ""
                })
            except Exception as e:
                logger.error(f"Error processing park record {park.id}: {e}")
                continue
        return records

    # Helper function to create file content (French number format)
    def create_file_content(df, file_format):
        output = io.BytesIO()
        if file_format == "excel":
            _write_parc_excel_french(df, output, "Parc Data")
        else:  # csv
            _write_parc_csv_french(df, output)
        output.seek(0)
        return output.getvalue()

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    # Handle "both" export type - create ZIP with both files
    if export_type == "both":
        # Get normal data (all filtered records, excluding anomalies)
        # query already has anomaly filter from apply_filters_to_query
        normal_parks = query.all()

        if len(normal_parks) == 0:
            raise HTTPException(status_code=404, detail="No data found with applied filters")

        # Get anomaly data - query for anomalies only (bypass anomaly exclusion)
        anomaly_query = db.query(Park)
        if accessible_dots:
            anomaly_query = anomaly_query.filter(Park.dot_id.in_(accessible_dots))
        
        # Apply filters WITHOUT anomaly exclusion
        anomaly_query = apply_filters_to_query(
            query=anomaly_query,
            dot_ids=dot_ids,
            actel_codes=actel_codes,
            subscriber_statuses=subscriber_statuses,
            telecom_types=telecom_types,
            offer_names=offer_names,
            offer_types=offer_types,
            customer_l2_codes=customer_l2_codes,
            customer_l3_codes=customer_l3_codes,
            search=search,
            date_from=date_from,
            date_to=date_to,
            include_exclusion_2b=False,
            exclude_anomalies=False  # Don't exclude anomalies
        )
        
        # Apply backward compatibility single value filters (if not already handled)
        if actel_code_filter and not actel_codes:
            anomaly_query = anomaly_query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
        if subscriber_status_filter and not subscriber_statuses:
            anomaly_query = anomaly_query.filter(Park.subscriber_status == subscriber_status_filter)
        if telecom_type_filter and not telecom_types:
            anomaly_query = anomaly_query.filter(Park.telecom_type == telecom_type_filter)
        
        # Filter to get ONLY anomalies (flag + safety-net rules)
        anomaly_query = apply_anomaly_only(anomaly_query, Park)
        anomaly_parks = anomaly_query.all()

        logger.info(
            f"Exporting BOTH files for user {current_user.id}: "
            f"{len(normal_parks):,} normal records, {len(anomaly_parks):,} anomaly records (format: {format})"
        )

        # Create DataFrames
        normal_df = pd.DataFrame(parks_to_records(normal_parks))
        anomaly_df = pd.DataFrame(parks_to_records(anomaly_parks)) if anomaly_parks else pd.DataFrame()

        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add normal data file
            file_ext = "xlsx" if format == "excel" else "csv"
            normal_filename = f"Parc_Corporate_NGBSS_{timestamp}.{file_ext}"
            normal_content = create_file_content(normal_df, format)
            zip_file.writestr(normal_filename, normal_content)

            # Add anomaly data file (only if there are anomalies)
            if len(anomaly_parks) > 0:
                anomaly_filename = f"Anomalie_Parc_NGBSS_{timestamp}.{file_ext}"
                anomaly_content = create_file_content(anomaly_df, format)
                zip_file.writestr(anomaly_filename, anomaly_content)
            else:
                # Add empty info file if no anomalies found
                info_content = "No anomalies found with the applied filters."
                zip_file.writestr("NO_ANOMALIES_FOUND.txt", info_content)

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=Parc_Export_{timestamp}.zip"}
        )

    # Handle single file export (normal or anomalies only)
    else:
        # If exporting anomalies only, filter for anomalies using database flag
        if export_type == "anomalies":
            # Rebuild query without anomaly exclusion
            anomaly_query = db.query(Park)
            if accessible_dots:
                anomaly_query = anomaly_query.filter(Park.dot_id.in_(accessible_dots))
            
            # Apply filters WITHOUT anomaly exclusion
            anomaly_query = apply_filters_to_query(
                query=anomaly_query,
                dot_ids=dot_ids,
                actel_codes=actel_codes,
                subscriber_statuses=subscriber_statuses,
                telecom_types=telecom_types,
                offer_names=offer_names,
                offer_types=offer_types,
                customer_l2_codes=customer_l2_codes,
                customer_l3_codes=customer_l3_codes,
                search=search,
                date_from=date_from,
                date_to=date_to,
                include_exclusion_2b=False,
                exclude_anomalies=False  # Don't exclude anomalies
            )
            
            # Apply backward compatibility single value filters (if not already handled)
            if actel_code_filter and not actel_codes:
                anomaly_query = anomaly_query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
            if subscriber_status_filter and not subscriber_statuses:
                anomaly_query = anomaly_query.filter(Park.subscriber_status == subscriber_status_filter)
            if telecom_type_filter and not telecom_types:
                anomaly_query = anomaly_query.filter(Park.telecom_type == telecom_type_filter)
            
            # Filter to get ONLY anomalies (flag + safety-net rules)
            query = apply_anomaly_only(anomaly_query, Park)

        # Get total count first for better error handling
        total_count = query.count()

        if total_count == 0:
            raise HTTPException(status_code=404, detail="No data found with applied filters")

        # Get ALL data - no limit
        parks = query.all()

        logger.info(
            f"Exporting {total_count:,} records for user {current_user.id} (type: {export_type}, format: {format})"
        )

        # Convert to records and create DataFrame
        records = parks_to_records(parks)
        df = pd.DataFrame(records)

        # Generate file
        output = io.BytesIO()

        if export_type == "anomalies":
            base_filename = f"Anomalie_Parc_NGBSS_{timestamp}"
        else:
            base_filename = f"Parc_Corporate_NGBSS_{timestamp}"

        if format == "excel":
            _write_parc_excel_french(df, output, "Parc Data")
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_filename}.xlsx"
        else:  # csv
            _write_parc_csv_french(df, output)
            media_type = "text/csv; charset=utf-8"
            filename = f"{base_filename}.csv"

        output.seek(0)

        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
