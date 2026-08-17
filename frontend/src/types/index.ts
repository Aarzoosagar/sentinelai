// Mirrors backend/app/schemas/*.py and app/models/enums.py exactly, so the
// frontend and API never drift silently out of sync.

export type Severity = "critical" | "high" | "medium" | "low" | "informational";
export type FindingStatus = "open" | "acknowledged" | "resolved" | "suppressed";
export type AwsService =
  | "iam"
  | "s3"
  | "ec2"
  | "cloudtrail"
  | "cloudwatch"
  | "lambda"
  | "rds"
  | "kms"
  | "secrets_manager";
export type AuditStatus = "queued" | "running" | "completed" | "failed";
export type AwsAuthMethod = "assume_role" | "access_key";
export type AccountValidationStatus = "pending" | "valid" | "invalid";
export type ComplianceFramework =
  | "cis_aws_foundations"
  | "aws_well_architected"
  | "nist_csf"
  | "iso_27001"
  | "soc_2";
export type ComplianceStatus = "pass" | "warning" | "fail";
export type ReportType = "pdf" | "csv" | "json";
export type ReportCategory = "executive" | "technical" | "compliance" | "risk" | "audit_history";
export type ChatRole = "user" | "assistant";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AwsAccount {
  id: string;
  account_alias: string;
  aws_account_id: string;
  region: string;
  auth_method: AwsAuthMethod;
  validation_status: AccountValidationStatus;
  validated_at: string | null;
  created_at: string;
  role_arn: string | null;
}

export interface AuditSession {
  id: string;
  aws_account_id: string;
  status: AuditStatus;
  started_at: string | null;
  completed_at: string | null;
  resources_scanned: number;
  security_score: number | null;
  error_message: string | null;
  created_at: string;
}

export interface RiskScore {
  risk_score: number;
  likelihood: number;
  business_impact: number;
  exploitability: number;
}

export interface FindingListItem {
  id: string;
  service: AwsService;
  title: string;
  severity: Severity;
  status: FindingStatus;
  resource_id: string | null;
  region: string | null;
  created_at: string;
}

export interface FindingDetail {
  id: string;
  audit_session_id: string;
  service: AwsService;
  title: string;
  description: string;
  severity: Severity;
  status: FindingStatus;
  resource_arn: string | null;
  resource_id: string | null;
  region: string | null;
  cis_control: string | null;
  nist_control: string | null;
  mitre_attack: string | null;
  remediation: string;
  estimated_remediation_time: string | null;
  references: string | null;
  ai_explanation: string | null;
  risk_score: RiskScore | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ComplianceResult {
  id: string;
  framework: ComplianceFramework;
  control_id: string;
  control_title: string;
  status: ComplianceStatus;
  notes: string | null;
  related_finding_id: string | null;
}

export interface ComplianceFrameworkSummary {
  framework: ComplianceFramework;
  score: number;
  passed: number;
  warnings: number;
  failed: number;
  total_controls: number;
  results: ComplianceResult[];
}

export interface ComplianceOverview {
  audit_session_id: string;
  frameworks: ComplianceFrameworkSummary[];
}

export interface Report {
  id: string;
  audit_session_id: string;
  type: ReportType;
  category: ReportCategory;
  generated_at: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface SuggestedQuestion {
  label: string;
  prompt: string;
}

export interface SeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
  informational: number;
}

export interface ServiceRiskPoint {
  service: string;
  finding_count: number;
  average_risk_score: number;
}

export interface ScoreTrendPoint {
  audit_session_id: string;
  date: string;
  security_score: number;
}

export interface RecentAuditSummary {
  id: string;
  aws_account_alias: string;
  status: string;
  security_score: number | null;
  completed_at: string | null;
}

export interface DashboardSummary {
  security_score: number | null;
  resources_scanned: number;
  compliance_score: number | null;
  findings_by_severity: SeverityBreakdown;
  risk_by_service: ServiceRiskPoint[];
  security_score_trend: ScoreTrendPoint[];
  recent_audits: RecentAuditSummary[];
  top_vulnerable_services: ServiceRiskPoint[];
}

export interface UserSettings {
  groq_model_override: string | null;
  email_notifications_enabled: boolean;
  critical_finding_alerts_enabled: boolean;
  theme: string;
}
