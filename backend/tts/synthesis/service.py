from __future__ import annotations

import io
import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from cached_path import cached_path
from hydra.utils import get_class
from importlib.resources import files
from omegaconf import OmegaConf

from tts.config import F5_TTS_MODEL_CKPT, F5_TTS_MODEL_NAME, resolve_f5_device
from tts.audio.utils import (
    append_trailing_silence,
    apply_volume,
    normalize_loudness,
    resample_audio,
    save_wav,
    sequential_crossfade,
)
from tts.schemas import (
    LineRequest,
    ParsedSegment,
    SpeakerOverride,
    SynthesisSettings,
    TtsSaveRequest,
    TtsSaveResponse,
)
from tts.voices.emotions import resolve_cfg_scale
from tts.voices.presets import PresetSpeaker, build_preset_speakers, resolve_speaker_alias


def _load_audio_with_soundfile(uri: str, *args, **kwargs):
    audio, sample_rate = sf.read(uri, always_2d=True)
    return torch.from_numpy(audio.T).float(), sample_rate


torchaudio.load = _load_audio_with_soundfile

from f5_tts.infer.utils_infer import infer_process, load_model, load_vocoder, preprocess_ref_audio_text


PACKAGE_VOICE_FALLBACKS = {
    "narrator": ("infer/examples/multi/main.flac", "So when he returned to town he took the Country Mouse with him."),
    "adult_female": ("infer/examples/basic/basic_ref_en.wav", "Some call me nature, others call me mother nature."),
}


@dataclass
class ResolvedSpeaker:
    speaker_id: str
    name: str
    reference_path: Path
    reference_text: str
    speed: float
    volume: float


@dataclass
class ResolvedSegment:
    segment_id: str
    speaker_id: str
    emotion: str
    cfg_scale: float
    text: str
    silence_ms: int
    speaker: ResolvedSpeaker


