import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { findingsApi } from "@/services/findingsApi";
import { Card } from "@/components/Card";
import { SeverityBadge } from "@/components/Badge";
import { LoadingState, ErrorState } from "@/components/States";
import { Select } from "@/components/Select";
import { RiskIndicator } from "@/components/RiskIndicator";
import { Tabs } from "@/components/Tabs";
import { Breadcrumb } from "@/components/Breadcrumb";
import { AiExplanationPanel } from "@/features/findings/AiExplanationPanel";
import { IacExamplePanel } from "@/features/findings/IacExamplePanel";
import type { FindingStatus } from "@/types";

export function FindingDetailPage() {
  const { findingId } = useParams<{ findingId: string }>();
  const queryClient = useQueryClient();

  const { data: finding, isLoading, isError } = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => findingsApi.get(findingId!),
    enabled: !!findingId,
  });

  const statusMutation = useMutation({
    mutationFn: (status: FindingStatus) => findingsApi.updateStatus(findingId!, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["finding", findingId] }),
  });

  if (isLoading) return <LoadingState label="Loading finding..." />;
  if (isError || !finding) return <ErrorState description="We couldn't load this finding." />;

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Findings", to: "/findings" }, { label: finding.title }]} />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs uppercase text-text-secondary">{finding.service}</span>
          </div>
          <h1 className="text-xl font-semibold">{finding.title}</h1>
          {finding.resource_id && (
            <p className="sentinel-mono mt-1 text-sm text-text-secondary">{finding.resource_id}</p>
          )}
        </div>
        <Select
          value={finding.status}
          onChange={(e) => statusMutation.mutate(e.target.value as FindingStatus)}
          className="w-44"
        >
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="suppressed">Suppressed</option>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <h2 className="mb-2 text-sm font-medium text-text-secondary">Description</h2>
            <p className="text-sm text-text-primary">{finding.description}</p>
          </Card>

          <Card>
            <Tabs
              tabs={[
                {
                  id: "explanation",
                  label: "AI Explanation",
                  content: <AiExplanationPanel finding={finding} />,
                },
                {
                  id: "remediation",
                  label: "Remediation",
                  content: (
                    <div className="flex flex-col gap-4">
                      <div>
                        <h3 className="mb-1 text-sm font-medium text-text-secondary">Guidance</h3>
                        <p className="text-sm text-text-primary">{finding.remediation}</p>
                        {finding.estimated_remediation_time && (
                          <p className="mt-1 text-xs text-text-secondary">
                            Estimated time: {finding.estimated_remediation_time}
                          </p>
                        )}
                      </div>
                      <div>
                        <h3 className="mb-2 text-sm font-medium text-text-secondary">Fix it with code</h3>
                        <IacExamplePanel findingId={finding.id} />
                      </div>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          {finding.risk_score && (
            <Card>
              <h2 className="mb-3 text-sm font-medium text-text-secondary">Risk Score</h2>
              <RiskIndicator risk={finding.risk_score} />
            </Card>
          )}

          <Card>
            <h2 className="mb-3 text-sm font-medium text-text-secondary">Framework Mappings</h2>
            <dl className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-text-secondary">CIS Control</dt>
                <dd className="sentinel-mono">{finding.cis_control ?? "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-secondary">NIST Control</dt>
                <dd className="sentinel-mono">{finding.nist_control ?? "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-secondary">MITRE ATT&amp;CK</dt>
                <dd className="text-right sentinel-mono">{finding.mitre_attack ?? "—"}</dd>
              </div>
            </dl>
          </Card>

          {finding.resource_arn && (
            <Card>
              <h2 className="mb-2 text-sm font-medium text-text-secondary">Resource</h2>
              <p className="sentinel-mono break-all text-xs text-text-primary">{finding.resource_arn}</p>
              {finding.region && <p className="mt-1 text-xs text-text-secondary">Region: {finding.region}</p>}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
