"""Reference voice asset checks for startup / health."""

from __future__ import annotations

from pathlib import Path

from tts.voices.presets import CANONICAL_SPEAKER_IDS, build_preset_speakers


def reference_voice_status(project_root: Path) -> dict:
    speakers = build_preset_speakers(project_root)
    present = 0
    missing: list[str] = []
    for speaker_id in CANONICAL_SPEAKER_IDS:
        preset = speakers[speaker_id]
        path = Path(preset.reference_audio)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        if path.is_file():
            present += 1
        else:
            missing.append(speaker_id)

    return {
        "reference_voices_ready": present == len(CANONICAL_SPEAKER_IDS),
        "reference_voices_count": present,
        "reference_voices_total": len(CANONICAL_SPEAKER_IDS),
        "missing_speakers": missing,
    }
