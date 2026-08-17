import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { findingsApi, type FindingsFilters } from "@/services/findingsApi";
import { SeverityBadge, StatusChip } from "@/components/Badge";
import { Pagination } from "@/components/Pagination";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Card } from "@/components/Card";
import { FindingsFilterBar } from "@/features/findings/FindingsFilterBar";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  open: "danger",
  acknowledged: "warning",
  resolved: "success",
  suppressed: "neutral",
};

export function FindingsListPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<FindingsFilters>({
    page: 1,
    page_size: 25,
    search: searchParams.get("search") ?? undefined,
    audit_session_id: searchParams.get("audit_session_id") ?? undefined,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["findings", filters],
    queryFn: () => findingsApi.list(filters),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Findings</h1>
        <p className="text-sm text-text-secondary">
          {data ? `${data.total} finding${data.total === 1 ? "" : "s"}` : "Browse and triage security findings."}
        </p>
      </div>

      <Card>
        <FindingsFilterBar filters={filters} onChange={setFilters} />
      </Card>

      {isLoading && <LoadingState label="Loading findings..." />}
      {isError && <ErrorState description="We couldn't load findings." />}

      {data && data.items.length === 0 && (
        <EmptyState title="No findings match your filters" description="Try broadening your search or clearing filters." />
      )}

      {data && data.items.length > 0 && (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-text-secondary">
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Finding</th>
                  <th className="px-4 py-3 font-medium">Service</th>
                  <th className="px-4 py-3 font-medium">Resource</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Detected</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((finding) => (
                  <tr key={finding.id} className="border-b border-border last:border-0 hover:bg-white/[0.02]">
                    <td className="px-4 py-3">
                      <SeverityBadge severity={finding.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/findings/${finding.id}`} className="font-medium hover:text-accent-blue">
                        {finding.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 uppercase text-text-secondary">{finding.service}</td>
                    <td className="sentinel-mono px-4 py-3 text-text-secondary">{finding.resource_id ?? "—"}</td>
                    <td className="px-4 py-3">
                      <StatusChip tone={STATUS_TONE[finding.status]}>{finding.status}</StatusChip>
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {new Date(finding.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-border p-4">
            <Pagination
              page={data.page}
              totalPages={data.total_pages}
              onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
            />
          </div>
        </Card>
      )}
    </div>
  );
}
