import DynamicWidget from "./DynamicWidget.jsx";
import InteractiveAudioCard from "./InteractiveAudioCard.jsx";

function KpiWidget({ widget }) {
  return (
    <article
      className="flex h-full min-h-[200px] flex-col justify-center rounded-xl border border-black/10 bg-white p-6 shadow-sm"
      id={widget.id}
    >
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
        {widget.type}
      </p>
      <h3 className="font-garage text-lg font-black text-black/70">{widget.title}</h3>
      <p className="mt-3 font-garage text-5xl font-black text-black">{widget.value}</p>
      {widget.kpiHelper ? (
        <p className="mt-2 text-sm font-semibold text-black/55">{widget.kpiHelper}</p>
      ) : null}
    </article>
  );
}

function gridClass(gridPos) {
  if (gridPos === "top-left") return "md:col-span-1";
  if (gridPos === "top-right") return "md:col-span-1";
  if (gridPos === "bottom-full") return "md:col-span-2";
  return "md:col-span-1";
}

export default function DashboardCanvas({
  widgets,
  chartAppearance,
  onPlayNarrative,
  ttsAvailable,
  speechLoading,
}) {
  const active = (widgets || []).filter((widget) => widget.renderStatus !== "removed");

  if (!active.length) {
    return (
      <div
        className="rounded-xl border border-dashed border-black/20 bg-white/50 p-8 text-center"
        id="main-canvas"
      >
        <p className="font-semibold text-black/55">
          Dashboard is empty. Ask the assistant to add widgets, or refresh to restore defaults.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2" id="main-canvas">
      {active.map((widget) => (
        <div className={gridClass(widget.gridPos)} key={widget.id}>
          {widget.type === "kpi-card" ? (
            <KpiWidget widget={widget} />
          ) : widget.type === "audio-text" ? (
            <InteractiveAudioCard
              block={{
                id: widget.id,
                sectionId: widget.id,
                title: widget.title,
                narrativeText: widget.content,
                audioStreamId: `${widget.id}-audio`,
                playbackLabel: "Listen to Insight",
              }}
              speechLoading={speechLoading}
              ttsAvailable={ttsAvailable}
              onPlayNarrative={onPlayNarrative}
            />
          ) : (
            <DynamicWidget appearanceSettings={chartAppearance} widget={widget} />
          )}
        </div>
      ))}
    </div>
  );
}
