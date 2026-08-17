import { FileText, Download } from "lucide-react";
import { Card } from "@/components/Card";
import { StatusChip } from "@/components/Badge";
import type { Report } from "@/types";
import { reportsApi } from "@/services";

const CATEGORY_LABELS: Record<string, string> = {
  executive: "Executive Report",
  technical: "Technical Report",
  compliance: "Compliance Report",
  risk: "Risk Report",
  audit_history: "Audit History Report",
};

export function ReportCard({ report }: { report: Report }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-blue/10 text-accent-blue">
            <FileText className="h-4 w-4" />
          </span>
          <div>
            <div className="font-medium">{CATEGORY_LABELS[report.category] ?? report.category}</div>
            <div className="text-xs text-text-secondary">{new Date(report.generated_at).toLocaleString()}</div>
          </div>
        </div>
        <StatusChip tone="neutral">{report.type.toUpperCase()}</StatusChip>
      </div>
      <a
        href={reportsApi.downloadUrl(report.id)}
        download
        className="mt-4 flex w-fit items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-blue/50 hover:text-text-primary"
      >
        <Download className="h-3.5 w-3.5" /> Download
      </a>
    </Card>
  );
}
