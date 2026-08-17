import { Search } from "lucide-react";
import { Select } from "@/components/Select";
import type { AwsService, FindingStatus, Severity } from "@/types";
import type { FindingsFilters } from "@/services/findingsApi";

const SERVICES: AwsService[] = ["iam", "s3", "ec2", "cloudtrail", "cloudwatch", "lambda", "rds", "kms", "secrets_manager"];
const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "informational"];
const STATUSES: FindingStatus[] = ["open", "acknowledged", "resolved", "suppressed"];

interface FindingsFilterBarProps {
  filters: FindingsFilters;
  onChange: (filters: FindingsFilters) => void;
}

export function FindingsFilterBar({ filters, onChange }: FindingsFilterBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="relative flex-1 min-w-[220px]">
        <label className="mb-1.5 block text-sm font-medium text-text-secondary">Search</label>
        <Search className="pointer-events-none absolute left-3 top-[38px] h-4 w-4 text-text-secondary" />
        <input
          value={filters.search ?? ""}
          onChange={(e) => onChange({ ...filters, search: e.target.value || undefined, page: 1 })}
          placeholder="Search findings..."
          className="w-full rounded-lg border border-border bg-bg py-2 pl-9 pr-3 text-sm placeholder:text-text-secondary/60 focus:border-accent-blue focus:outline-none"
        />
      </div>

      <Select
        label="Severity"
        value={filters.severity ?? ""}
        onChange={(e) => onChange({ ...filters, severity: (e.target.value || undefined) as Severity, page: 1 })}
      >
        <option value="">All</option>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s[0].toUpperCase() + s.slice(1)}
          </option>
        ))}
      </Select>

      <Select
        label="Service"
        value={filters.service ?? ""}
        onChange={(e) => onChange({ ...filters, service: (e.target.value || undefined) as AwsService, page: 1 })}
      >
        <option value="">All</option>
        {SERVICES.map((s) => (
          <option key={s} value={s}>
            {s.toUpperCase()}
          </option>
        ))}
      </Select>

      <Select
        label="Status"
        value={filters.status ?? ""}
        onChange={(e) => onChange({ ...filters, status: (e.target.value || undefined) as FindingStatus, page: 1 })}
      >
        <option value="">All</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s[0].toUpperCase() + s.slice(1)}
          </option>
        ))}
      </Select>
    </div>
  );
}
