import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/services/auditApi";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Card } from "@/components/Card";
import { StatusChip } from "@/components/Badge";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  queued: "neutral",
  running: "info",
  completed: "success",
  failed: "danger",
};

function scoreColor(score: number | null): string {
  if (score === null) return "text-text-secondary";
  if (score >= 80) return "text-accent-green";
  if (score >= 50) return "text-accent-yellow";
  return "text-accent-red";
}

export function AuditHistoryPage() {
  const { data: audits, isLoading, isError } = useQuery({
    queryKey: ["audit-history"],
    queryFn: auditApi.history,
  });

  if (isLoading) return <LoadingState label="Loading audit history..." />;
  if (isError) return <ErrorState description="We couldn't load your audit history." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Audit History</h1>
        <p className="text-sm text-text-secondary">Every audit run against your connected AWS accounts.</p>
      </div>

      {audits && audits.length === 0 && (
        <EmptyState title="No audits yet" description="Connect an AWS account and run your first audit." />
      )}

      {audits && audits.length > 0 && (
        <div className="relative flex flex-col gap-4 pl-6">
          <div className="absolute bottom-2 left-[7px] top-2 w-px bg-border" />
          {audits.map((audit) => (
            <div key={audit.id} className="relative">
              <span
                className={`absolute -left-6 top-4 h-3 w-3 rounded-full border-2 border-bg ${
                  audit.status === "completed"
                    ? "bg-accent-green"
                    : audit.status === "failed"
                      ? "bg-accent-red"
                      : "bg-accent-blue"
                }`}
              />
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <StatusChip tone={STATUS_TONE[audit.status]}>{audit.status}</StatusChip>
                      <span className="text-xs text-text-secondary">
                        {new Date(audit.created_at).toLocaleString()}
                      </span>
                    </div>
                    {audit.error_message && (
                      <p className="mt-1 max-w-lg text-xs text-accent-red">{audit.error_message}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-xs text-text-secondary">Score</div>
                      <div className={`font-mono text-lg font-semibold ${scoreColor(audit.security_score)}`}>
                        {audit.security_score ?? "—"}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-text-secondary">Resources</div>
                      <div className="font-mono text-lg font-semibold">{audit.resources_scanned}</div>
                    </div>
                    {audit.status === "completed" && (
                      <Link
                        to={`/findings?audit_session_id=${audit.id}`}
                        className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-blue/50 hover:text-text-primary"
                      >
                        View findings
                      </Link>
                    )}
                    {(audit.status === "queued" || audit.status === "running") && (
                      <Link
                        to={`/audit-wizard/${audit.id}`}
                        className="rounded-lg border border-accent-blue/40 px-3 py-1.5 text-xs font-medium text-accent-blue hover:bg-accent-blue/10"
                      >
                        View progress
                      </Link>
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
