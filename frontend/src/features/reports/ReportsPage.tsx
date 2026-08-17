import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { auditApi } from "@/services/auditApi";
import { reportsApi } from "@/services";
import { Select } from "@/components/Select";
import { Button } from "@/components/Button";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { ReportCard } from "@/features/reports/ReportCard";
import { GenerateReportModal } from "@/features/reports/GenerateReportModal";

export function ReportsPage() {
  const { data: audits, isLoading: auditsLoading } = useQuery({
    queryKey: ["audit-history"],
    queryFn: auditApi.history,
  });
  const completedAudits = audits?.filter((a) => a.status === "completed") ?? [];

  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (!selectedAuditId && completedAudits.length > 0) {
      setSelectedAuditId(completedAudits[0].id);
    }
  }, [completedAudits, selectedAuditId]);

  const { data: reports, isLoading: reportsLoading, isError } = useQuery({
    queryKey: ["reports", selectedAuditId],
    queryFn: () => reportsApi.listForAudit(selectedAuditId!),
    enabled: !!selectedAuditId,
  });

  if (auditsLoading) return <LoadingState label="Loading audits..." />;

  if (completedAudits.length === 0) {
    return (
      <EmptyState
        title="No completed audits yet"
        description="Run an audit first, then come back here to generate executive, technical, compliance, and risk reports."
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Reports</h1>
          <p className="text-sm text-text-secondary">Generate and download PDF, CSV, or JSON reports.</p>
        </div>
        <div className="flex items-end gap-3">
          <Select value={selectedAuditId ?? ""} onChange={(e) => setSelectedAuditId(e.target.value)} className="w-64">
            {completedAudits.map((audit) => (
              <option key={audit.id} value={audit.id}>
                Audit from {new Date(audit.completed_at ?? audit.created_at).toLocaleString()}
              </option>
            ))}
          </Select>
          <Button onClick={() => setModalOpen(true)} disabled={!selectedAuditId}>
            <Plus className="h-4 w-4" /> Generate report
          </Button>
        </div>
      </div>

      {reportsLoading && <LoadingState label="Loading reports..." />}
      {isError && <ErrorState description="We couldn't load reports for this audit." />}

      {reports && reports.length === 0 && (
        <EmptyState
          title="No reports generated yet"
          description="Generate an executive, technical, compliance, or risk report for this audit."
          action={
            <Button size="sm" onClick={() => setModalOpen(true)}>
              Generate report
            </Button>
          }
        />
      )}

      {reports && reports.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}

      {selectedAuditId && (
        <GenerateReportModal isOpen={modalOpen} onClose={() => setModalOpen(false)} auditId={selectedAuditId} />
      )}
    </div>
  );
}
