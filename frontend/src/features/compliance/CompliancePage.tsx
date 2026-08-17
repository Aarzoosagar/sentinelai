import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/services/auditApi";
import { complianceApi } from "@/services";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Select } from "@/components/Select";
import { ComplianceCard } from "@/components/ComplianceCard";
import { ComplianceControlTable } from "@/features/compliance/ComplianceControlTable";
import { Card } from "@/components/Card";

export function CompliancePage() {
  const { data: audits, isLoading: auditsLoading } = useQuery({
    queryKey: ["audit-history"],
    queryFn: auditApi.history,
  });

  const completedAudits = audits?.filter((a) => a.status === "completed") ?? [];
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [activeFramework, setActiveFramework] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedAuditId && completedAudits.length > 0) {
      setSelectedAuditId(completedAudits[0].id);
    }
  }, [completedAudits, selectedAuditId]);

  const { data: overview, isLoading: overviewLoading, isError } = useQuery({
    queryKey: ["compliance", selectedAuditId],
    queryFn: () => complianceApi.overview(selectedAuditId!),
    enabled: !!selectedAuditId,
  });

  useEffect(() => {
    if (overview && overview.frameworks.length > 0 && !activeFramework) {
      setActiveFramework(overview.frameworks[0].framework);
    }
  }, [overview, activeFramework]);

  if (auditsLoading) return <LoadingState label="Loading audits..." />;

  if (completedAudits.length === 0) {
    return (
      <EmptyState
        title="No completed audits yet"
        description="Run an audit to see your compliance posture across CIS, NIST, ISO 27001, SOC 2, and AWS Well-Architected."
      />
    );
  }

  const activeSummary = overview?.frameworks.find((f) => f.framework === activeFramework);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Compliance</h1>
          <p className="text-sm text-text-secondary">Control-level results across every supported framework.</p>
        </div>
        <Select
          value={selectedAuditId ?? ""}
          onChange={(e) => {
            setSelectedAuditId(e.target.value);
            setActiveFramework(null);
          }}
          className="w-64"
        >
          {completedAudits.map((audit) => (
            <option key={audit.id} value={audit.id}>
              Audit from {new Date(audit.completed_at ?? audit.created_at).toLocaleString()}
            </option>
          ))}
        </Select>
      </div>

      {overviewLoading && <LoadingState label="Loading compliance results..." />}
      {isError && <ErrorState description="We couldn't load compliance results for this audit." />}

      {overview && overview.frameworks.length === 0 && (
        <EmptyState title="No compliance data for this audit" />
      )}

      {overview && overview.frameworks.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {overview.frameworks.map((summary) => (
              <ComplianceCard
                key={summary.framework}
                summary={summary}
                isActive={summary.framework === activeFramework}
                onClick={() => setActiveFramework(summary.framework)}
              />
            ))}
          </div>

          {activeSummary && (
            <Card className="p-0">
              <ComplianceControlTable results={activeSummary.results} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
