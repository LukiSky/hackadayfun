"""Minimal Pydantic models for F5-TTS synthesis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpeakerOverride(BaseModel):
    name: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)


class SynthesisSettings(BaseModel):
    sample_rate_hz: int = Field(default=44100, ge=8000, le=48000)
    crossfade_ms: int = Field(default=120, ge=0, le=2000)
    silence_ms_default: int = Field(default=500, ge=0, le=5000)
    normalize_loudness: bool = True
    target_lufs: float = Field(default=-16.0)
    true_peak_ceiling_db: float = Field(default=-1.0)
    cfg_scale_default: float = Field(default=2.8, ge=1.0, le=5.0)
    cfg_scale_min: float = Field(default=1.0, ge=0.5, le=5.0)
    cfg_scale_max: float = Field(default=5.0, ge=1.0, le=8.0)
    ode_solver_steps: int = Field(default=32, ge=4, le=64)


class LineRequest(BaseModel):
    speaker: str = "narrator"
    text: str = Field(..., min_length=1)
    emotion: str = "Neutral"
    cfg_scale: float | None = Field(default=None, ge=1.0, le=5.0)
    silence_ms: int | None = Field(default=None, ge=0, le=5000)


class TtsSaveRequest(BaseModel):
    lines: list[LineRequest]
    speakers: dict[str, SpeakerOverride] | None = None
    settings: SynthesisSettings | None = None
    audio_id: str | None = None
    story_id: str | None = None
    title: str | None = None


class ParsedSegment(BaseModel):
    segment_id: str
    speaker: str
    emotion: str
    cfg_scale: float
    text: str


class TtsSaveResponse(BaseModel):
    audio_id: str
    story_id: str | None = None
    title: str | None = None
    segment_count: int
    duration_seconds: float
    get_audio_url: str
    saved_path: str
    saved_relative_path: str
    parsed_segments: list[ParsedSegment]


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    speaker: str = Field(default="narrator")
    emotion: str = Field(default="Neutral")
    # When true, apply louder normalization and slightly more inference steps for demos.
    enhance_clarity: bool = Field(default=True)


class TtsHealthResponse(BaseModel):
    enabled: bool
    model_loaded: bool
    device: str
    engine: str = "f5-tts"
    reference_voices_ready: bool = False
    reference_voices_count: int = 0
    message: str | None = None
