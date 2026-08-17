"""
PDF report generation via ReportLab.

Produces a styled PDF matching the dark-enterprise brand described in the
project spec (rendered in print-safe light colors, since PDF output is
always printed/viewed on white by convention — the SaaS UI itself stays
dark-mode-only per spec). Supports the five report categories: Executive,
Technical, Compliance, Risk, and Audit History.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.audit_session import AuditSession
from app.models.compliance_result import ComplianceResult
from app.models.enums import ComplianceStatus, ReportCategory, Severity
from app.models.finding import Finding

_BRAND_BLUE = colors.HexColor("#3B82F6")
_SEVERITY_COLORS = {
    Severity.CRITICAL: colors.HexColor("#EF4444"),
    Severity.HIGH: colors.HexColor("#F59E0B"),
    Severity.MEDIUM: colors.HexColor("#EAB308"),
    Severity.LOW: colors.HexColor("#10B981"),
    Severity.INFORMATIONAL: colors.HexColor("#6B7280"),
}
_COMPLIANCE_COLORS = {
    ComplianceStatus.PASS: colors.HexColor("#10B981"),
    ComplianceStatus.WARNING: colors.HexColor("#F59E0B"),
    ComplianceStatus.FAIL: colors.HexColor("#EF4444"),
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SentinelTitle", fontSize=22, leading=26, textColor=_BRAND_BLUE,
            spaceAfter=4, fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="SentinelSubtitle", fontSize=11, leading=14, textColor=colors.HexColor("#6B7280"),
            spaceAfter=20,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SentinelSectionHeading", fontSize=14, leading=18, textColor=colors.HexColor("#111111"),
            spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold",
        )
    )
    return styles


def _header(styles, audit: AuditSession, category: ReportCategory) -> list:
    title_map = {
        ReportCategory.EXECUTIVE: "Executive Security Report",
        ReportCategory.TECHNICAL: "Technical Security Report",
        ReportCategory.COMPLIANCE: "Compliance Report",
        ReportCategory.RISK: "Risk Report",
        ReportCategory.AUDIT_HISTORY: "Audit History Report",
    }
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    elements = [
        Paragraph("SentinelAI", styles["SentinelTitle"]),
        Paragraph(title_map[category], styles["Heading2"]),
        Paragraph(
            f"Audit ID: {audit.id} &nbsp;|&nbsp; Generated: {generated_at} &nbsp;|&nbsp; "
            f"Security Score: {audit.security_score if audit.security_score is not None else 'N/A'}/100",
            styles["SentinelSubtitle"],
        ),
        Spacer(1, 0.1 * inch),
    ]
    return elements


def _findings_table(findings: list[Finding], styles, max_rows: int | None = None) -> Table:
    header = ["Severity", "Service", "Title", "Resource", "CIS Control"]
    rows = [header]
    shown = findings[:max_rows] if max_rows else findings
    for f in shown:
        rows.append(
            [
                f.severity.value.upper(),
                Paragraph(f.service.value.upper(), styles["BodyText"]),
                Paragraph(f.title, styles["BodyText"]),
                f.resource_id or "-",
                f.cis_control or "-",
            ]
        )

    table = Table(rows, colWidths=[0.75 * inch, 0.95 * inch, 2.35 * inch, 1.3 * inch, 0.85 * inch], repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ]
    for i, f in enumerate(shown, start=1):
        style_commands.append(("TEXTCOLOR", (0, i), (0, i), _SEVERITY_COLORS[f.severity]))
        style_commands.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style_commands))
    return table


def _compliance_table(results: list[ComplianceResult], styles) -> Table:
    header = ["Framework", "Control", "Title", "Status"]
    rows = [header]
    for r in results:
        rows.append(
            [
                Paragraph(r.framework.value.replace("_", " ").upper(), styles["BodyText"]),
                r.control_id,
                Paragraph(r.control_title, styles["BodyText"]),
                r.status.value.upper(),
            ]
        )
    table = Table(rows, colWidths=[1.5 * inch, 0.8 * inch, 2.9 * inch, 0.8 * inch], repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ]
    for i, r in enumerate(results, start=1):
        style_commands.append(("TEXTCOLOR", (3, i), (3, i), _COMPLIANCE_COLORS[r.status]))
        style_commands.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style_commands))
    return table


def _severity_summary_table(findings: list[Finding], styles) -> Table:
    counts = {s: 0 for s in Severity}
    for f in findings:
        counts[f.severity] += 1
    rows = [["Critical", "High", "Medium", "Low", "Informational"], [str(counts[s]) for s in Severity]]
    table = Table(rows, colWidths=[1 * inch] * 5)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("TEXTCOLOR", (0, 1), (0, 1), _SEVERITY_COLORS[Severity.CRITICAL]),
                ("TEXTCOLOR", (1, 1), (1, 1), _SEVERITY_COLORS[Severity.HIGH]),
                ("TEXTCOLOR", (2, 1), (2, 1), _SEVERITY_COLORS[Severity.MEDIUM]),
                ("TEXTCOLOR", (3, 1), (3, 1), _SEVERITY_COLORS[Severity.LOW]),
                ("TEXTCOLOR", (4, 1), (4, 1), _SEVERITY_COLORS[Severity.INFORMATIONAL]),
            ]
        )
    )
    return table


def generate_pdf_report(
    audit: AuditSession,
    findings: list[Finding],
    compliance_results: list[ComplianceResult],
    category: ReportCategory,
    ai_summary: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    styles = _styles()
    elements: list = _header(styles, audit, category)

    elements.append(Paragraph("Findings by Severity", styles["SentinelSectionHeading"]))
    elements.append(_severity_summary_table(findings, styles))
    elements.append(Spacer(1, 0.2 * inch))

    if ai_summary:
        elements.append(Paragraph("Summary", styles["SentinelSectionHeading"]))
        elements.append(Paragraph(ai_summary.replace("\n", "<br/>"), styles["BodyText"]))
        elements.append(Spacer(1, 0.2 * inch))

    if category in (ReportCategory.TECHNICAL, ReportCategory.RISK, ReportCategory.EXECUTIVE):
        elements.append(Paragraph("Findings", styles["SentinelSectionHeading"]))
        max_rows = None if category == ReportCategory.TECHNICAL else 15
        elements.append(_findings_table(findings, styles, max_rows=max_rows))
        elements.append(Spacer(1, 0.2 * inch))

    if category in (ReportCategory.COMPLIANCE, ReportCategory.EXECUTIVE) and compliance_results:
        elements.append(Paragraph("Compliance Controls", styles["SentinelSectionHeading"]))
        elements.append(_compliance_table(compliance_results, styles))

    doc.build(elements)
    return buffer.getvalue()