class F5TtsService:
    _instance: F5TtsService | None = None
    _init_lock = threading.Lock()

    def __init__(self, project_root: Path):
        self.project_root = project_root
        default_output = (project_root / "generated_audio").resolve()
        configured = os.environ.get("F5_TTS_OUTPUT_DIR", "").strip()
        self.output_dir = Path(configured).expanduser().resolve() if configured else default_output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.preset_speakers = build_preset_speakers(project_root)
        self.device = resolve_f5_device()
        self.ode_solver_steps = int(os.environ.get("F5_TTS_ODE_SOLVER_STEPS", "32"))
        self.cuda_benchmark = os.environ.get("F5_TTS_CUDNN_BENCHMARK", "1") == "1"
        self.enable_tf32 = os.environ.get("F5_TTS_ENABLE_TF32", "1") == "1"
        self.enable_compile = os.environ.get("F5_TTS_TORCH_COMPILE", "0") == "1"
        self.compile_mode = os.environ.get("F5_TTS_TORCH_COMPILE_MODE", "reduce-overhead")
        self.model_name = F5_TTS_MODEL_NAME
        self.model_ckpt = F5_TTS_MODEL_CKPT
        self._model = None
        self._vocoder = None
        self._speaker_refs: dict[str, tuple[str, str]] = {}
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._configure_torch_runtime()

    def _configure_torch_runtime(self) -> None:
        """Enable CUDA performance flags when available."""
        if not str(self.device).startswith("cuda"):
            return

        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.benchmark = self.cuda_benchmark

        if self.enable_tf32 and hasattr(torch.backends, "cuda"):
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception:
                pass

        if hasattr(torch, "set_float32_matmul_precision"):
            try:
                torch.set_float32_matmul_precision("high")
            except Exception:
                pass

    @classmethod
    def get(cls, project_root: Path) -> F5TtsService:
        if cls._instance is not None and not str(cls._instance.device).strip():
            cls._instance = None
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls(project_root)
        return cls._instance

    @property
    def model_loaded(self) -> bool:
        return self._model is not None and self._vocoder is not None

    def _effective_device(self) -> str:
        if not str(self.device or "").strip():
            self.device = resolve_f5_device()
        return self.device

    def ensure_loaded(self) -> None:
        device = self._effective_device()
        if self.model_loaded:
            return
        with self._load_lock:
            if self.model_loaded:
                return
            self._vocoder = load_vocoder(vocoder_name="vocos", device=device)
            model_cfg = OmegaConf.load(str(files("f5_tts").joinpath(f"configs/{self.model_name}.yaml")))
            model_cls = get_class(f"f5_tts.model.{model_cfg.model.backbone}")
            ckpt_file = str(cached_path(self.model_ckpt))
            self._model = load_model(
                model_cls,
                model_cfg.model.arch,
                ckpt_file,
                mel_spec_type="vocos",
                device=device,
            )
            if self.enable_compile and hasattr(torch, "compile"):
                try:
                    self._model = torch.compile(self._model, mode=self.compile_mode)
                except Exception:
                    # Keep startup robust: fallback to eager if compile fails.
                    pass

    def _resolve_package_path(self, relative_path: str) -> str:
        return str(files("f5_tts").joinpath(relative_path))

    def _resolve_reference_path(self, speaker: ResolvedSpeaker) -> Path:
        reference = speaker.reference_path
        if reference.is_file():
            return reference

        fallback_audio, _ = PACKAGE_VOICE_FALLBACKS.get(
            speaker.speaker_id,
            PACKAGE_VOICE_FALLBACKS["narrator"],
        )
        return Path(self._resolve_package_path(fallback_audio))

    def _prepare_speaker(self, speaker: ResolvedSpeaker) -> tuple[str, str]:
        if speaker.speaker_id in self._speaker_refs:
            return self._speaker_refs[speaker.speaker_id]

        ref_audio_path = str(self._resolve_reference_path(speaker))
        ref_text = speaker.reference_text
        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_path, ref_text)
        self._speaker_refs[speaker.speaker_id] = (ref_audio, ref_text)
        return ref_audio, ref_text

    def _resolve_speaker(
        self,
        speaker_id: str,
        overrides: dict[str, SpeakerOverride] | None,
    ) -> ResolvedSpeaker:
        canonical_id = resolve_speaker_alias(speaker_id)
        override = (overrides or {}).get(speaker_id) or (overrides or {}).get(canonical_id)
        preset: PresetSpeaker | None = self.preset_speakers.get(canonical_id)

        if preset is None and override is None:
            raise ValueError(f"Unknown speaker '{speaker_id}'.")

        ref_audio = override.ref_audio if override and override.ref_audio else (preset.reference_audio if preset else None)
        ref_text = override.ref_text if override and override.ref_text else (preset.reference_text if preset else None)
        if not ref_audio or not ref_text:
            raise ValueError(f"Speaker '{speaker_id}' requires ref_audio and ref_text.")

        reference_path = Path(ref_audio)
        if not reference_path.is_absolute():
            reference_path = (self.project_root / reference_path).resolve()

        name = (override.name if override and override.name else None) or (preset.name if preset else speaker_id)
        speed = override.speed if override else (preset.speed if preset else 1.0)
        volume = override.volume if override else (preset.volume if preset else 1.0)

        return ResolvedSpeaker(
            speaker_id=canonical_id,
            name=name,
            reference_path=reference_path,
            reference_text=ref_text,
            speed=speed,
            volume=volume,
        )

    def _resolve_segments(
        self,
        request: TtsSaveRequest,
        settings: SynthesisSettings,
    ) -> list[ResolvedSegment]:
        segments: list[ResolvedSegment] = []
        speaker_cache: dict[str, ResolvedSpeaker] = {}

        for index, line in enumerate(request.lines, start=1):
            canonical_speaker = resolve_speaker_alias(line.speaker)
            if canonical_speaker not in speaker_cache:
                speaker_cache[canonical_speaker] = self._resolve_speaker(line.speaker, request.speakers)

            cfg_scale, emotion_key = resolve_cfg_scale(
                line.emotion,
                override=line.cfg_scale,
                default=settings.cfg_scale_default,
                minimum=settings.cfg_scale_min,
                maximum=settings.cfg_scale_max,
            )
            silence_ms = line.silence_ms if line.silence_ms is not None else settings.silence_ms_default

            segments.append(
                ResolvedSegment(
                    segment_id=f"SEG_{index:04d}",
                    speaker_id=canonical_speaker,
                    emotion=emotion_key,
                    cfg_scale=cfg_scale,
                    text=line.text.strip(),
                    silence_ms=silence_ms,
                    speaker=speaker_cache[canonical_speaker],
                )
            )
        return segments

    def _synthesize_segment(
        self,
        segment: ResolvedSegment,
        settings: SynthesisSettings,
    ) -> tuple[np.ndarray, int]:
        self.ensure_loaded()
        device = self._effective_device()
        ref_audio, ref_text = self._prepare_speaker(segment.speaker)

        with self._inference_lock:
            with torch.inference_mode():
                wav, sample_rate, _ = infer_process(
                    ref_audio,
                    ref_text,
                    segment.text,
                    self._model,
                    self._vocoder,
                    nfe_step=settings.ode_solver_steps,
                    cfg_strength=segment.cfg_scale,
                    speed=segment.speaker.speed,
                    device=device,
                )

        if isinstance(wav, torch.Tensor):
            audio = wav.squeeze().cpu().numpy().astype(np.float32)
        else:
            audio = np.asarray(wav).squeeze().astype(np.float32)

        audio = apply_volume(audio, segment.speaker.volume)
        audio = append_trailing_silence(audio, sample_rate, segment.silence_ms)
        return audio, sample_rate

    def synthesize_and_save(self, request: TtsSaveRequest) -> TtsSaveResponse:
        settings = request.settings or SynthesisSettings()
        segments = self._resolve_segments(request, settings)
        generated: list[np.ndarray] = []
        sample_rate = settings.sample_rate_hz

        for segment in segments:
            audio, native_rate = self._synthesize_segment(segment, settings)
            audio = resample_audio(audio, native_rate, sample_rate)
            if settings.normalize_loudness:
                audio = normalize_loudness(
                    audio,
                    sample_rate,
                    settings.target_lufs,
                    settings.true_peak_ceiling_db,
                )
            generated.append(audio)

        stitched = sequential_crossfade(generated, sample_rate, settings.crossfade_ms)
        if settings.normalize_loudness and len(generated) > 1:
            stitched = normalize_loudness(
                stitched,
                sample_rate,
                settings.target_lufs,
                settings.true_peak_ceiling_db,
            )

        audio_id = request.audio_id or str(uuid.uuid4())
        safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in audio_id)
        output_path = self.output_dir / f"{safe_id}.wav"
        save_wav(stitched, sample_rate, str(output_path))

        duration_seconds = len(stitched) / sample_rate if len(stitched) else 0.0
        parsed = [
            ParsedSegment(
                segment_id=segment.segment_id,
                speaker=segment.speaker_id,
                emotion=segment.emotion,
                cfg_scale=segment.cfg_scale,
                text=segment.text,
            )
            for segment in segments
        ]

        resolved = output_path.resolve()
        try:
            saved_relative = str(resolved.relative_to(self.project_root.resolve()))
        except ValueError:
            saved_relative = str(resolved)

        return TtsSaveResponse(
            audio_id=safe_id,
            story_id=request.story_id,
            title=request.title,
            segment_count=len(segments),
            duration_seconds=round(duration_seconds, 3),
            get_audio_url=f"/api/v1/tts/audio/{safe_id}",
            saved_path=str(resolved),
            saved_relative_path=saved_relative,
            parsed_segments=parsed,
        )

    def synthesize_to_bytes(self, request: TtsSaveRequest) -> bytes:
        """Synthesize audio and return raw WAV bytes without writing to disk."""
        settings = request.settings or SynthesisSettings()
        segments = self._resolve_segments(request, settings)
        generated: list[np.ndarray] = []
        sample_rate = settings.sample_rate_hz

        for segment in segments:
            audio, native_rate = self._synthesize_segment(segment, settings)
            audio = resample_audio(audio, native_rate, sample_rate)
            if settings.normalize_loudness:
                audio = normalize_loudness(
                    audio,
                    sample_rate,
                    settings.target_lufs,
                    settings.true_peak_ceiling_db,
                )
            generated.append(audio)

        stitched = sequential_crossfade(generated, sample_rate, settings.crossfade_ms)
        if settings.normalize_loudness and len(generated) > 1:
            stitched = normalize_loudness(
                stitched,
                sample_rate,
                settings.target_lufs,
                settings.true_peak_ceiling_db,
            )

        buf = io.BytesIO()
        sf.write(buf, stitched, sample_rate, subtype="PCM_24", format="WAV")
        return buf.getvalue()

    def get_audio_path(self, audio_id: str) -> Path:
        safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in audio_id)
        path = self.output_dir / f"{safe_id}.wav"
        if not path.is_file():
            raise FileNotFoundError(f"Audio '{audio_id}' not found.")
        return path

    def speak_text(
        self,
        text: str,
        speaker: str = "narrator",
        emotion: str = "Neutral",
        *,
        enhance_clarity: bool = True,
    ) -> bytes:
        """Single-line text-to-speech using a preset reference voice."""
        cleaned = " ".join(text.split())
        if len(cleaned) > 5000:
            cleaned = cleaned[:4997] + "…"
        settings = None
        if enhance_clarity:
            steps = int(os.environ.get("F5_TTS_SPEAK_ODE_STEPS", "40"))
            settings = SynthesisSettings(
                normalize_loudness=True,
                target_lufs=float(os.environ.get("F5_TTS_TARGET_LUFS", "-14.0")),
                true_peak_ceiling_db=-0.5,
                ode_solver_steps=min(64, max(24, steps)),
                sample_rate_hz=44100,
                silence_ms_default=200,
            )
        request = TtsSaveRequest(
            lines=[LineRequest(speaker=speaker, text=cleaned, emotion=emotion)],
            settings=settings,
        )
        return self.synthesize_to_bytes(request)

    def warmup(self) -> None:
        self.ensure_loaded()


def create_service(project_root: Path, *, load_model: bool = True) -> F5TtsService:
    service = F5TtsService.get(project_root)
    if load_model:
        service.warmup()
    return service
