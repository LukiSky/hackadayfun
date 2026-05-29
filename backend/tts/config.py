"""F5-TTS and backend path configuration."""

import os
from pathlib import Path

import torch
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_ROOT / ".env", override=True)


def resolve_f5_device() -> str:
    """Pick torch device; treat empty F5_TTS_DEVICE as auto-detect."""
    configured = os.environ.get("F5_TTS_DEVICE", "").strip()
    if configured:
        return configured
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

F5_TTS_MODEL_NAME: str = os.environ.get("F5_TTS_MODEL_NAME", "F5TTS_v1_Base")
F5_TTS_MODEL_CKPT: str = os.environ.get(
    "F5_TTS_MODEL_CKPT",
    "hf://SWivid/F5-TTS/F5TTS_v1_Base/model_1250000.safetensors",
)
