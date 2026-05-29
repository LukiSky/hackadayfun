"""F5-TTS: text in, WAV out."""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from tts.config import BACKEND_ROOT
from tts.deps import get_tts_service
from tts.schemas import SpeakRequest, TtsHealthResponse
from tts.voices.assets import reference_voice_status
from tts.voices.presets import CANONICAL_SPEAKER_IDS

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/health")
def tts_health(request: Request):
    enabled = getattr(request.app.state, "tts_enabled", False)
    service = getattr(request.app.state, "tts_service", None)
    voices = reference_voice_status(BACKEND_ROOT)

    if not enabled:
        return {
            "enabled": False,
            "model_loaded": False,
            "device": "n/a",
            "engine": "f5-tts",
            "reference_voices_ready": voices["reference_voices_ready"],
            "reference_voices_count": voices["reference_voices_count"],
            "message": "TTS disabled. Set F5_TTS_ENABLED=1 in backend/.env and restart.",
        }

    msg = None
    if not voices["reference_voices_ready"]:
        missing = ", ".join(voices["missing_speakers"][:5])
        msg = (
            f"Reference voices incomplete ({voices['reference_voices_count']}/"
            f"{voices['reference_voices_total']}). Missing: {missing}. "
            "Copy WAVs from TTS-API-SPRINT3/assets/reference_voices/."
        )
    elif not (service and service.model_loaded):
        msg = "TTS enabled. Model loads on first speak request (may take 1–2 minutes)."

    return TtsHealthResponse(
        enabled=True,
        model_loaded=bool(service and service.model_loaded),
        device=service.device if service else "not loaded yet",
        reference_voices_ready=voices["reference_voices_ready"],
        reference_voices_count=voices["reference_voices_count"],
        message=msg,
    )


@router.get("/speakers")
def list_speakers():
    return {"speakers": list(CANONICAL_SPEAKER_IDS)}


@router.post("/speak")
async def speak(body: SpeakRequest, request: Request):
    if not getattr(request.app.state, "tts_enabled", False):
        raise HTTPException(
            status_code=503,
            detail="TTS is disabled. Set F5_TTS_ENABLED=1 in backend/.env and restart.",
        )

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        loop = asyncio.get_event_loop()
        wav_bytes = await loop.run_in_executor(
            None,
            lambda: get_tts_service(request).speak_text(
                text,
                body.speaker,
                body.emotion,
                enhance_clarity=body.enhance_clarity,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return Response(content=wav_bytes, media_type="audio/wav")
