function GrowthCell({ status, children }) {
  const icon =
    status === "up" ? "↑" : status === "down" ? "↓" : "→";
  const color =
    status === "up"
      ? "text-green-700"
      : status === "down"
        ? "text-red-700"
        : "text-black/60";
  return (
    <span className={`inline-flex items-center gap-1 font-bold ${color}`}>
      <span aria-hidden>{icon}</span>
      {children}
    </span>
  );
}

export default function RegionalPivotTable({ rows, title }) {
  return (
    <div className="rounded-xl border border-black/10 bg-white p-5" id="regional-matrix">
      <h3 className="font-garage text-xl font-black">{title}</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-black/10 text-left text-xs font-bold uppercase tracking-wider text-black/50">
              <th className="w-[20%] py-2 pr-3">Region</th>
              <th className="w-[30%] py-2 pr-3">Avg outcome</th>
              <th className="w-[20%] py-2 pr-3">vs. peers</th>
              <th className="w-[30%] py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                className={`border-b border-black/5 ${
                  row.isFooter
                    ? "bg-black/[0.04] font-bold"
                    : index % 2 === 0
                      ? "bg-white"
                      : "bg-black/[0.02]"
                }`}
                key={`${row.region}-${row.isFooter ? "footer" : "row"}`}
              >
                <td className="py-3 pr-3">{row.region}</td>
                <td className="py-3 pr-3 tabular-nums">
                  {typeof row.revenue === "number"
                    ? row.revenue.toFixed(2)
                    : row.revenue}
                </td>
                <td className="py-3 pr-3">
                  <GrowthCell status={row.status}>{row.growth}</GrowthCell>
                </td>
                <td className="py-3 text-black/65">{row.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? (
          <p className="py-8 text-center text-sm font-semibold text-black/50">
            No regional field detected in the CSV.
          </p>
        ) : null}
      </div>
    </div>
  );
}
