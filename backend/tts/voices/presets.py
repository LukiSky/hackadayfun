from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CANONICAL_SPEAKER_IDS = (
    "narrator",
    "childMale1",
    "childMale2",
    "childMale3",
    "childFemale1",
    "childFemale2",
    "childFemale3",
    "adultMale1",
    "adultMale2",
    "adultMale3",
    "adultFemale1",
    "adultFemale2",
    "adultFemale3",
    "oldMale1",
    "oldMale2",
    "oldFemale1",
    "oldFemale2",
)


@dataclass(frozen=True)
class PresetSpeaker:
    speaker_id: str
    name: str
    reference_audio: str
    reference_text: str
    speed: float = 1.0
    volume: float = 1.0
    age_group: str = ""
    gender: str = ""


SPEAKER_ALIASES: dict[str, str] = {
    "narrator": "narrator",
    "narator": "narrator",
    "storyteller": "narrator",
    "childmale1": "childMale1",
    "child_male_1": "childMale1",
    "childmale2": "childMale2",
    "child_male_2": "childMale2",
    "childmale3": "childMale3",
    "child_male_3": "childMale3",
    "childfemale1": "childFemale1",
    "child_female_1": "childFemale1",
    "childfemale2": "childFemale2",
    "child_female_2": "childFemale2",
    "childfemale3": "childFemale3",
    "child_female_3": "childFemale3",
    "adultmale1": "adultMale1",
    "adult_male_1": "adultMale1",
    "adultmale2": "adultMale2",
    "adult_male_2": "adultMale2",
    "adultmale3": "adultMale3",
    "adult_male_3": "adultMale3",
    "adultfemale1": "adultFemale1",
    "adult_female_1": "adultFemale1",
    "adultfemale2": "adultFemale2",
    "adult_female_2": "adultFemale2",
    "adultfemale3": "adultFemale3",
    "adult_female_3": "adultFemale3",
    "oldmale1": "oldMale1",
    "old_male_1": "oldMale1",
    "oldmale": "oldMale1",
    "old_man1": "oldMale1",
    "oldman1": "oldMale1",
    "oldmale2": "oldMale2",
    "old_male_2": "oldMale2",
    "old_man2": "oldMale2",
    "oldman2": "oldMale2",
    "oldfemale1": "oldFemale1",
    "old_female_1": "oldFemale1",
    "oldfemale": "oldFemale1",
    "old_female": "oldFemale1",
    "grandma1": "oldFemale1",
    "grandma_1": "oldFemale1",
    "oldfemale2": "oldFemale2",
    "old_female_2": "oldFemale2",
    "grandma2": "oldFemale2",
    "grandma_2": "oldFemale2",
    # Legacy ids
    "adult_female": "adultFemale1",
    "adult_male": "adultMale1",
    "child_female": "childFemale1",
    "child_male": "childMale1",
}


def normalize_speaker_key(speaker: str) -> str:
    return speaker.strip().lower().replace("-", "_").replace(" ", "_")


def resolve_speaker_alias(speaker: str) -> str:
    raw = speaker.strip()
    if raw in CANONICAL_SPEAKER_IDS:
        return raw
    key = normalize_speaker_key(raw)
    canonical = SPEAKER_ALIASES.get(key)
    if canonical is None:
        compact = key.replace("_", "")
        for alias, target in SPEAKER_ALIASES.items():
            if alias.replace("_", "") == compact:
                return target
        allowed = ", ".join(CANONICAL_SPEAKER_IDS)
        raise ValueError(f"Unknown speaker '{speaker}'. Use one of: {allowed}")
    return canonical


def _voices_dir(project_root: Path) -> Path:
    return project_root / "assets" / "reference_voices"


# F5-TTS: speed < 1.0 = slower delivery. Narrator kept as-is; characters slowed and staggered.
SPEAKER_DELIVERY: dict[str, tuple[float, float]] = {
    "narrator": (0.95, 1.0),
    "childMale1": (0.80, 0.98),
    "childMale2": (0.76, 0.94),
    "childMale3": (0.76, 0.94),
    "childFemale1": (0.82, 1.0),
    "childFemale2": (0.77, 0.96),
    "childFemale3": (0.77, 0.96),
    "adultMale1": (0.86, 0.98),
    "adultMale2": (0.83, 0.94),
    "adultMale3": (0.83, 0.94),
    "adultFemale1": (0.85, 1.0),
    "adultFemale2": (0.81, 0.96),
    "adultFemale3": (0.81, 0.96),
    "oldMale1": (0.78, 0.95),
    "oldMale2": (0.74, 0.92),
    "oldFemale1": (0.76, 0.96),
    "oldFemale2": (0.72, 0.93),
}


