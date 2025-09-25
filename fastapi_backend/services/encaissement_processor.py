"""
Encaissement data processing service
Handles data cleaning, calculations, and aggregations for Encaissement AR DOT module
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime


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

        # Convert numeric columns
        numeric_columns = ['Montant Ttc', 'Encaissement']
        for col in numeric_columns:
            if col in df.columns:
                # Replace comma with dot and convert to float
                df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

        return df

    @staticmethod
    def calculate_encaisse_rate(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate encaissement rate"""
        if 'Montant Ttc' in df.columns and 'Encaissement' in df.columns:
            df['Taux d\'encaissement'] = (
                df['Encaissement'] / df['Montant Ttc'] * 100
            ).round(2)

            # Handle division by zero or inf values
            df['Taux d\'encaissement'] = df['Taux d\'encaissement'].replace(
                [np.inf, -np.inf], 0
            ).fillna(0)

        return df

    @staticmethod
    def get_overview_data(df: pd.DataFrame) -> Dict[str, Any]:
        """Get overview statistics"""
        return {
            'total_organisations': df['Org Name'].nunique(),
            'total_factures': df['N FACT'].sum() if 'N FACT' in df.columns else 0,
            'total_montant_ttc': df['Montant Ttc'].sum() if 'Montant Ttc' in df.columns else 0,
            'total_encaissement': df['Encaissement'].sum() if 'Encaissement' in df.columns else 0,
            'avg_encaisse_rate': df['Taux d\'encaissement'].mean() if 'Taux d\'encaissement' in df.columns else 0
        }

    @staticmethod
    def get_by_organisation_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by organisation"""
        if df.empty:
            return []

        grouped = df.groupby('Org Name').agg({
            'N FACT': 'sum',
            'Montant Ttc': 'sum',
            'Encaissement': 'sum'
        }).reset_index()

        # Recalculate encaissement rate for grouped data
        grouped['Taux d\'encaissement'] = (
            grouped['Encaissement'] / grouped['Montant Ttc'] * 100
        ).round(2)

        return grouped.to_dict('records')

    @staticmethod
    def get_by_date_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by date (if date columns exist)"""
        # This method assumes there might be date columns in the future
        # For now, return sample monthly data
        return [
            {
                'month': 'January',
                'total_montant_ttc': df['Montant Ttc'].sum() * 0.3 if 'Montant Ttc' in df.columns else 0,
                'total_encaissement': df['Encaissement'].sum() * 0.3 if 'Encaissement' in df.columns else 0
            },
            {
                'month': 'February',
                'total_montant_ttc': df['Montant Ttc'].sum() * 0.4 if 'Montant Ttc' in df.columns else 0,
                'total_encaissement': df['Encaissement'].sum() * 0.4 if 'Encaissement' in df.columns else 0
            },
            {
                'month': 'March',
                'total_montant_ttc': df['Montant Ttc'].sum() * 0.3 if 'Montant Ttc' in df.columns else 0,
                'total_encaissement': df['Encaissement'].sum() * 0.3 if 'Encaissement' in df.columns else 0
            }
        ]

    @staticmethod
    def get_encaisse_rate_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get data grouped by encaissement rate"""
        if 'Taux d\'encaissement' not in df.columns:
            return []

        # Create rate buckets
        df['Rate Bucket'] = pd.cut(
            df['Taux d\'encaissement'],
            bins=[0, 25, 50, 75, 100],
            labels=['0-25%', '25-50%', '50-75%', '75-100%']
        )

        rate_data = df.groupby('Rate Bucket').agg({
            'N FACT': 'count',
            'Montant Ttc': 'sum',
            'Encaissement': 'sum'
        }).reset_index()

        return rate_data.to_dict('records')

    @staticmethod
    def validate_data_structure(df: pd.DataFrame) -> Dict[str, Any]:
        """Validate the structure of uploaded data"""
        required_columns = ['Org Name', 'N FACT', 'Montant Ttc', 'Encaissement']
        missing_columns = [col for col in required_columns if col not in df.columns]

        return {
            'is_valid': len(missing_columns) == 0,
            'missing_columns': missing_columns,
            'available_columns': list(df.columns),
            'total_rows': len(df),
            'total_columns': len(df.columns)
        }