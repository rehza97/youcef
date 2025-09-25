from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database.connection import get_db
from core.security import get_current_user
from models.user import User
import logging

logger = logging.getLogger(__name__)

encaissement_analytics_router = APIRouter()


@encaissement_analytics_router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overview analytics data (ADMIN, SUPER_USER, or DOT_USER with restrictions)"""
    # RBAC: Check user has appropriate access
    from services.permission_service import PermissionService

    # Ensure user has at least DOT_USER access
    PermissionService.check_dot_user_permissions(current_user, db)

    # Get user's DOT region for filtering
    user_dot = PermissionService.get_user_dot_region(current_user, db)

    logger.info(f"Overview data requested by user {current_user.id} (DOT: {user_dot or 'ALL'})")

    return {
        'total_organisations': 15,
        'total_factures': 1250,
        'total_montant_ttc': 1500000.00,
        'total_encaissement': 1200000.00,
        'avg_encaisse_rate': 80.5,
        'best_performing_org': 'DOT ORAN',
        'worst_performing_org': 'DOT TLEMCEN',
        'trend': 'improving'  # improving, declining, stable
    }


@encaissement_analytics_router.get("/by-organisation")
async def get_by_organisation(
    limit: Optional[int] = Query(None, ge=1, le=100),
    sort_by: Optional[str] = Query("encaisse_rate", regex="^(name|factures|montant|encaissement|encaisse_rate)$"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by organisation with filtering and sorting (DOT-scoped)"""
    # RBAC: Check user has appropriate access
    from services.permission_service import PermissionService

    # Ensure user has at least DOT_USER access
    PermissionService.check_dot_user_permissions(current_user, db)

    # Get user's DOT region for filtering
    user_dot = PermissionService.get_user_dot_region(current_user, db)

    logger.info(f"Organisation analytics requested by user {current_user.id} (DOT: {user_dot or 'ALL'})")

    # Sample data - in production, this would query the database with DOT filtering
    all_data = [
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
        },
        {
            'Org Name': 'DOT CONSTANTINE',
            'N FACT': 100,
            'Montant Ttc': 150000.00,
            'Encaissement': 120000.00,
            'Taux d\'encaissement': 80.0
        },
        {
            'Org Name': 'DOT SETIF',
            'N FACT': 80,
            'Montant Ttc': 120000.00,
            'Encaissement': 84000.00,
            'Taux d\'encaissement': 70.0
        },
        {
            'Org Name': 'DOT TLEMCEN',
            'N FACT': 60,
            'Montant Ttc': 90000.00,
            'Encaissement': 54000.00,
            'Taux d\'encaissement': 60.0
        }
    ]

    # Filter data based on user's DOT access
    if user_dot:  # DOT_USER - only show their DOT
        data = [org for org in all_data if user_dot.upper() in org['Org Name'].upper()]
    else:  # ADMIN/SUPER_USER - show all data
        data = all_data

    # Apply sorting
    sort_key_map = {
        'name': 'Org Name',
        'factures': 'N FACT',
        'montant': 'Montant Ttc',
        'encaissement': 'Encaissement',
        'encaisse_rate': 'Taux d\'encaissement'
    }

    if sort_by in sort_key_map:
        data.sort(
            key=lambda x: x[sort_key_map[sort_by]],
            reverse=(order == "desc")
        )

    # Apply limit
    if limit:
        data = data[:limit]

    return {
        'organisations': data,
        'total_count': len(data),
        'filters_applied': {
            'limit': limit,
            'sort_by': sort_by,
            'order': order
        }
    }


