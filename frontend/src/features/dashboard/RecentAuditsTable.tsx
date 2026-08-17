import { Link } from "react-router-dom";
import type { RecentAuditSummary } from "@/types";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusChip } from "@/components/Badge";
import { EmptyState } from "@/components/States";
import { Button } from "@/components/Button";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  queued: "neutral",
  running: "info",
  completed: "success",
  failed: "danger",
};

export function RecentAuditsTable({ audits }: { audits: RecentAuditSummary[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Audits</CardTitle>
      </CardHeader>
      {audits.length === 0 ? (
        <EmptyState
          title="No audits yet"
          description="Connect an AWS account and run your first audit to see results here."
          action={
            <Link to="/aws-accounts">
              <Button size="sm">Connect an AWS account</Button>
            </Link>
          }
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-text-secondary">
                <th className="pb-2 font-medium">AWS Account</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Score</th>
                <th className="pb-2 font-medium">Completed</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((audit) => (
                <tr key={audit.id} className="border-t border-border">
                  <td className="py-2.5">
                    <Link to={`/audit-history/${audit.id}`} className="hover:text-accent-blue">
                      {audit.aws_account_alias}
                    </Link>
                  </td>
                  <td className="py-2.5">
                    <StatusChip tone={STATUS_TONE[audit.status] ?? "neutral"}>{audit.status}</StatusChip>
                  </td>
                  <td className="py-2.5 font-mono">{audit.security_score ?? "—"}</td>
                  <td className="py-2.5 text-text-secondary">
                    {audit.completed_at ? new Date(audit.completed_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
