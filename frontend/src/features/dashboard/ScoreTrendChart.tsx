import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ScoreTrendPoint } from "@/types";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { EmptyState } from "@/components/States";

export function ScoreTrendChart({ data }: { data: ScoreTrendPoint[] }) {
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    score: d.security_score,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Security Score Trend</CardTitle>
      </CardHeader>
      {chartData.length < 2 ? (
        <EmptyState title="Not enough data yet" description="Run a few more audits to see your score trend over time." />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis domain={[0, 100]} stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: "#111111", border: "1px solid #222222", borderRadius: 8, fontSize: 12 }}
            />
            <Line type="monotone" dataKey="score" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3, fill: "#3B82F6" }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
