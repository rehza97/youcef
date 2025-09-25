from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
import json
from database.connection import get_db
from core.security import get_current_user
from models.user import User

router = APIRouter()


class EncaissementProcessor:
    """Data processor for Encaissement AR DOT module"""

    @staticmethod
    def clean_org_name(org_name: str) -> str:
        """Clean organization name according to requirements"""
        if not org_name:
            return ""

        # Remove AT_SIEGE
        if "AT_SIEGE" in org_name:
            return ""

        # Replace DOT_ with empty
        org_name = org_name.replace("DOT_", "")

        # Replace - and _ with space
        org_name = org_name.replace("-", " ")
        org_name = org_name.replace("_", " ")

        return org_name.strip()

    @staticmethod
    def process_encaissement_data(df: pd.DataFrame) -> pd.DataFrame:
        """Process encaissement data according to requirements"""

        # Keep only the table (remove any header rows)
        df = df.dropna(subset=['Org Name', 'N FACT'])

        # Clean Org Name
        df['Org Name'] = df['Org Name'].apply(
            EncaissementProcessor.clean_org_name)

        # Remove rows where Org Name is empty (after cleaning)
        df = df[df['Org Name'] != ""]

        # Convert N FACT to numeric
        df['N FACT'] = pd.to_numeric(df['N FACT'], errors='coerce')
        df = df.dropna(subset=['N FACT'])

        # Sort by Org Name, Typ Fact, and N FACT
        df = df.sort_values(['Org Name', 'Typ Fact', 'N FACT'])

        # Create combined column
        df['Organisation& N Fact& Typ Fact'] = (
            df['Org Name'].astype(str) + "& " +
            df['N FACT'].astype(str) + "& " +
            df['Typ Fact'].astype(str)
        )

        # Handle duplicates
        duplicate_mask = df.duplicated(
            subset=['Organisation& N Fact& Typ Fact'], keep=False)
        if duplicate_mask.any():
            # Replace amounts with 0.00 for duplicates
            amount_columns = ['Montant Ht', 'Montant Taxe',
                              'Montant Ttc', 'Chiffre Aff Exe']
            for col in amount_columns:
                if col in df.columns:
                    df.loc[duplicate_mask, col] = 0.00

        # Replace . with , in amount columns
        amount_columns = ['Montant Ht', 'Montant Taxe',
                          'Montant Ttc', 'Chiffre Aff Exe', 'Encaissement']
        for col in amount_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('.', ',')

        return df

    @staticmethod
    def calculate_encaisse_rate(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate encaissement rate (Encaissement / Montant Ttc)"""
        if 'Encaissement' in df.columns and 'Montant Ttc' in df.columns:
            # Convert to numeric for calculation
            encaissement = pd.to_numeric(
                df['Encaissement'].str.replace(',', '.'), errors='coerce')
            montant_ttc = pd.to_numeric(
                df['Montant Ttc'].str.replace(',', '.'), errors='coerce')

            # Calculate rate
            df['Taux d\'encaissement'] = np.where(
                montant_ttc > 0,
                (encaissement / montant_ttc) * 100,
                0
            )

        return df

    @staticmethod
    def get_overview_data(df: pd.DataFrame) -> Dict[str, Any]:
        """Get overview data for dashboard"""
        overview = {
            'total_organisations': df['Org Name'].nunique(),
            'total_factures': len(df),
            'total_montant_ttc': df['Montant Ttc'].str.replace(',', '.').astype(float).sum(),
            'total_encaissement': df['Encaissement'].str.replace(',', '.').astype(float).sum(),
            'avg_encaisse_rate': 0
        }

        # Calculate average encaissement rate
        if 'Taux d\'encaissement' in df.columns:
            overview['avg_encaisse_rate'] = df['Taux d\'encaissement'].mean()

        return overview

    @staticmethod
    def get_by_organisation_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by organisation"""
        org_data = df.groupby('Org Name').agg({
            'N FACT': 'count',
            'Montant Ttc': lambda x: x.str.replace(',', '.').astype(float).sum(),
            'Encaissement': lambda x: x.str.replace(',', '.').astype(float).sum(),
            'Taux d\'encaissement': 'mean'
        }).reset_index()

        return org_data.to_dict('records')

    @staticmethod
    def get_by_date_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by date"""
        # Convert Date Fact to datetime
        df['Date Fact'] = pd.to_datetime(df['Date Fact'], errors='coerce')
        df = df.dropna(subset=['Date Fact'])

        date_data = df.groupby(df['Date Fact'].dt.to_period('M')).agg({
            'N FACT': 'count',
            'Montant Ttc': lambda x: x.str.replace(',', '.').astype(float).sum(),
            'Encaissement': lambda x: x.str.replace(',', '.').astype(float).sum(),
            'Taux d\'encaissement': 'mean'
        }).reset_index()

        date_data['Date Fact'] = date_data['Date Fact'].astype(str)
        return date_data.to_dict('records')

    @staticmethod
    def get_encaisse_rate_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by encaissement rate"""
        # Create rate buckets
        df['Rate Bucket'] = pd.cut(
            df['Taux d\'encaissement'],
            bins=[0, 25, 50, 75, 100],
            labels=['0-25%', '25-50%', '50-75%', '75-100%']
        )

        rate_data = df.groupby('Rate Bucket').agg({
            'N FACT': 'count',
            'Montant Ttc': lambda x: x.str.replace(',', '.').astype(float).sum(),
            'Encaissement': lambda x: x.str.replace(',', '.').astype(float).sum()
        }).reset_index()

        return rate_data.to_dict('records')


@router.post("/upload-data")
async def upload_encaissement_data(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process encaissement data"""

    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400, detail="File must be Excel or CSV")

    try:
        # Read file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            df = pd.read_excel(file.file)

        # Process data
        df = EncaissementProcessor.process_encaissement_data(df)
        df = EncaissementProcessor.calculate_encaisse_rate(df)

        # Convert to JSON for response
        result = {
            'processed_data': df.to_dict('records'),
            'overview': EncaissementProcessor.get_overview_data(df),
            'by_organisation': EncaissementProcessor.get_by_organisation_data(df),
            'by_date': EncaissementProcessor.get_by_date_data(df),
            'by_encaisse_rate': EncaissementProcessor.get_encaisse_rate_data(df)
        }

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overview data"""
    # This would typically load from database
    # For now, return sample data
    return {
        'total_organisations': 15,
        'total_factures': 1250,
        'total_montant_ttc': 1500000.00,
        'total_encaissement': 1200000.00,
        'avg_encaisse_rate': 80.5
    }


@router.get("/by-organisation")
async def get_by_organisation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by organisation"""
    # Sample data
    return [
        {
            'Org Name': 'DOT ALGER',
            'N FACT': 150,
            'Montant Ttc': 250000.00,
            'Encaissement': 200000.00,
            'Taux d\'encaissement': 80.0
        },
        {
            'Org Name': 'DOT ORAN',
            'N FACT': 120,
            'Montant Ttc': 180000.00,
            'Encaissement': 162000.00,
            'Taux d\'encaissement': 90.0
        }
    ]


@router.get("/by-date")
async def get_by_date(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by date"""
    # Sample data
    return [
        {
            'Date Fact': '2024-01',
            'N FACT': 200,
            'Montant Ttc': 300000.00,
            'Encaissement': 240000.00,
            'Taux d\'encaissement': 80.0
        },
        {
            'Date Fact': '2024-02',
            'N FACT': 180,
            'Montant Ttc': 270000.00,
            'Encaissement': 243000.00,
            'Taux d\'encaissement': 90.0
        }
    ]


@router.get("/by-encaisse-rate")
async def get_by_encaisse_rate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by encaissement rate"""
    # Sample data
    return [
        {
            'Rate Bucket': '0-25%',
            'N FACT': 50,
            'Montant Ttc': 75000.00,
            'Encaissement': 15000.00
        },
        {
            'Rate Bucket': '25-50%',
            'N FACT': 100,
            'Montant Ttc': 150000.00,
            'Encaissement': 60000.00
        },
        {
            'Rate Bucket': '50-75%',
            'N FACT': 200,
            'Montant Ttc': 300000.00,
            'Encaissement': 225000.00
        },
        {
            'Rate Bucket': '75-100%',
            'N FACT': 300,
            'Montant Ttc': 450000.00,
            'Encaissement': 405000.00
        }
    ]


@router.get("/chart-data")
async def get_chart_data(
    chart_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chart data for different visualizations"""

    if chart_type == "histogram_combined":
        # Histogramme combiné (Encaissement et Montant TTC par mois)
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'datasets': [
                {
                    'label': 'Encaissement',
                    'data': [200000, 240000, 180000, 220000, 260000, 300000],
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 1
                },
                {
                    'label': 'Montant TTC',
                    'data': [250000, 300000, 225000, 275000, 325000, 375000],
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 1
                }
            ]
        }

    elif chart_type == "pie_3d":
        # Secteur 3D (encaissement / mois)
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'datasets': [{
                'data': [200000, 240000, 180000, 220000, 260000, 300000],
                'backgroundColor': [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
                ]
            }]
        }

    elif chart_type == "histogram_dot_rate":
        # Histogramme (DOT et Taux d'encaissement)
        return {
            'labels': ['DOT ALGER', 'DOT ORAN', 'DOT CONSTANTINE', 'DOT ANNABA'],
            'datasets': [{
                'label': 'Taux d\'encaissement (%)',
                'data': [80, 90, 75, 85],
                'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            }]
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid chart type")
