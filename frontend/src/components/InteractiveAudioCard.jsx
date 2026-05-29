import { useState } from "react";
import { PlayCircle, Volume2 } from "lucide-react";

export default function InteractiveAudioCard({
  block,
  onPlayNarrative,
  ttsAvailable,
  speechLoading,
}) {
  const [playing, setPlaying] = useState(false);

  async function handlePlay() {
    if (!block?.narrativeText?.trim() || !onPlayNarrative) return;
    setPlaying(true);
    try {
      await onPlayNarrative(block.narrativeText);
    } finally {
      setPlaying(false);
    }
  }

  return (
    <article
      className="audio-player rounded-xl border border-black/10 bg-[#FFD100]/30 p-4"
      data-component="audio-player"
      id={block.sectionId || "revenue-story"}
    >
      <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-garage text-xl font-black text-black">
          {block.title || "Key Insights"}
        </h3>
        <button
          aria-label={block.playbackLabel || "Listen to Insight"}
          className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-black px-4 py-2 text-sm font-bold text-white transition hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!ttsAvailable || speechLoading || playing}
          type="button"
          onClick={handlePlay}
        >
          <PlayCircle size={18} />
          {speechLoading || playing ? "Playing…" : block.playbackLabel || "Listen to Insight"}
        </button>
      </header>

      <div className="rounded-lg bg-white/80 p-4 text-sm leading-7 text-black/80">
        {block.narrativeText?.split("\n\n").map((paragraph, index) => (
          <p className={index ? "mt-4" : ""} key={index}>
            {paragraph}
          </p>
        ))}
      </div>

      <audio
        className="sr-only"
        id={block.audioStreamId || "revenue-audio-stream"}
        preload="auto"
      />

      {!ttsAvailable ? (
        <p className="mt-2 flex items-center gap-2 text-xs font-semibold text-black/50">
          <Volume2 size={14} />
          Speech service unavailable — read the narrative above.
        </p>
      ) : null}
    </article>
  );
}
