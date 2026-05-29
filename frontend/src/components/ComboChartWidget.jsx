import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function ComboChartWidget({ data, title, annotation }) {
  const target =
    data.length > 0
      ? data.reduce((sum, row) => sum + row.target, 0) / data.length
      : 0;

  return (
    <div className="rounded-xl border border-black/10 bg-white p-5" id="rev-matrix-chart">
      <h3 className="font-garage text-xl font-black">{title}</h3>
      <p className="mt-1 text-xs font-semibold text-black/55">
        Bars: average outcome by region · Line: feedback density index
      </p>
      {annotation ? (
        <p className="mt-2 rounded-lg bg-[#FFD100]/30 px-3 py-2 text-xs font-semibold text-black/70">
          {annotation}
        </p>
      ) : null}
      <div className="mt-4 h-72">
        <ResponsiveContainer height="100%" width="100%">
          <ComposedChart data={data} margin={{ bottom: 24, left: 8, right: 12, top: 8 }}>
            <CartesianGrid stroke="#e0e0e0" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis hide orientation="right" yAxisId="right" />
            <Tooltip />
            <Legend verticalAlign="top" align="right" />
            <ReferenceLine
              y={target}
              yAxisId="left"
              stroke="#2b5c8f"
              strokeDasharray="4 4"
              label={{ value: "Peer target", position: "insideTopRight", fontSize: 10 }}
            />
            <Bar
              dataKey="actual"
              fill="#2b5c8f"
              name="Avg outcome"
              radius={[4, 4, 0, 0]}
              yAxisId="left"
            />
            <Line
              dataKey="cacIndex"
              dot={{ fill: "#e63946", r: 4 }}
              name="Feedback index"
              stroke="#e63946"
              strokeWidth={2}
              type="monotone"
              yAxisId="right"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
