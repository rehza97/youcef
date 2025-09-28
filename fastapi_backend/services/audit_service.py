import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base
from models.user import User

logger = logging.getLogger(__name__)

class AuditLog(Base):
    """Audit log model for tracking security-relevant activities"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for system actions
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    additional_data = Column(JSON, nullable=True)
    severity = Column(String(20), default="info")  # info, warning, error, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")

class SecurityIncident(Base):
    """Security incident tracking"""
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_type = Column(String(50), nullable=False)  # unauthorized_access, malware_detected, etc.
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    description = Column(Text, nullable=False)
    incident_data = Column(JSON, nullable=True)
    status = Column(String(20), default="open")  # open, investigating, resolved, closed
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")

class AuditService:
    """Service for security audit logging and incident tracking"""

    # Critical actions that should always be logged
    CRITICAL_ACTIONS = {
        'login_failed',
        'login_success',
        'password_changed',
        'user_created',
        'user_deleted',
        'permission_changed',
        'file_uploaded',
        'file_downloaded',
        'file_deleted',
        'conversation_created',
        'message_sent',
        'admin_action'
    }

    # Actions that indicate potential security incidents
    SUSPICIOUS_ACTIONS = {
        'multiple_login_failures',
        'unauthorized_access_attempt',
        'malware_detected',
        'path_traversal_attempt',
        'injection_attempt',
        'rate_limit_exceeded'
    }

    def log_activity(
        self,
        db: Session,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info"
    ) -> Optional[AuditLog]:
        """Log security-relevant activity"""
        try:
            # Determine severity based on action
            if action in self.SUSPICIOUS_ACTIONS:
                severity = "warning"
            elif action in self.CRITICAL_ACTIONS:
                severity = "info"

            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                details=details,
                additional_data=additional_data,
                severity=severity,
                created_at=datetime.utcnow()
            )

            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)

            # Check for suspicious patterns
            self._check_for_suspicious_patterns(db, user_id, action, ip_address)

            logger.info(f"Audit log created: {action} by user {user_id}")
            return audit_log

        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            db.rollback()
            return None

    def log_security_incident(
        self,
        db: Session,
        incident_type: str,
        description: str,
        severity: str = "medium",
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        incident_data: Optional[Dict[str, Any]] = None
    ) -> Optional[SecurityIncident]:
        """Log security incident"""
        try:
            incident = SecurityIncident(
                incident_type=incident_type,
                severity=severity,
                user_id=user_id,
                ip_address=ip_address,
                description=description,
                incident_data=incident_data,
                status="open",
                created_at=datetime.utcnow()
            )

            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Also create audit log for the incident
            self.log_activity(
                db=db,
                user_id=user_id,
                action="security_incident",
                resource_type="security",
                resource_id=incident.id,
                details=f"Security incident: {incident_type}",
                additional_data={"severity": severity, "incident_id": incident.id},
                ip_address=ip_address,
                severity="error"
            )

            logger.error(f"Security incident logged: {incident_type} (ID: {incident.id})")
            return incident

        except Exception as e:
            logger.error(f"Error logging security incident: {e}")
            db.rollback()
            return None

    def _check_for_suspicious_patterns(
        self,
        db: Session,
        user_id: Optional[int],
        action: str,
        ip_address: Optional[str]
    ):
        """Check for suspicious activity patterns"""
        try:
            current_time = datetime.utcnow()

            # Check for multiple login failures
            if action == "login_failed" and user_id:
                recent_failures = db.query(AuditLog).filter(
                    AuditLog.user_id == user_id,
                    AuditLog.action == "login_failed",
                    AuditLog.created_at >= current_time - timedelta(minutes=15)
                ).count()

                if recent_failures >= 5:
                    self.log_security_incident(
                        db=db,
                        incident_type="multiple_login_failures",
                        description=f"User {user_id} had {recent_failures} login failures in 15 minutes",
                        severity="high",
                        user_id=user_id,
                        ip_address=ip_address,
                        incident_data={"failure_count": recent_failures}
                    )

            # Check for excessive file downloads from same IP
            if action == "file_downloaded" and ip_address:
                recent_downloads = db.query(AuditLog).filter(
                    AuditLog.action == "file_downloaded",
                    AuditLog.ip_address == ip_address,
                    AuditLog.created_at >= current_time - timedelta(minutes=10)
                ).count()

                if recent_downloads >= 20:
                    self.log_security_incident(
                        db=db,
                        incident_type="excessive_file_access",
                        description=f"IP {ip_address} downloaded {recent_downloads} files in 10 minutes",
                        severity="medium",
                        ip_address=ip_address,
                        incident_data={"download_count": recent_downloads}
                    )

        except Exception as e:
            logger.error(f"Error checking suspicious patterns: {e}")

    def get_user_activity_logs(
        self,
        db: Session,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        action_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Get activity logs for a specific user"""
        try:
            query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

            if action_filter:
                query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))

            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)

            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting user activity logs: {e}")
            return []

    def get_security_incidents(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        severity_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        incident_type_filter: Optional[str] = None
    ) -> List[SecurityIncident]:
        """Get security incidents"""
        try:
            query = db.query(SecurityIncident)

            if severity_filter:
                query = query.filter(SecurityIncident.severity == severity_filter)

            if status_filter:
                query = query.filter(SecurityIncident.status == status_filter)

            if incident_type_filter:
                query = query.filter(SecurityIncident.incident_type.ilike(f"%{incident_type_filter}%"))

            return query.order_by(SecurityIncident.created_at.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting security incidents: {e}")
            return []

    def resolve_security_incident(
        self,
        db: Session,
        incident_id: int,
        resolved_by_user_id: int,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve a security incident"""
        try:
            incident = db.query(SecurityIncident).filter(SecurityIncident.id == incident_id).first()
            if not incident:
                return False

            incident.status = "resolved"
            incident.resolved_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()

            if resolution_notes:
                if not incident.incident_data:
                    incident.incident_data = {}
                incident.incident_data['resolution_notes'] = resolution_notes
                incident.incident_data['resolved_by'] = resolved_by_user_id

            db.commit()

            # Log the resolution
            self.log_activity(
                db=db,
                user_id=resolved_by_user_id,
                action="incident_resolved",
                resource_type="security",
                resource_id=incident_id,
                details=f"Resolved security incident: {incident.incident_type}",
                severity="info"
            )

            return True

        except Exception as e:
            logger.error(f"Error resolving security incident: {e}")
            db.rollback()
            return False

    def get_activity_summary(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get summary of activities for dashboard"""
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()

            # Get total activities
            total_activities = db.query(AuditLog).filter(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).count()

            # Get activities by severity
            severity_counts = db.query(
                AuditLog.severity,
                func.count(AuditLog.id)
            ).filter(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).group_by(AuditLog.severity).all()

            # Get top actions
            top_actions = db.query(
                AuditLog.action,
                func.count(AuditLog.id)
            ).filter(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc()).limit(10).all()

            # Get open incidents
            open_incidents = db.query(SecurityIncident).filter(
                SecurityIncident.status.in_(["open", "investigating"])
            ).count()

            return {
                "total_activities": total_activities,
                "severity_breakdown": {severity: count for severity, count in severity_counts},
                "top_actions": {action: count for action, count in top_actions},
                "open_incidents": open_incidents,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return {}

    def cleanup_old_logs(
        self,
        db: Session,
        retention_days: int = 90
    ) -> int:
        """Clean up old audit logs"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old logs (keep critical actions longer)
            deleted_count = db.query(AuditLog).filter(
                and_(
                    AuditLog.created_at < cutoff_date,
                    AuditLog.severity.in_(["info"]),  # Only delete info level logs
                    ~AuditLog.action.in_(self.CRITICAL_ACTIONS)  # Keep critical actions
                )
            ).delete()

            db.commit()

            logger.info(f"Cleaned up {deleted_count} old audit logs")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            db.rollback()
            return 0

# Global instance
audit_service = AuditService()