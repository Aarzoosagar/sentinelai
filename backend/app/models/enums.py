"""Shared enumerations used by multiple ORM models."""

import enum


class AwsAuthMethod(str, enum.Enum):
    ASSUME_ROLE = "assume_role"
    ACCESS_KEY = "access_key"


class AccountValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


class AuditStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AwsService(str, enum.Enum):
    IAM = "iam"
    S3 = "s3"
    EC2 = "ec2"
    CLOUDTRAIL = "cloudtrail"
    CLOUDWATCH = "cloudwatch"
    LAMBDA = "lambda"
    RDS = "rds"
    KMS = "kms"
    SECRETS_MANAGER = "secrets_manager"


class ComplianceFramework(str, enum.Enum):
    CIS_AWS_FOUNDATIONS = "cis_aws_foundations"
    AWS_WELL_ARCHITECTED = "aws_well_architected"
    NIST_CSF = "nist_csf"
    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"


class ComplianceStatus(str, enum.Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class ReportType(str, enum.Enum):
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class ReportCategory(str, enum.Enum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    RISK = "risk"
    AUDIT_HISTORY = "audit_history"


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
