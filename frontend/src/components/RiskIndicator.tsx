import type { RiskScore } from "@/types";

function toneForScore(score: number): { color: string; label: string } {
  if (score >= 80) return { color: "#EF4444", label: "Critical risk" };
  if (score >= 60) return { color: "#F59E0B", label: "High risk" };
  if (score >= 35) return { color: "#EAB308", label: "Medium risk" };
  return { color: "#10B981", label: "Low risk" };
}

export function RiskIndicator({ risk }: { risk: RiskScore }) {
  const { color, label } = toneForScore(risk.risk_score);
  const circumference = 2 * Math.PI * 34;
  const offset = circumference * (1 - risk.risk_score / 100);

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-20 w-20 shrink-0">
        <svg viewBox="0 0 80 80" className="h-20 w-20 -rotate-90">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#222222" strokeWidth="8" />
          <circle
            cx="40"
            cy="40"
            r="34"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 300ms ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-lg font-semibold">
          {risk.risk_score}
        </div>
      </div>
      <div>
        <div className="text-sm font-medium" style={{ color }}>
          {label}
        </div>
        <dl className="mt-2 flex flex-col gap-1 text-xs text-text-secondary">
          <div className="flex justify-between gap-4">
            <dt>Likelihood</dt>
            <dd className="font-mono text-text-primary">{risk.likelihood}/5</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>Business impact</dt>
            <dd className="font-mono text-text-primary">{risk.business_impact}/5</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>Exploitability</dt>
            <dd className="font-mono text-text-primary">{risk.exploitability}/5</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
