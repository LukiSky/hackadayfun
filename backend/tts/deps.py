"""Lazy F5-TTS service initialization (loads model on first speak request)."""

from __future__ import annotations

import threading

from fastapi import Request

from tts.config import BACKEND_ROOT

_load_lock = threading.Lock()


def get_tts_service(request: Request):
    if not getattr(request.app.state, "tts_enabled", False):
        return None

    service = getattr(request.app.state, "tts_service", None)
    if service is not None:
        return service

    with _load_lock:
        service = getattr(request.app.state, "tts_service", None)
        if service is None:
            from tts.synthesis import create_service

            service = create_service(BACKEND_ROOT, load_model=True)
            request.app.state.tts_service = service
    return service
