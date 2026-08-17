"""
Importing this package registers every ORM model against `Base.metadata`.
This is required for Alembic autogenerate and for `Base.metadata.create_all`
to see all nine tables.
"""

from app.models.ai_message import AiMessage
from app.models.audit_session import AuditSession
from app.models.aws_account import AwsAccount
from app.models.compliance_result import ComplianceResult
from app.models.finding import Finding
from app.models.report import Report
from app.models.risk_score import RiskScore
from app.models.settings import UserSettings
from app.models.user import User

__all__ = [
    "AiMessage",
    "AuditSession",
    "AwsAccount",
    "ComplianceResult",
    "Finding",
    "Report",
    "RiskScore",
    "UserSettings",
    "User",
]
