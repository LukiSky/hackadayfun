/** Shared browser playback for TTS WAV blobs — tuned for clarity. */

const MAX_TTS_CHARS = 1200;

export function prepareTextForTts(text) {
  if (!text?.trim()) return "";
  let cleaned = text
    .replace(/\s+/g, " ")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[#*_`]/g, "")
    .trim();
  if (cleaned.length > MAX_TTS_CHARS) {
    const slice = cleaned.slice(0, MAX_TTS_CHARS);
    const lastStop = Math.max(slice.lastIndexOf(". "), slice.lastIndexOf("! "), slice.lastIndexOf("? "));
    cleaned = (lastStop > 200 ? slice.slice(0, lastStop + 1) : slice).trim() + "…";
  }
  return cleaned;
}

/**
 * @param {Blob} blob - WAV from /api/tts/speak
 * @param {{ playbackRate?: number, volume?: number, onEnded?: () => void }} options
 * @returns {Promise<HTMLAudioElement>}
 */
export function playTtsBlob(blob, { playbackRate = 0.98, volume = 1, onEnded } = {}) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.volume = Math.min(1, Math.max(0, volume));
    audio.playbackRate = playbackRate;
    audio.preservesPitch = true;

    const cleanup = () => {
      URL.revokeObjectURL(url);
      onEnded?.();
    };

    audio.onended = () => {
      cleanup();
      resolve(audio);
    };
    audio.onerror = () => {
      cleanup();
      reject(new Error("Audio playback failed"));
    };

    audio.play().then(() => resolve(audio)).catch(reject);
  });
}
