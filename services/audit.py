from sqlalchemy.orm import Session
from models import AuditLog
from fastapi import Request
from typing import Optional


class AuditService:
    """Service for logging audit trails of important actions"""
    
    @staticmethod
    def log(
        db: Session,
        request: Request,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        details: Optional[str] = None,
        trip_id: Optional[int] = None
    ):
        """
        Log an audit event
        
        Args:
            db: Database session
            request: FastAPI request object
            action: Action performed (created, updated, deleted, etc.)
            entity_type: Type of entity (deposit, expense, crew_member, etc.)
            entity_id: ID of the affected entity
            details: Additional details about the action
            trip_id: ID of the trip if applicable
        """
        user_id = request.session.get("user_id")
        ip_address = request.client.host if request.client else None
        
        audit_log = AuditLog(
            trip_id=trip_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )
        
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def get_logs(
        db: Session,
        trip_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        limit: int = 100
    ):
        """
        Retrieve audit logs with optional filtering
        
        Args:
            db: Database session
            trip_id: Filter by trip ID
            entity_type: Filter by entity type
            limit: Maximum number of logs to retrieve
        
        Returns:
            List of audit log entries
        """
        query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
        
        if trip_id:
            query = query.filter(AuditLog.trip_id == trip_id)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        
        return query.limit(limit).all()
