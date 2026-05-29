from __future__ import annotations

"""Emotion normalization for a fixed 5-emotion catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionProfile:
    emotion_id: int
    cfg_scale: float
    description: str


EMOTION_DICT: dict[str, int] = {
    "Angry": 1,
    "Neutral": 2,
    "Sad": 3,
    "Surprise": 4,
    "Happy": 5,
}

EMOTION_PROFILES: dict[str, EmotionProfile] = {
    "Angry": EmotionProfile(1, 3.7, "Strong, forceful delivery."),
    "Neutral": EmotionProfile(2, 2.0, "Clear, even delivery."),
    "Sad": EmotionProfile(3, 2.9, "Soft and sorrowful delivery."),
    "Surprise": EmotionProfile(4, 3.4, "Startled/reactive delivery."),
    "Happy": EmotionProfile(5, 3.1, "Bright, upbeat delivery."),
}

EMOTION_ALIASES: dict[str, str] = {
    "angry": "Angry",
    "anger": "Angry",
    "aggressive": "Angry",
    "furious": "Angry",
    "mad": "Angry",
    "neutral": "Neutral",
    "narrative": "Neutral",
    "scene_set": "Neutral",
    "scene-set": "Neutral",
    "calm": "Neutral",
    "sad": "Sad",
    "melancholy": "Sad",
    "fear": "Sad",
    "fearful": "Sad",
    "terrified": "Sad",
    "surprise": "Surprise",
    "surprised": "Surprise",
    "curious": "Surprise",
    "shocked": "Surprise",
    "happy": "Happy",
    "excited": "Happy",
    "cheerful": "Happy",
    "warm": "Happy",
}


def normalize_emotion_key(emotion: str) -> str:
    normalized = emotion.strip().lower().replace("-", "_").replace(" ", "_")
    return EMOTION_ALIASES.get(normalized, "Neutral")


def resolve_cfg_scale(
    emotion: str,
    *,
    override: float | None = None,
    default: float = 2.8,
    minimum: float = 1.0,
    maximum: float = 5.0,
) -> tuple[float, str]:
    if override is not None:
        clamped = max(minimum, min(float(override), maximum))
        return clamped, normalize_emotion_key(emotion)

    key = normalize_emotion_key(emotion)
    profile = EMOTION_PROFILES.get(key)
    if profile is None:
        clamped = max(minimum, min(default, maximum))
        return clamped, "Neutral"

    clamped = max(minimum, min(profile.cfg_scale, maximum))
    return clamped, key


def list_supported_emotions() -> list[dict[str, str | float]]:
    items: list[dict[str, str | float]] = []
    for emotion, profile in EMOTION_PROFILES.items():
        items.append(
            {
                "emotion": emotion,
                "emotion_id": profile.emotion_id,
                "cfg_scale": profile.cfg_scale,
                "description": profile.description,
            }
        )
    return sorted(items, key=lambda item: int(item["emotion_id"]))
