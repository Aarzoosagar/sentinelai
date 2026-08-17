import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ScanSearch, AlertOctagon, ClipboardCheck } from "lucide-react";
import { dashboardApi } from "@/services";
import { MetricCard } from "@/components/MetricCard";
import { LoadingState, ErrorState } from "@/components/States";
import { SeverityBreakdownChart } from "@/features/dashboard/SeverityBreakdownChart";
import { RiskByServiceChart } from "@/features/dashboard/RiskByServiceChart";
import { ScoreTrendChart } from "@/features/dashboard/ScoreTrendChart";
import { RecentAuditsTable } from "@/features/dashboard/RecentAuditsTable";

function scoreTone(score: number | null): "neutral" | "success" | "warning" | "danger" {
  if (score === null) return "neutral";
  if (score >= 80) return "success";
  if (score >= 50) return "warning";
  return "danger";
}

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardApi.summary,
  });

  if (isLoading) return <LoadingState label="Loading your security posture..." />;
  if (isError || !data) return <ErrorState description="We couldn't load your dashboard. Try refreshing." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-text-secondary">Your cloud security posture at a glance.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Security Score"
          value={data.security_score !== null ? `${data.security_score}/100` : "—"}
          icon={<ShieldCheck className="h-4 w-4" />}
          tone={scoreTone(data.security_score)}
        />
        <MetricCard
          label="Resources Scanned"
          value={data.resources_scanned}
          icon={<ScanSearch className="h-4 w-4" />}
        />
        <MetricCard
          label="Critical Findings"
          value={data.findings_by_severity.critical}
          icon={<AlertOctagon className="h-4 w-4" />}
          tone={data.findings_by_severity.critical > 0 ? "danger" : "success"}
        />
        <MetricCard
          label="Compliance Score"
          value={data.compliance_score !== null ? `${data.compliance_score}/100` : "—"}
          icon={<ClipboardCheck className="h-4 w-4" />}
          tone={scoreTone(data.compliance_score)}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SeverityBreakdownChart data={data.findings_by_severity} />
        <RiskByServiceChart data={data.risk_by_service} />
      </div>

      <ScoreTrendChart data={data.security_score_trend} />
      <RecentAuditsTable audits={data.recent_audits} />
    </div>
  );
}
