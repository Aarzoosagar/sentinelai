import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import type { SeverityBreakdown } from "@/types";
import { Card, CardHeader, CardTitle } from "@/components/Card";

const SEVERITY_COLORS: Record<string, string> = {
  Critical: "#EF4444",
  High: "#F59E0B",
  Medium: "#EAB308",
  Low: "#10B981",
  Informational: "#6B7280",
};

export function SeverityBreakdownChart({ data }: { data: SeverityBreakdown }) {
  const chartData = [
    { name: "Critical", value: data.critical },
    { name: "High", value: data.high },
    { name: "Medium", value: data.medium },
    { name: "Low", value: data.low },
    { name: "Informational", value: data.informational },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Findings by Severity</CardTitle>
      </CardHeader>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
          <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: "#111111", border: "1px solid #222222", borderRadius: 8, fontSize: 12 }}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
