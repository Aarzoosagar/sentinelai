import clsx from "clsx";
import { Card } from "@/components/Card";
import { ProgressBar } from "@/components/States";
import type { ComplianceFrameworkSummary } from "@/types";

const FRAMEWORK_LABELS: Record<string, string> = {
  cis_aws_foundations: "CIS AWS Foundations",
  aws_well_architected: "AWS Well-Architected",
  nist_csf: "NIST CSF",
  iso_27001: "ISO 27001",
  soc_2: "SOC 2",
};

function toneForScore(score: number): "green" | "yellow" | "red" {
  if (score >= 80) return "green";
  if (score >= 50) return "yellow";
  return "red";
}

export function ComplianceCard({
  summary,
  isActive,
  onClick,
}: {
  summary: ComplianceFrameworkSummary;
  isActive: boolean;
  onClick: () => void;
}) {
  const tone = toneForScore(summary.score);
  const toneText: Record<string, string> = { green: "text-accent-green", yellow: "text-accent-yellow", red: "text-accent-red" };

  return (
    <button onClick={onClick} className="text-left">
      <Card className={clsx("transition-colors duration-150", isActive && "border-accent-blue")}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">{FRAMEWORK_LABELS[summary.framework] ?? summary.framework}</span>
          <span className={clsx("text-lg font-semibold", toneText[tone])}>{summary.score}</span>
        </div>
        <div className="mt-3">
          <ProgressBar value={summary.score} tone={tone} />
        </div>
        <div className="mt-2 flex justify-between text-xs text-text-secondary">
          <span>{summary.passed} passed</span>
          <span>{summary.warnings} warnings</span>
          <span>{summary.failed} failed</span>
        </div>
      </Card>
    </button>
  );
}
