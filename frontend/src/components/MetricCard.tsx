import type { ReactNode } from "react";
import clsx from "clsx";
import { Card } from "@/components/Card";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
  hint?: string;
}

const toneClasses: Record<string, string> = {
  neutral: "text-text-primary",
  success: "text-accent-green",
  warning: "text-accent-yellow",
  danger: "text-accent-red",
};

export function MetricCard({ label, value, icon, tone = "neutral", hint }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <span className="text-sm text-text-secondary">{label}</span>
        {icon && <span className="text-text-secondary">{icon}</span>}
      </div>
      <div className={clsx("mt-2 text-3xl font-semibold tracking-tight", toneClasses[tone])}>{value}</div>
      {hint && <div className="mt-1 text-xs text-text-secondary">{hint}</div>}
    </Card>
  );
}
