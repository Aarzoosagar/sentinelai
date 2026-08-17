import clsx from "clsx";
import type { ComplianceStatus, Severity } from "@/types";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-accent-red/10 text-accent-red border-accent-red/30",
  high: "bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  low: "bg-accent-green/10 text-accent-green border-accent-green/30",
  informational: "bg-text-secondary/10 text-text-secondary border-text-secondary/30",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
        SEVERITY_STYLES[severity]
      )}
    >
      {severity}
    </span>
  );
}

const COMPLIANCE_STYLES: Record<ComplianceStatus, string> = {
  pass: "bg-accent-green/10 text-accent-green border-accent-green/30",
  warning: "bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30",
  fail: "bg-accent-red/10 text-accent-red border-accent-red/30",
};

export function ComplianceBadge({ status }: { status: ComplianceStatus }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
        COMPLIANCE_STYLES[status]
      )}
    >
      {status}
    </span>
  );
}

export function StatusChip({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  const toneStyles: Record<string, string> = {
    neutral: "bg-white/5 text-text-secondary border-border",
    success: "bg-accent-green/10 text-accent-green border-accent-green/30",
    warning: "bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30",
    danger: "bg-accent-red/10 text-accent-red border-accent-red/30",
    info: "bg-accent-blue/10 text-accent-blue border-accent-blue/30",
  };
  return (
    <span className={clsx("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium capitalize", toneStyles[tone])}>
      {children}
    </span>
  );
}
