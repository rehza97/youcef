"""
KPI Cache Service - Fast cached analytics for dashboard
Caches expensive KPI calculations to avoid real-time computation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import hashlib

from models.park import Park
from models.dot import DOT
from services.dot_service import DOTService

logger = logging.getLogger(__name__)


class KPICacheService:
    """High-performance KPI caching service"""

    def __init__(self):
        # In-memory cache (can be replaced with Redis)
        self._cache = {}
        self._cache_ttl = {}
        self.default_ttl = 300  # 5 minutes

    def _get_cache_key(self, user_id: int, endpoint: str, **kwargs) -> str:
        """Generate cache key for user + endpoint + parameters"""
        key_data = f"{user_id}:{endpoint}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache:
            return False

        if cache_key not in self._cache_ttl:
            return False

        return datetime.utcnow() < self._cache_ttl[cache_key]

    def _set_cache(self, cache_key: str, data: Any, ttl_seconds: int = None):
        """Set cache entry with TTL"""
        ttl = ttl_seconds or self.default_ttl
        self._cache[cache_key] = data
        self._cache_ttl[cache_key] = datetime.utcnow() + timedelta(seconds=ttl)

    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Get cache entry if valid"""
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        return None

    def get_overview_analytics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get cached overview analytics"""
        cache_key = self._get_cache_key(user_id, "overview")

        # Check cache first
        cached_data = self._get_cache(cache_key)
        if cached_data:
            logger.debug(f"✅ KPI cache HIT for overview (user {user_id})")
            return cached_data

        logger.debug(
            f"🔄 KPI cache MISS for overview (user {user_id}) - computing...")

        # Compute fresh data
        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id)

        if not accessible_dots:
            result = {
                "total_active_subscribers": 0,
                "total_dots": 0,
                "recent_activity": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        else:
            # ✅ OPTIMIZED: Use indexed queries
            base_query = db.query(Park).filter(
                Park.dot_id.in_(accessible_dots))

            # Total active subscribers (uses idx_parks_subscriber_status)
            total_active = base_query.filter(
                Park.subscriber_status.in_(["Active", "ACTIVE", "active"])
            ).count()

            # Recent activity (uses idx_parks_created_at)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_activity = base_query.filter(
                Park.created_at >= seven_days_ago
            ).count()

            result = {
                "total_active_subscribers": total_active,
                "total_dots": len(accessible_dots),
                "recent_activity": recent_activity,
                "last_updated": datetime.utcnow().isoformat()
            }

        # Cache for 5 minutes
        self._set_cache(cache_key, result, 300)
        return result

    def get_telecom_type_distribution(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get cached telecom type distribution"""
        cache_key = self._get_cache_key(user_id, "telecom_type")

        cached_data = self._get_cache(cache_key)
        if cached_data:
            logger.debug(f"✅ KPI cache HIT for telecom_type (user {user_id})")
            return cached_data

        logger.debug(
            f"🔄 KPI cache MISS for telecom_type (user {user_id}) - computing...")

        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id)

        if not accessible_dots:
            result = {"distribution": [], "total": 0}
        else:
            # ✅ OPTIMIZED: Single query with GROUP BY (uses idx_parks_telecom_type)
            distribution = db.query(
                Park.telecom_type,
                func.count(Park.id).label('count')
            ).filter(
                Park.dot_id.in_(accessible_dots),
                Park.telecom_type.isnot(None)
            ).group_by(Park.telecom_type).order_by(func.count(Park.id).desc()).all()

            total_count = sum([item.count for item in distribution])

            result = {
                "distribution": [
                    {
                        "type": item.telecom_type,
                        "count": item.count,
                        "percentage": round((item.count / total_count * 100), 2) if total_count > 0 else 0
                    }
                    for item in distribution
                ],
                "total": total_count
            }

        # Cache for 10 minutes (less frequently changing)
        self._set_cache(cache_key, result, 600)
        return result

    def get_subscriber_status_distribution(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get cached subscriber status distribution"""
        cache_key = self._get_cache_key(user_id, "subscriber_status")

        cached_data = self._get_cache(cache_key)
        if cached_data:
            logger.debug(
                f"✅ KPI cache HIT for subscriber_status (user {user_id})")
            return cached_data

        logger.debug(
            f"🔄 KPI cache MISS for subscriber_status (user {user_id}) - computing...")

        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id)

        if not accessible_dots:
            result = {"distribution": [], "total": 0}
        else:
            # ✅ OPTIMIZED: Single query with GROUP BY (uses idx_parks_subscriber_status)
            distribution = db.query(
                Park.subscriber_status,
                func.count(Park.id).label('count')
            ).filter(
                Park.dot_id.in_(accessible_dots),
                Park.subscriber_status.isnot(None)
            ).group_by(Park.subscriber_status).order_by(func.count(Park.id).desc()).all()

            total_count = sum([item.count for item in distribution])

            result = {
                "distribution": [
                    {
                        "status": item.subscriber_status,
                        "count": item.count,
                        "percentage": round((item.count / total_count * 100), 2) if total_count > 0 else 0
                    }
                    for item in distribution
                ],
                "total": total_count
            }

        # Cache for 10 minutes
        self._set_cache(cache_key, result, 600)
        return result

    def get_customer_l2_distribution(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get cached customer L2 distribution"""
        cache_key = self._get_cache_key(user_id, "customer_l2")

        cached_data = self._get_cache(cache_key)
        if cached_data:
            logger.debug(f"✅ KPI cache HIT for customer_l2 (user {user_id})")
            return cached_data

        logger.debug(
            f"🔄 KPI cache MISS for customer_l2 (user {user_id}) - computing...")

        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id)

        if not accessible_dots:
            result = {"distribution": [], "total": 0}
        else:
            # ✅ OPTIMIZED: Single query with GROUP BY (uses idx_parks_customer_l2)
            distribution = db.query(
                Park.customer_l2_code,
                Park.customer_l2_description,
                func.count(Park.id).label('count')
            ).filter(
                Park.dot_id.in_(accessible_dots),
                Park.customer_l2_code.isnot(None)
            ).group_by(Park.customer_l2_code, Park.customer_l2_description).order_by(func.count(Park.id).desc()).all()

            total_count = sum([item.count for item in distribution])

            result = {
                "distribution": [
                    {
                        "code": item.customer_l2_code,
                        "description": item.customer_l2_description,
                        "count": item.count,
                        "percentage": round((item.count / total_count * 100), 2) if total_count > 0 else 0
                    }
                    for item in distribution
                ],
                "total": total_count
            }

        # Cache for 15 minutes (changes less frequently)
        self._set_cache(cache_key, result, 900)
        return result

    def get_customer_l3_distribution(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get cached customer L3 distribution"""
        cache_key = self._get_cache_key(user_id, "customer_l3")

        cached_data = self._get_cache(cache_key)
        if cached_data:
            logger.debug(f"✅ KPI cache HIT for customer_l3 (user {user_id})")
            return cached_data

        logger.debug(
            f"🔄 KPI cache MISS for customer_l3 (user {user_id}) - computing...")

        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=user_id)

        if not accessible_dots:
            result = {"distribution": [], "total": 0}
        else:
            # ✅ OPTIMIZED: Single query with GROUP BY (uses idx_parks_customer_l3)
            distribution = db.query(
                Park.customer_l3_code,
                Park.customer_l3_description,
                func.count(Park.id).label('count')
            ).filter(
                Park.dot_id.in_(accessible_dots),
                Park.customer_l3_code.isnot(None)
            ).group_by(Park.customer_l3_code, Park.customer_l3_description).order_by(func.count(Park.id).desc()).all()

            total_count = sum([item.count for item in distribution])

            result = {
                "distribution": [
                    {
                        "code": item.customer_l3_code,
                        "description": item.customer_l3_description,
                        "count": item.count,
                        "percentage": round((item.count / total_count * 100), 2) if total_count > 0 else 0
                    }
                    for item in distribution
                ],
                "total": total_count
            }

        # Cache for 15 minutes (changes less frequently)
        self._set_cache(cache_key, result, 900)
        return result

    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user"""
        keys_to_remove = [key for key in self._cache.keys()
                          if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
        logger.info(
            f"🗑️ Invalidated {len(keys_to_remove)} cache entries for user {user_id}")

    def invalidate_all_cache(self):
        """Invalidate all cache entries"""
        self._cache.clear()
        self._cache_ttl.clear()
        logger.info("🗑️ Invalidated all KPI cache entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_entries = sum(1 for key in self._cache.keys()
                            if self._is_cache_valid(key))
        total_entries = len(self._cache)

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "cache_hit_ratio": "N/A"  # Would need hit/miss tracking
        }


# Global instance
kpi_cache_service = KPICacheService()
