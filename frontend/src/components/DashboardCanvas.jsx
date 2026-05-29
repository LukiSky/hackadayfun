import DynamicWidget from "./DynamicWidget.jsx";

export default function DashboardCanvas({ widgets, editMode, onUpdateWidget, onDeleteWidget }) {
  if (!widgets.length) {
    return (
      <div className="card flex min-h-[200px] items-center justify-center border-dashed text-center text-sm text-slate-500">
        <p>
          No charts yet. Ask the copilot: &ldquo;Add a bar chart of attendance by program&rdquo; or
          &ldquo;Add a pie chart of feedback sentiment&rdquo;.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {widgets.map((w) => (
        <DynamicWidget
          key={w.id}
          widget={w}
          editMode={editMode}
          onUpdate={(patch) => onUpdateWidget?.(w.id, patch)}
          onDelete={() => onDeleteWidget?.(w.id)}
        />
      ))}
    </div>
  );
}
