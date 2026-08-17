"""
Control catalogs for compliance scoring.

CIS_CONTROL_TITLES / NIST_CONTROL_TITLES give human-readable titles for the
control IDs that collectors already attach to findings (Finding.cis_control
/ Finding.nist_control), so CIS and NIST results can be built directly from
findings.

ISO 27001 / SOC 2 / AWS Well-Architected don't have a per-finding control ID
from the collectors, so CIS_TO_CROSSWALK derives their control outcomes
from the same underlying CIS control via a static crosswalk table.
"""

from __future__ import annotations

from app.models.enums import ComplianceFramework

CIS_CONTROL_TITLES: dict[str, str] = {
    "1.5-1.11": "IAM password policy meets complexity/rotation requirements",
    "1.7": "Eliminate use of the root user for administrative/day-to-day tasks",
    "1.10": "Ensure MFA is enabled for all IAM users with a console password",
    "1.12": "Ensure credentials unused for 90+ days are disabled",
    "1.14": "Ensure access keys are rotated every 90 days or less",
    "1.16": "Ensure IAM policies are attached only to groups/roles with least privilege",
    "2.1.1": "Ensure S3 buckets employ encryption-at-rest",
    "2.1.2": "Ensure S3 bucket access logging is enabled",
    "2.1.3": "Ensure S3 bucket versioning is enabled",
    "2.1.5": "Ensure S3 buckets block public access",
    "2.2.1": "Ensure EBS volume encryption is enabled",
    "2.3.1": "Ensure RDS instances have storage encryption enabled",
    "2.3.3": "Ensure RDS instances are not publicly accessible",
    "2.8": "Ensure rotation for customer-managed KMS keys is enabled",
    "2.9": "Ensure Secrets Manager secrets are rotated",
    "3.1": "Ensure CloudTrail is enabled in all regions and actively logging",
    "3.2": "Ensure CloudTrail log file validation is enabled",
    "3.4": "Ensure CloudTrail trails are integrated with CloudWatch Logs",
    "3.7": "Ensure CloudTrail logs are encrypted with KMS",
    "4.x": "Ensure security-relevant CloudWatch alarms exist",
    "5.1": "Ensure EC2 instances do not have unnecessary public IPs",
    "5.2 / 5.3": "Ensure security groups restrict ingress from 0.0.0.0/0",
}

NIST_CONTROL_TITLES: dict[str, str] = {
    "AC-2": "Account Management",
    "AC-3": "Access Enforcement",
    "AC-6": "Least Privilege",
    "AU-2": "Audit Events",
    "AU-6": "Audit Review, Analysis, and Reporting",
    "AU-9": "Protection of Audit Information",
    "AU-11": "Audit Record Retention",
    "CP-9": "System Backup",
    "CP-10": "System Recovery and Reconstitution",
    "IA-2": "Identification and Authentication (Organizational Users)",
    "IA-5": "Authenticator Management",
    "SC-7": "Boundary Protection",
    "SC-12": "Cryptographic Key Establishment and Management",
    "SC-28": "Protection of Information at Rest",
    "SI-2": "Flaw Remediation",
}

# CIS control id -> list of (framework, control_id, title) derived controls.
CIS_CROSSWALK: dict[str, list[tuple[ComplianceFramework, str, str]]] = {
    "1.10": [
        (ComplianceFramework.ISO_27001, "A.9.4.2", "Secure log-on procedures"),
        (ComplianceFramework.SOC_2, "CC6.1", "Logical access — MFA for privileged access"),
    ],
    "1.16": [
        (ComplianceFramework.ISO_27001, "A.9.2.3", "Management of privileged access rights"),
        (ComplianceFramework.SOC_2, "CC6.3", "Least-privilege access provisioning"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-2", "Apply least-privilege permissions"),
    ],
    "2.1.1": [
        (ComplianceFramework.ISO_27001, "A.10.1.1", "Policy on the use of cryptographic controls"),
        (ComplianceFramework.SOC_2, "CC6.7", "Encryption of data at rest"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-8", "Protect data at rest"),
    ],
    "2.1.5": [
        (ComplianceFramework.ISO_27001, "A.13.1.3", "Segregation in networks / access control"),
        (ComplianceFramework.SOC_2, "CC6.6", "Logical access — restrict public access to systems"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-5", "Protect network resources"),
    ],
    "2.3.1": [
        (ComplianceFramework.ISO_27001, "A.10.1.1", "Policy on the use of cryptographic controls"),
        (ComplianceFramework.SOC_2, "CC6.7", "Encryption of data at rest"),
    ],
    "2.3.3": [
        (ComplianceFramework.ISO_27001, "A.13.1.3", "Segregation in networks / access control"),
        (ComplianceFramework.SOC_2, "CC6.6", "Logical access — restrict public access to systems"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-5", "Protect network resources"),
    ],
    "3.1": [
        (ComplianceFramework.ISO_27001, "A.12.4.1", "Event logging"),
        (ComplianceFramework.SOC_2, "CC7.2", "Monitoring for security events"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-4", "Detect and investigate security events"),
    ],
    "3.7": [
        (ComplianceFramework.ISO_27001, "A.12.4.2", "Protection of log information"),
        (ComplianceFramework.SOC_2, "CC7.2", "Monitoring for security events"),
    ],
    "4.x": [
        (ComplianceFramework.ISO_27001, "A.16.1.2", "Reporting information security events"),
        (ComplianceFramework.SOC_2, "CC7.2", "Monitoring for security events"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-4", "Detect and investigate security events"),
    ],
    "5.2 / 5.3": [
        (ComplianceFramework.ISO_27001, "A.13.1.1", "Network controls"),
        (ComplianceFramework.SOC_2, "CC6.6", "Logical access — restrict public access to systems"),
        (ComplianceFramework.AWS_WELL_ARCHITECTED, "SEC-5", "Protect network resources"),
    ],
    "1.14": [
        (ComplianceFramework.ISO_27001, "A.9.2.4", "Management of secret authentication information"),
        (ComplianceFramework.SOC_2, "CC6.1", "Logical access — credential management"),
    ],
    "2.9": [
        (ComplianceFramework.ISO_27001, "A.9.2.4", "Management of secret authentication information"),
        (ComplianceFramework.SOC_2, "CC6.1", "Logical access — credential management"),
    ],
}
