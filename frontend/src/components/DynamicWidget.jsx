import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_PALETTES } from "../lib/activeContext.js";

const DEFAULT_COLORS = CHART_PALETTES["Brand Colors"];

export default function DynamicWidget({ widget, appearanceSettings }) {
  if (!widget || widget.renderStatus === "removed") return null;

  const palette =
    CHART_PALETTES[appearanceSettings?.theme] || DEFAULT_COLORS;
  const showDataLabels = appearanceSettings?.showDataLabels !== false;

  const chartData = widget.labels.map((label, index) => ({
    name: label,
    value: widget.values[index] ?? 0,
  }));

  return (
    <article
      className="rounded-xl border border-black/10 bg-white p-4 shadow-sm"
      id={widget.id}
    >
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
        {widget.type}
      </p>
      <h3 className="font-garage text-xl font-black text-black">{widget.title}</h3>
      <div className="mt-4 h-64">
        {chartData.length ? (
          <ResponsiveContainer height="100%" width="100%">
            {widget.type === "pie-chart" ? (
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      fill={palette[index % palette.length]}
                      key={entry.name}
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            ) : widget.type === "line-chart" ? (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line
                  dataKey="value"
                  dot={{ r: 3 }}
                  stroke={palette[1]}
                  strokeWidth={3}
                  type="monotone"
                >
                  {showDataLabels ? (
                    <LabelList dataKey="value" position="top" fontSize={10} />
                  ) : null}
                </Line>
              </LineChart>
            ) : (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      fill={palette[index % palette.length]}
                      key={entry.name}
                    />
                  ))}
                  {showDataLabels ? (
                    <LabelList dataKey="value" position="top" fontSize={10} />
                  ) : null}
                </Bar>
              </BarChart>
            )}
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-black/50">No chart data in this widget.</p>
        )}
      </div>
    </article>
  );
}
