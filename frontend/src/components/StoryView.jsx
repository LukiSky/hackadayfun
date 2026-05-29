import { useState } from "react";
import { generateStory } from "../api/client.js";

export default function StoryView() {
  const [theme, setTheme] = useState("");
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const result = await generateStory(theme || undefined);
      setStory(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold">Generate impact story</h2>
        <p className="mt-1 text-sm text-slate-600">
          Ethical, de-identified narrative from mock participant feedback.
        </p>
        <label className="mt-4 block text-sm font-medium">Optional theme</label>
        <input
          className="input mt-1 max-w-md"
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          placeholder="e.g. confidence, belonging"
        />
        <button type="button" className="btn-primary mt-4" onClick={handleGenerate} disabled={loading}>
          {loading ? "Writing…" : "Generate story"}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {story && (
        <div className="card border-brand-100 bg-brand-50/30">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{story.story}</div>
          <ul className="mt-4 list-inside list-disc text-xs text-slate-500">
            {story.citations.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
