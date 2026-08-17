import { Link } from "react-router-dom";
import { ComplianceBadge } from "@/components/Badge";
import type { ComplianceResult } from "@/types";

export function ComplianceControlTable({ results }: { results: ComplianceResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-text-secondary">
            <th className="px-4 py-3 font-medium">Control</th>
            <th className="px-4 py-3 font-medium">Description</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Related finding</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.id} className="border-b border-border last:border-0">
              <td className="sentinel-mono px-4 py-3">{result.control_id}</td>
              <td className="px-4 py-3">{result.control_title}</td>
              <td className="px-4 py-3">
                <ComplianceBadge status={result.status} />
              </td>
              <td className="px-4 py-3">
                {result.related_finding_id ? (
                  <Link to={`/findings/${result.related_finding_id}`} className="text-accent-blue hover:underline">
                    View finding
                  </Link>
                ) : (
                  <span className="text-text-secondary">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
