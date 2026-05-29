export default function MetricCard({ label, value }) {
  return (
    <div className="rounded-soft bg-cleanWhite p-5 shadow-sm border border-black/10">
      <p className="font-proxima text-sm text-black/60">{label}</p>
      <h3 className="mt-2 font-garage text-3xl text-inkBlack">{value}</h3>
    </div>
  );
}