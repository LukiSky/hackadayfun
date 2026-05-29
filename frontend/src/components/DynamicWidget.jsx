import {
  Bar,
  BarChart,
  Cell,
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

const PIE_COLORS = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#64748b"];

function toChartData(labels, values) {
  return (labels || []).map((label, i) => ({
    name: String(label),
    value: Number(values?.[i] ?? 0),
  }));
}

export default function DynamicWidget({ widget, editMode, onUpdate, onDelete }) {
  const { type, title, labels, values, value } = widget;
  const data = toChartData(labels, values);

  return (
    <div className="card relative flex h-full min-h-[220px] flex-col">
      {editMode && (
        <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-slate-100 pb-2">
          <input
            className="input flex-1 text-xs"
            value={title}
            onChange={(e) => onUpdate?.({ title: e.target.value })}
            aria-label="Chart title"
          />
          <select
            className="rounded border border-slate-300 px-2 py-1 text-xs"
            value={type}
            onChange={(e) => onUpdate?.({ type: e.target.value })}
          >
            <option value="bar-chart">Bar</option>
            <option value="line-chart">Line</option>
            <option value="pie-chart">Pie</option>
            <option value="kpi-card">KPI</option>
          </select>
          <button
            type="button"
            className="text-xs text-red-600 hover:underline"
            onClick={() => onDelete?.()}
          >
            Remove
          </button>
        </div>
      )}
      {!editMode && <h3 className="mb-2 text-sm font-semibold text-slate-800">{title}</h3>}

      {type === "kpi-card" ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-4xl font-bold text-brand-600">{value ?? "—"}</p>
        </div>
      ) : (
        <div className="min-h-[180px] flex-1">
          <ResponsiveContainer width="100%" height={180}>
            {type === "line-chart" ? (
              <LineChart data={data}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot />
              </LineChart>
            ) : type === "pie-chart" ? (
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                  {data.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            ) : (
              <BarChart data={data}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
