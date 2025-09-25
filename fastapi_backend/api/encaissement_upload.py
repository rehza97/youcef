from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from services.encaissement_processor import EncaissementProcessor
import logging

logger = logging.getLogger(__name__)

encaissement_upload_router = APIRouter()


@encaissement_upload_router.post("/upload-data")
async def upload_encaissement_data(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process encaissement data (ADMIN only)"""

    # RBAC: Only ADMIN can upload files per cursor rules
    from services.permission_service import PermissionService
    PermissionService.require_upload_access(current_user, db)

    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV format")

    try:
        logger.info(f"Processing encaissement file: {file.filename}")

        # Read file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            df = pd.read_excel(file.file)

        logger.info(f"File loaded with {len(df)} rows and {len(df.columns)} columns")

        # Validate data structure
        validation = EncaissementProcessor.validate_data_structure(df)
        if not validation['is_valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data structure. Missing columns: {validation['missing_columns']}"
            )

        # Process data
        df = EncaissementProcessor.process_encaissement_data(df)
        df = EncaissementProcessor.calculate_encaisse_rate(df)

        logger.info(f"Data processed successfully. Final dataset has {len(df)} rows")

        # Convert to JSON for response
        result = {
            'success': True,
            'message': f'File processed successfully. {len(df)} records processed.',
            'validation': validation,
            'processed_data': df.to_dict('records'),
            'overview': EncaissementProcessor.get_overview_data(df),
            'by_organisation': EncaissementProcessor.get_by_organisation_data(df),
            'by_date': EncaissementProcessor.get_by_date_data(df),
            'by_encaisse_rate': EncaissementProcessor.get_encaisse_rate_data(df)
        }

        return result

    except pd.errors.EmptyDataError:
        logger.error("Uploaded file is empty")
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")
    except KeyError as e:
        logger.error(f"Missing required column: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Missing required column in the data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}")


@encaissement_upload_router.post("/validate-structure")
async def validate_file_structure(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate the structure of uploaded file before processing (ADMIN only)"""

    # RBAC: Only ADMIN can validate file structures for upload
    from services.permission_service import PermissionService
    PermissionService.require_upload_access(current_user, db)

    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV format")

    try:
        logger.info(f"Validating structure of file: {file.filename}")

        # Read just the header to check structure
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file, nrows=5)  # Read only first 5 rows
        else:
            df = pd.read_excel(file.file, nrows=5)  # Read only first 5 rows

        validation = EncaissementProcessor.validate_data_structure(df)

        return {
            'filename': file.filename,
            'validation': validation,
            'sample_data': df.head(3).to_dict('records') if not df.empty else []
        }

    except Exception as e:
        logger.error(f"Error validating file structure: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error validating file structure: {str(e)}")


@encaissement_upload_router.get("/template")
async def download_template(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Excel template for encaissement data (ADMIN only)"""

    # RBAC: Only ADMIN can download upload templates
    from services.permission_service import PermissionService
    PermissionService.require_upload_access(current_user, db)

    # Create a sample template
    template_data = {
        'Org Name': ['DOT_ALGER', 'DOT_ORAN', 'DOT_CONSTANTINE'],
        'N FACT': [100, 150, 75],
        'Montant Ttc': ['125000,50', '187500,75', '95000,25'],
        'Encaissement': ['100000,40', '150000,60', '76000,20']
    }

    df_template = pd.DataFrame(template_data)

    # Save to Excel in memory
    from io import BytesIO
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_template.to_excel(writer, sheet_name='Encaissement_Data', index=False)

        # Add instructions sheet
        instructions = pd.DataFrame({
            'Column': ['Org Name', 'N FACT', 'Montant Ttc', 'Encaissement'],
            'Description': [
                'Organization name (DOT_ prefix will be cleaned)',
                'Number of invoices',
                'Total amount with tax (use comma as decimal separator)',
                'Amount collected (use comma as decimal separator)'
            ],
            'Required': ['Yes', 'Yes', 'Yes', 'Yes']
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)

    output.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        BytesIO(output.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=encaissement_template.xlsx"}
    )