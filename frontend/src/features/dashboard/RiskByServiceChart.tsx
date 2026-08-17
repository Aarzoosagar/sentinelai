import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ServiceRiskPoint } from "@/types";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { EmptyState } from "@/components/States";

export function RiskByServiceChart({ data }: { data: ServiceRiskPoint[] }) {
  const chartData = data.map((d) => ({ name: d.service.toUpperCase(), findings: d.finding_count }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Findings by AWS Service</CardTitle>
      </CardHeader>
      {chartData.length === 0 ? (
        <EmptyState title="No findings yet" description="Run an audit to see findings broken down by service." />
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" horizontal={false} />
            <XAxis type="number" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
            <YAxis type="category" dataKey="name" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} width={90} />
            <Tooltip
              contentStyle={{ background: "#111111", border: "1px solid #222222", borderRadius: 8, fontSize: 12 }}
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
            />
            <Bar dataKey="findings" fill="#3B82F6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
