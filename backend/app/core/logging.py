"""
Q-Shield Logging Module
Structured JSON logging with audit trail support.
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager
import uuid

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class QShieldJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with Q-Shield specific fields."""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        super().add_fields(log_record, record, message_dict)
        
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["service"] = settings.APP_NAME
        log_record["version"] = settings.APP_VERSION
        log_record["environment"] = settings.ENVIRONMENT
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }


class AuditLogger:
    """
    Tamper-evident audit logger for security events.
    Implements append-only logging with integrity verification.
    """
    
    def __init__(self, log_path: str = None):
        self.log_path = Path(log_path or settings.AUDIT_LOG_PATH)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("qshield.audit")
        self._setup_handler()
    
    def _setup_handler(self):
        """Setup file handler for audit logs."""
        handler = logging.FileHandler(self.log_path, mode='a')
        handler.setFormatter(QShieldJsonFormatter())
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
    
    def _compute_hash(self, event: dict) -> str:
        """Compute SHA-256 hash of event for integrity."""
        import hashlib
        event_str = json.dumps(event, sort_keys=True, default=str)
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    def log_event(
        self,
        event_type: str,
        actor: str,
        resource: str,
        action: str,
        outcome: str,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
    ):
        """
        Log an audit event with tamper-evident fields.
        
        Args:
            event_type: Category of event (auth, scan, certificate, etc.)
            actor: User or system performing the action
            resource: Resource being acted upon
            action: Action being performed
            outcome: success, failure, or denied
            details: Additional event-specific details
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for the request
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "resource": resource,
            "action": action,
            "outcome": outcome,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "details": details or {},
        }
        
        # Add integrity hash
        event["integrity_hash"] = self._compute_hash(event)
        
        self._logger.info(
            json.dumps(event, default=str),
            extra=event
        )
        
        return event["event_id"]
    
    def log_authentication(
        self,
        user: str,
        method: str,
        outcome: str,
        ip_address: str = None,
        details: dict = None,
    ):
        """Log authentication event."""
        return self.log_event(
            event_type="authentication",
            actor=user,
            resource="auth/session",
            action=method,
            outcome=outcome,
            ip_address=ip_address,
            details=details,
        )
    
    def log_scan(
        self,
        user: str,
        target: str,
        scan_type: str,
        outcome: str,
        details: dict = None,
    ):
        """Log scanning event."""
        return self.log_event(
            event_type="scan",
            actor=user,
            resource=target,
            action=scan_type,
            outcome=outcome,
            details=details,
        )
    
    def log_certificate(
        self,
        user: str,
        certificate_id: str,
        action: str,
        outcome: str,
        details: dict = None,
    ):
        """Log certificate-related event."""
        return self.log_event(
            event_type="certificate",
            actor=user,
            resource=f"cert/{certificate_id}",
            action=action,
            outcome=outcome,
            details=details,
        )
    
    def log_data_access(
        self,
        user: str,
        resource: str,
        action: str,
        outcome: str,
        details: dict = None,
    ):
        """Log data access event."""
        return self.log_event(
            event_type="data_access",
            actor=user,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details,
        )


def setup_logging():
    """Configure application-wide logging."""
    
    # Create formatter
    if settings.LOG_FORMAT == "json":
        formatter = QShieldJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (if configured)
    handlers = [console_handler]
    if settings.LOG_FILE_PATH:
        log_path = Path(settings.LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DATABASE_ECHO else logging.WARNING
    )
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(f"qshield.{name}")


# Context manager for request-scoped logging
class RequestContext:
    """Request-scoped logging context."""
    
    _current: Optional["RequestContext"] = None
    
    def __init__(
        self,
        request_id: str = None,
        user_id: str = None,
        ip_address: str = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.ip_address = ip_address
        self.start_time = datetime.now(timezone.utc)
    
    @classmethod
    def get_current(cls) -> Optional["RequestContext"]:
        return cls._current
    
    def __enter__(self):
        RequestContext._current = self
        return self
    
    def __exit__(self, *args):
        RequestContext._current = None


@contextmanager
def request_context(
    request_id: str = None,
    user_id: str = None,
    ip_address: str = None,
):
    """Context manager for request-scoped logging."""
    ctx = RequestContext(request_id, user_id, ip_address)
    try:
        yield ctx
    finally:
        pass


# Initialize audit logger
audit_logger = AuditLogger()