def build_preset_speakers(project_root: Path) -> dict[str, PresetSpeaker]:
    voices = _voices_dir(project_root)

    return {
        "narrator": PresetSpeaker(
            speaker_id="narrator",
            name="Narrator",
            age_group="adult",
            gender="male",
            reference_audio=str(voices / "narrator.wav"),
            reference_text="Some call me nature. Others call me Mother Nature.",
            speed=SPEAKER_DELIVERY["narrator"][0],
            volume=SPEAKER_DELIVERY["narrator"][1],
        ),
        "childMale1": PresetSpeaker(
            speaker_id="childMale1",
            name="Child Male 1",
            age_group="child",
            gender="male",
            reference_audio=str(voices / "childMale1.wav"),
            reference_text=(
                "I do know the Lamy Lamy dance, but everybody can't really do it without a lamb costume."
            ),
            speed=SPEAKER_DELIVERY["childMale1"][0],
            volume=SPEAKER_DELIVERY["childMale1"][1],
        ),
        "childMale2": PresetSpeaker(
            speaker_id="childMale2",
            name="Child Male 2",
            age_group="child",
            gender="male",
            reference_audio=str(voices / "childMale2.wav"),
            reference_text=(
                "Everyone is here, so it's been a long time. Sorry! Sorry, sorry. "
                "Uzumaki Nalt is... Bagger! I'm going to defeat you! Yes."
            ),
            speed=SPEAKER_DELIVERY["childMale2"][0],
            volume=SPEAKER_DELIVERY["childMale2"][1],
        ),
        "childMale3": PresetSpeaker(
            speaker_id="childMale3",
            name="Child Male 3",
            age_group="child",
            gender="male",
            reference_audio=str(voices / "childMale3.wav"),
            reference_text=(
                "Everyone is here, so it's been a long time. Sorry! Sorry, sorry. "
                "Uzumaki Nalt is... Bagger! I'm going to defeat you! Yes."
            ),
            speed=SPEAKER_DELIVERY["childMale3"][0],
            volume=SPEAKER_DELIVERY["childMale3"][1],
        ),
        "childFemale1": PresetSpeaker(
            speaker_id="childFemale1",
            name="Child Female 1",
            age_group="child",
            gender="female",
            reference_audio=str(voices / "childFemale1.wav"),
            reference_text=(
                "or Wizard Bill's music shop is? I can't find it anywhere. "
                "He's got a guitar that plays the most savory, licks and ooo."
            ),
            speed=SPEAKER_DELIVERY["childFemale1"][0],
            volume=SPEAKER_DELIVERY["childFemale1"][1],
        ),
        "childFemale2": PresetSpeaker(
            speaker_id="childFemale2",
            name="Child Female 2",
            age_group="child",
            gender="female",
            reference_audio=str(voices / "childFemale2.wav"),
            reference_text=(
                "I love you dad, but we don't even know if the kid's gonna be a vampire. "
                "I'd be thrilled if the baby's human-"
            ),
            speed=SPEAKER_DELIVERY["childFemale2"][0],
            volume=SPEAKER_DELIVERY["childFemale2"][1],
        ),
        "childFemale3": PresetSpeaker(
            speaker_id="childFemale3",
            name="Child Female 3",
            age_group="child",
            gender="female",
            reference_audio=str(voices / "childFemale3.wav"),
            reference_text=(
                "I love you dad, but we don't even know if the kid's gonna be a vampire. "
                "I'd be thrilled if the baby's human-"
            ),
            speed=SPEAKER_DELIVERY["childFemale3"][0],
            volume=SPEAKER_DELIVERY["childFemale3"][1],
        ),
        "adultMale1": PresetSpeaker(
            speaker_id="adultMale1",
            name="Adult Male 1",
            age_group="adult",
            gender="male",
            reference_audio=str(voices / "adultMale1.wav"),
            reference_text=(
                "Allow me to introduce myself. Think, predator and local goose expert, "
                "which I know you could use about now."
            ),
            speed=SPEAKER_DELIVERY["adultMale1"][0],
            volume=SPEAKER_DELIVERY["adultMale1"][1],
        ),
        "adultMale2": PresetSpeaker(
            speaker_id="adultMale2",
            name="Adult Male 2",
            age_group="adult",
            gender="male",
            reference_audio=str(voices / "adultMale2.wav"),
            reference_text=(
                "Allow me to introduce myself. Think, predator, and local goose expert, "
                "which I know you could use about now. Here you go."
            ),
            speed=SPEAKER_DELIVERY["adultMale2"][0],
            volume=SPEAKER_DELIVERY["adultMale2"][1],
        ),
        "adultMale3": PresetSpeaker(
            speaker_id="adultMale3",
            name="Adult Male 3",
            age_group="adult",
            gender="male",
            reference_audio=str(voices / "adultMale3.wav"),
            reference_text=(
                "Allow me to introduce myself. Think, predator, and local goose expert, "
                "which I know you could use about now. Here you go."
            ),
            speed=SPEAKER_DELIVERY["adultMale3"][0],
            volume=SPEAKER_DELIVERY["adultMale3"][1],
        ),
        "adultFemale1": PresetSpeaker(
            speaker_id="adultFemale1",
            name="Adult Female 1",
            age_group="adult",
            gender="female",
            reference_audio=str(voices / "adultFemale1.wav"),
            reference_text=(
                "Oh, Pelington, please be careful. That's Mrs. Bards' especially powerful radio."
            ),
            speed=SPEAKER_DELIVERY["adultFemale1"][0],
            volume=SPEAKER_DELIVERY["adultFemale1"][1],
        ),
        "adultFemale2": PresetSpeaker(
            speaker_id="adultFemale2",
            name="Adult Female 2",
            age_group="adult",
            gender="female",
            reference_audio=str(voices / "adultFemale2.wav"),
            reference_text=(
                "I am not scared. I've thought where we'll send ghosts. But in the end I know "
                "we usually unmask them and it's just a shrilly little scared man inside."
            ),
            speed=SPEAKER_DELIVERY["adultFemale2"][0],
            volume=SPEAKER_DELIVERY["adultFemale2"][1],
        ),
        "adultFemale3": PresetSpeaker(
            speaker_id="adultFemale3",
            name="Adult Female 3",
            age_group="adult",
            gender="female",
            reference_audio=str(voices / "adultFemale3.wav"),
            reference_text=(
                "I am not scared. I've thought where we'll send ghosts. But in the end I know "
                "we usually unmask them and it's just a shrilly little scared man inside."
            ),
            speed=SPEAKER_DELIVERY["adultFemale3"][0],
            volume=SPEAKER_DELIVERY["adultFemale3"][1],
        ),
        "oldMale1": PresetSpeaker(
            speaker_id="oldMale1",
            name="Old Male 1",
            age_group="elder",
            gender="male",
            reference_audio=str(voices / "oldMale1.wav"),
            reference_text=(
                "What do I do now, really? Ready as I'll ever be. Would you do me a favor and take this? "
                "I'll meet you at the van in just a minute."
            ),
            speed=SPEAKER_DELIVERY["oldMale1"][0],
            volume=SPEAKER_DELIVERY["oldMale1"][1],
        ),
        "oldMale2": PresetSpeaker(
            speaker_id="oldMale2",
            name="Old Male 2",
            age_group="elder",
            gender="male",
            reference_audio=str(voices / "oldMale1.wav"),
            reference_text=(
                "What do I do now, really? Ready as I'll ever be. Would you do me a favor and take this? "
                "I'll meet you at the van in just a minute."
            ),
            speed=SPEAKER_DELIVERY["oldMale2"][0],
            volume=SPEAKER_DELIVERY["oldMale2"][1],
        ),
        "oldFemale1": PresetSpeaker(
            speaker_id="oldFemale1",
            name="Old Female 1",
            age_group="elder",
            gender="female",
            reference_audio=str(voices / "oldFemale1.wav"),
            reference_text="Oh, yuck! Oh, dear! Oh, my! This is the limit! Heaven's to Betsey!",
            speed=SPEAKER_DELIVERY["oldFemale1"][0],
            volume=SPEAKER_DELIVERY["oldFemale1"][1],
        ),
        "oldFemale2": PresetSpeaker(
            speaker_id="oldFemale2",
            name="Old Female 2",
            age_group="elder",
            gender="female",
            reference_audio=str(voices / "oldFemale1.wav"),
            reference_text="Oh, yuck! Oh, dear! Oh, my! This is the limit! Heaven's to Betsey!",
            speed=SPEAKER_DELIVERY["oldFemale2"][0],
            volume=SPEAKER_DELIVERY["oldFemale2"][1],
        ),
    }


def list_preset_speakers(project_root: Path) -> list[dict[str, str]]:
    presets = build_preset_speakers(project_root)
    return [
        {
            "speaker": speaker.speaker_id,
            "name": speaker.name,
            "age": speaker.age_group,
            "gender": speaker.gender,
            "speed": speaker.speed,
            "volume": speaker.volume,
            "reference_audio": speaker.reference_audio,
        }
        for speaker in presets.values()
    ]
