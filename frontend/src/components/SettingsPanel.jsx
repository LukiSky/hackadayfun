import { Settings, X } from "lucide-react";
import {
  contextHasAudioText,
  contextHasChartTypes,
} from "../lib/activeContext.js";

function ControlLabel({ children }) {
  return (
    <span className="text-sm font-bold text-black/70">{children}</span>
  );
}

export default function SettingsPanel({
  open,
  onClose,
  activeContext,
  widgetSettings,
  onSettingChange,
  filters,
  fields,
  dates,
  onDateChange,
  onRegenerateStory,
  settingsLoading,
}) {
  const chartSettings = widgetSettings["revenue-viz"] || {};
  const storySettings = widgetSettings["revenue-story"] || {};
  const showCharts = contextHasChartTypes(activeContext);
  const showStory = contextHasAudioText(activeContext);

  if (!open) return null;

  return (
    <>
      <button
        aria-label="Close settings"
        className="fixed inset-0 z-40 bg-black/20"
        type="button"
        onClick={onClose}
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l-2 border-black bg-white shadow-2xl print-exclude"
        id="right-settings-drawer"
        data-component="settings-drawer"
      >
        <header className="border-b border-black/10 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-black/45">
                <Settings size={14} />
                Dashboard Controls
              </p>
              <h2 className="font-garage text-2xl font-black">Adjusting current view</h2>
              <p className="mt-1 text-xs font-semibold text-black/55">
                {(activeContext?.currentWidgets || []).length} widget(s) ·{" "}
                {activeContext?.activeDataSources?.[0] || "lifechanger-csv"}
              </p>
            </div>
            <button
              aria-label="Close dashboard controls"
              className="rounded-full border border-black/10 p-2 hover:bg-black/[0.04]"
              type="button"
              onClick={onClose}
            >
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {showCharts ? (
            <section className="mb-6 rounded-xl border border-black/10 bg-black/[0.02] p-4">
              <h3 className="font-garage text-lg font-black">Chart Appearance</h3>
              <div className="mt-4 grid gap-4">
                <label className="grid gap-2">
                  <ControlLabel>Color Palette</ControlLabel>
                  <select
                    className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                    value={chartSettings.theme || "Brand Colors"}
                    onChange={(event) =>
                      onSettingChange("revenue-viz", "theme", event.target.value, {
                        mutationType: "ui-only",
                      })
                    }
                  >
                    {["Monochrome", "Brand Colors", "High Contrast"].map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex items-center justify-between gap-3">
                  <ControlLabel>Show Data Labels</ControlLabel>
                  <input
                    checked={chartSettings.showDataLabels !== false}
                    type="checkbox"
                    onChange={(event) =>
                      onSettingChange(
                        "revenue-viz",
                        "showDataLabels",
                        event.target.checked,
                        { mutationType: "ui-only" },
                      )
                    }
                  />
                </label>

                <label className="grid gap-2">
                  <ControlLabel>Time Grouping</ControlLabel>
                  <select
                    className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                    value={chartSettings.xAxisInterval || "Monthly"}
                    onChange={(event) =>
                      onSettingChange(
                        "revenue-viz",
                        "xAxisInterval",
                        event.target.value,
                        { mutationType: "data-mutation" },
                      )
                    }
                  >
                    {["Daily", "Weekly", "Monthly"].map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>
          ) : null}

          {showStory ? (
            <section className="mb-6 rounded-xl border border-black/10 bg-[#FFD100]/20 p-4">
              <h3 className="font-garage text-lg font-black">Storytelling &amp; Audio</h3>
              <div className="mt-4 grid gap-4">
                <label className="grid gap-2">
                  <ControlLabel>Narrator Voice</ControlLabel>
                  <select
                    className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                    value={storySettings.voiceModel || "Professional (Female)"}
                    onChange={(event) =>
                      onSettingChange(
                        "revenue-story",
                        "voiceModel",
                        event.target.value,
                        { mutationType: "ui-only" },
                      )
                    }
                  >
                    {[
                      "Professional (Female)",
                      "Energetic (Male)",
                      "Calm (Neutral)",
                    ].map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="grid gap-2">
                  <ControlLabel>
                    Playback Speed ({storySettings.playbackSpeed ?? 1})
                  </ControlLabel>
                  <input
                    max="2"
                    min="0.5"
                    step="0.1"
                    type="range"
                    value={storySettings.playbackSpeed ?? 1}
                    onChange={(event) =>
                      onSettingChange(
                        "revenue-story",
                        "playbackSpeed",
                        Number(event.target.value),
                        { mutationType: "ui-only" },
                      )
                    }
                  />
                </label>

                <div className="grid gap-2">
                  <ControlLabel>Detail Level</ControlLabel>
                  <div className="flex flex-wrap gap-2">
                    {["Summary", "Standard", "Deep Dive"].map((level) => (
                      <button
                        className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${
                          storySettings.detailLevel === level
                            ? "border-black bg-black text-white"
                            : "border-black/15 bg-white text-black hover:bg-black/[0.04]"
                        }`}
                        disabled={settingsLoading}
                        key={level}
                        type="button"
                        onClick={() => onRegenerateStory(level)}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                  {settingsLoading ? (
                    <p className="text-xs font-semibold text-black/50">
                      Regenerating story via LangChain…
                    </p>
                  ) : null}
                </div>
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-black/10 bg-black/[0.02] p-4">
            <h3 className="font-garage text-lg font-black">Data Filters</h3>
            <div className="mt-4 grid gap-3">
              <label className="grid gap-2">
                <ControlLabel>From date</ControlLabel>
                <input
                  className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                  disabled={!fields.date}
                  max={filters.toDate || dates.max}
                  min={dates.min}
                  type="date"
                  value={filters.fromDate}
                  onChange={(event) => onDateChange("fromDate", event.target.value)}
                />
              </label>
              <label className="grid gap-2">
                <ControlLabel>To date</ControlLabel>
                <input
                  className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold"
                  disabled={!fields.date}
                  max={dates.max}
                  min={filters.fromDate || dates.min}
                  type="date"
                  value={filters.toDate}
                  onChange={(event) => onDateChange("toDate", event.target.value)}
                />
              </label>
            </div>
          </section>

          {!showCharts && !showStory ? (
            <p className="rounded-lg bg-black/[0.04] p-4 text-sm font-semibold text-black/55">
              Generate a chart or story in chat to unlock chart and audio controls.
            </p>
          ) : null}
        </div>
      </aside>
    </>
  );
}
