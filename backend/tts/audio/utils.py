from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
import torch
import torchaudio


def append_trailing_silence(audio: np.ndarray, sample_rate: int, silence_ms: int) -> np.ndarray:
    if silence_ms <= 0:
        return audio
    silence_samples = int(sample_rate * silence_ms / 1000)
    return np.concatenate([audio, np.zeros(silence_samples, dtype=audio.dtype)])


def apply_volume(audio: np.ndarray, gain: float) -> np.ndarray:
    if gain == 1.0:
        return audio
    return np.clip(audio * gain, -1.0, 1.0)


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return audio
    tensor = torch.from_numpy(audio).unsqueeze(0).float()
    resampled = torchaudio.functional.resample(tensor, source_rate, target_rate)
    return resampled.squeeze(0).numpy()


def sequential_crossfade(segments: list[np.ndarray], sample_rate: int, crossfade_ms: int) -> np.ndarray:
    if not segments:
        return np.array([], dtype=np.float32)
    if len(segments) == 1:
        return segments[0]

    crossfade_samples = int(sample_rate * crossfade_ms / 1000)
    if crossfade_samples <= 0:
        return np.concatenate(segments)

    output = segments[0].copy()
    for next_segment in segments[1:]:
        if len(output) < crossfade_samples or len(next_segment) < crossfade_samples:
            output = np.concatenate([output, next_segment])
            continue

        fade_out = np.linspace(1.0, 0.0, crossfade_samples, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, crossfade_samples, dtype=np.float32)
        overlap = output[-crossfade_samples:] * fade_out + next_segment[:crossfade_samples] * fade_in
        output = np.concatenate([output[:-crossfade_samples], overlap, next_segment[crossfade_samples:]])
    return output


def _apply_peak_ceiling(audio: np.ndarray, true_peak_ceiling_db: float) -> np.ndarray:
    peak_limit = 10 ** (true_peak_ceiling_db / 20.0)
    peak = np.max(np.abs(audio))
    if peak > peak_limit:
        audio = audio * (peak_limit / peak)
    return audio.astype(np.float32)


def normalize_loudness(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float,
    true_peak_ceiling_db: float,
) -> np.ndarray:
    if len(audio) < sample_rate * 0.35:
        rms = np.sqrt(np.mean(audio**2))
        if rms > 1e-8:
            target_rms = 10 ** ((target_lufs + 3.0) / 20.0) * 0.12
            audio = audio * (target_rms / rms)
        return _apply_peak_ceiling(audio, true_peak_ceiling_db)

    meter = pyln.Meter(sample_rate)
    loudness = meter.integrated_loudness(audio)
    if np.isinf(loudness):
        return _apply_peak_ceiling(audio, true_peak_ceiling_db)

    normalized = pyln.normalize.loudness(audio, loudness, target_lufs)
    return _apply_peak_ceiling(normalized, true_peak_ceiling_db)


def save_wav(audio: np.ndarray, sample_rate: int, output_path: str, bit_depth: str = "PCM_24") -> None:
    subtype = "PCM_24" if "24" in bit_depth else "PCM_16"
    sf.write(output_path, audio, sample_rate, subtype=subtype)
