"""
Report generation orchestration: builds the requested report (PDF/CSV/JSON,
in the requested category), writes it to disk under REPORTS_DIR, and
returns a `Report` ORM row ready to be persisted by the caller.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.models.audit_session import AuditSession
from app.models.compliance_result import ComplianceResult
from app.models.enums import ReportCategory, ReportType
from app.models.finding import Finding
from app.models.report import Report
from app.services.reports.csv_report import generate_findings_csv
from app.services.reports.json_report import generate_json_report
from app.services.reports.pdf_report import generate_pdf_report


def _reports_dir() -> Path:
    return Path(get_settings().sentinelai_reports_dir)


def _report_filename(audit_id: str, report_type: ReportType, category: ReportCategory) -> str:
    return f"{audit_id}_{category.value}.{report_type.value}"


def generate_report(
    db: Session,
    audit: AuditSession,
    findings: list[Finding],
    compliance_results: list[ComplianceResult],
    report_type: ReportType,
    category: ReportCategory,
    ai_summary: str | None = None,
) -> Report:
    reports_dir = _reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = _report_filename(audit.id, report_type, category)
    file_path = reports_dir / filename

    if report_type == ReportType.PDF:
        content = generate_pdf_report(audit, findings, compliance_results, category, ai_summary=ai_summary)
        file_path.write_bytes(content)
    elif report_type == ReportType.CSV:
        content = generate_findings_csv(audit, findings)
        file_path.write_text(content, encoding="utf-8")
    elif report_type == ReportType.JSON:
        content = generate_json_report(audit, findings, compliance_results)
        file_path.write_text(content, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported report type: {report_type}")

    report = Report(
        audit_session_id=audit.id,
        type=report_type,
        category=category,
        file_path=str(file_path),
    )
    db.add(report)
    db.flush()
    return report
