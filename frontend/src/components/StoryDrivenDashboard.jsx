import DynamicWidget from "./DynamicWidget.jsx";
import InteractiveAudioCard from "./InteractiveAudioCard.jsx";

export default function StoryDrivenDashboard({
  visualizations,
  storytellingBlocks,
  chartAppearance,
  onPlayNarrative,
  ttsAvailable,
  speechLoading,
}) {
  const blocks = storytellingBlocks || [];
  const vizList = visualizations || [];

  if (!blocks.length && !vizList.length) {
    return null;
  }

  return (
    <section className="grid gap-5" id="story-driven-dashboard">
      {vizList.map((viz) => (
        <div id={viz.sectionId || "revenue-viz"} key={viz.id}>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            Chart section · {viz.engine}
          </p>
          <DynamicWidget appearanceSettings={chartAppearance} widget={viz.chartConfig} />
        </div>
      ))}

      {blocks.map((block) => (
        <InteractiveAudioCard
          block={block}
          key={block.id}
          speechLoading={speechLoading}
          ttsAvailable={ttsAvailable}
          onPlayNarrative={onPlayNarrative}
        />
      ))}
    </section>
  );
}