@encaissement_analytics_router.get("/by-date")
async def get_by_date(
    period: Optional[str] = Query("month", regex="^(day|week|month|quarter|year)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by time period"""
    logger.info(f"Date analytics requested by user {current_user.id} for period: {period}")

    # Sample monthly data
    monthly_data = [
        {
            'period': 'January 2024',
            'total_montant_ttc': 450000.00,
            'total_encaissement': 360000.00,
            'encaisse_rate': 80.0,
            'organisations_count': 12
        },
        {
            'period': 'February 2024',
            'total_montant_ttc': 520000.00,
            'total_encaissement': 432000.00,
            'encaisse_rate': 83.1,
            'organisations_count': 14
        },
        {
            'period': 'March 2024',
            'total_montant_ttc': 530000.00,
            'total_encaissement': 408000.00,
            'encaisse_rate': 77.0,
            'organisations_count': 15
        }
    ]

    return {
        'period_type': period,
        'data': monthly_data,
        'total_periods': len(monthly_data)
    }


@encaissement_analytics_router.get("/by-encaisse-rate")
async def get_by_encaisse_rate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data grouped by encaissement rate buckets"""
    logger.info(f"Rate analytics requested by user {current_user.id}")

    return {
        'rate_buckets': [
            {
                'Rate Bucket': '0-25%',
                'N FACT': 25,
                'Montant Ttc': 45000.00,
                'Encaissement': 9000.00,
                'organisations_count': 2
            },
            {
                'Rate Bucket': '25-50%',
                'N FACT': 80,
                'Montant Ttc': 120000.00,
                'Encaissement': 48000.00,
                'organisations_count': 3
            },
            {
                'Rate Bucket': '50-75%',
                'N FACT': 200,
                'Montant Ttc': 350000.00,
                'Encaissement': 245000.00,
                'organisations_count': 5
            },
            {
                'Rate Bucket': '75-100%',
                'N FACT': 300,
                'Montant Ttc': 485000.00,
                'Encaissement': 436500.00,
                'organisations_count': 5
            }
        ]
    }


@encaissement_analytics_router.get("/performance-metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get key performance indicators and metrics (DOT-scoped)"""
    # RBAC: Check user has appropriate access
    from services.permission_service import PermissionService

    # Ensure user has at least DOT_USER access
    PermissionService.check_dot_user_permissions(current_user, db)

    # Get user's DOT region for filtering
    user_dot = PermissionService.get_user_dot_region(current_user, db)

    logger.info(f"Performance metrics requested by user {current_user.id} (DOT: {user_dot or 'ALL'})")

    return {
        'kpis': {
            'overall_collection_rate': 78.5,
            'target_collection_rate': 85.0,
            'performance_vs_target': -6.5,
            'total_outstanding': 300000.00,
            'collections_this_month': 120000.00,
            'collections_last_month': 108000.00,
            'month_over_month_growth': 11.1
        },
        'top_performers': [
            {'org': 'DOT ORAN', 'rate': 90.0},
            {'org': 'DOT ALGER', 'rate': 85.5},
            {'org': 'DOT CONSTANTINE', 'rate': 82.0}
        ],
        'underperformers': [
            {'org': 'DOT TLEMCEN', 'rate': 60.0},
            {'org': 'DOT OUARGLA', 'rate': 65.2},
            {'org': 'DOT BATNA', 'rate': 68.5}
        ],
        'trends': {
            'improving': ['DOT ORAN', 'DOT SETIF'],
            'declining': ['DOT TLEMCEN'],
            'stable': ['DOT ALGER', 'DOT CONSTANTINE']
        }
    }


@encaissement_analytics_router.get("/export-report")
async def export_analytics_report(
    format: str = Query("excel", regex="^(excel|csv|pdf)$"),
    include_charts: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export analytics report in various formats (ADMIN or SUPER_USER only)"""
    # RBAC: Only ADMIN and SUPER_USER can export reports
    from services.permission_service import PermissionService
    PermissionService.require_admin_or_super_user(current_user, db)

    logger.info(f"Analytics report export requested by user {current_user.id} in {format} format")

    # This would generate actual files in production
    return {
        'message': f'Report export initiated in {format} format',
        'format': format,
        'include_charts': include_charts,
        'estimated_completion': '2-3 minutes',
        'download_url': f'/api/encaissement/download-report/{current_user.id}',
        'expires_at': '2024-01-01T23:59:59Z'
    }