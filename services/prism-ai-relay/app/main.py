"""
PRISM AI Relay Service

WhatsApp bridge üzerinden Meta AI ile yapılan konuşmaları PRISM içinde
ayrı bir Matrix room'una (örn. @metaai:server) yönlendirir.

Not: Bu servis şu anda altyapı/placeholder durumundadır.
Tam entegrasyon için:
  1. Matrix bot kullanıcısı oluşturulmalı
  2. WhatsApp bridge event'leri dinlenmeli
  3. Meta AI mesajları ayıklanıp bot üzerinden Matrix room'una aktarılmalı
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

MATRIX_HOMESERVER = os.environ.get("MATRIX_HOMESERVER", "http://synapse:8008")
MATRIX_USER = os.environ.get("MATRIX_AI_USER", "")
MATRIX_PASSWORD = os.environ.get("MATRIX_AI_PASSWORD", "")
META_AI_ROOM_NAME = os.environ.get("META_AI_ROOM_NAME", "Meta AI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # İlk etapta bot login ve room oluşturma burada yapılabilir.
    # Şimdilik sadece sağlık kontrolü.
    yield


app = FastAPI(
    title="PRISM AI Relay",
    description="WhatsApp/Meta AI entegrasyon relay servisi.",
    version="0.1.0",
    lifespan=lifespan,
)


class RelayStatus(BaseModel):
    status: str
    homeserver: str
    bot_configured: bool
    room_name: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "prism-ai-relay"}


@app.get("/status", response_model=RelayStatus)
def status():
    return RelayStatus(
        status="placeholder",
        homeserver=MATRIX_HOMESERVER,
        bot_configured=bool(MATRIX_USER and MATRIX_PASSWORD),
        room_name=META_AI_ROOM_NAME,
    )


@app.post("/webhook/whatsapp")
def whatsapp_webhook(payload: dict):
    """
    WhatsApp bridge'den gelen event'leri kabul eder.
    Gelecekte burada Meta AI mesajları filtrelenip Matrix room'una aktarılacak.
    """
    return {
        "received": True,
        "note": "AI relay processing is not yet implemented in this placeholder.",
    }
