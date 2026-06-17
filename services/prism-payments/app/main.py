"""
PRISM Payments Service

Basit ödeme / bakiye API'si.
- Monero node durumunu sorgular
- Kullanıcı bakiyelerini yönetir (PostgreSQL)
- Ödeme talepleri oluşturur

Not: Bu servis ilk etapta placeholder/altyapı niteliğindedir.
Gerçek para transferleri için Monero cüzdan yönetimi (monero-wallet-rpc)
ve/veya Breez SDK entegrasyonu gereklidir.
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import psycopg2
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ortam değişkenleri
# ---------------------------------------------------------------------------
MONEROD_RPC_URL = os.environ.get("MONEROD_RPC_URL", "http://monerod:18089")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgres://synapse:synapse@db:5432/payments?sslmode=disable",
)
BREEZ_API_KEY = os.environ.get("BREEZ_API_KEY", "")


# ---------------------------------------------------------------------------
# Veritabanı başlatma
# ---------------------------------------------------------------------------
def _ensure_database_exists():
    """payments veritabanı yoksa oluşturur."""
    try:
        # Veritabanı adını postgres olarak değiştirerek yönetim bağlantısı kur
        admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True
        cur = conn.cursor()
        db_name = DATABASE_URL.rsplit("/", 1)[-1].split("?", 1)[0]
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s;",
            (db_name,),
        )
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db_name};")
            print(f"✅ Veritabanı oluşturuldu: {db_name}")
        cur.close()
        conn.close()
    except Exception as exc:
        print(f"⚠️  DB ensure warning (non-fatal): {exc}")


def init_db():
    """Gerekli tabloları oluşturur."""
    _ensure_database_exists()
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id VARCHAR(255) PRIMARY KEY,
                xmr_balance VARCHAR(40) NOT NULL DEFAULT '0.000000000000',
                lightning_balance_msat BIGINT NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_intents (
                id UUID PRIMARY KEY,
                sender_id VARCHAR(255),
                recipient_id VARCHAR(255),
                amount_xmr VARCHAR(40),
                memo TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        print(f"⚠️  DB init warning (non-fatal): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PRISM Payments",
    description="PRISM uygulaması için ödeme ve bakiye servisi.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Pydantic modelleri
# ---------------------------------------------------------------------------
class BalanceResponse(BaseModel):
    user_id: str
    xmr_balance: str
    lightning_balance_msat: int
    updated_at: Optional[str] = None


class PaymentIntentRequest(BaseModel):
    sender_id: Optional[str] = None
    recipient_id: str
    amount_xmr: str = Field(..., pattern=r"^\d+(\.\d+)?$")
    memo: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    id: str
    sender_id: Optional[str]
    recipient_id: str
    amount_xmr: str
    status: str
    created_at: str


class MoneroStatusResponse(BaseModel):
    height: int
    target_height: int
    synchronized: bool
    outgoing_connections: int
    incoming_connections: int
    version: str


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# ---------------------------------------------------------------------------
# API endpoint'leri
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "prism-payments"}


@app.get("/balance/{user_id}", response_model=BalanceResponse)
def get_balance(user_id: str):
    """Kullanıcı bakiyesini getir."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_balances (user_id, xmr_balance, lightning_balance_msat)
        VALUES (%s, '0.000000000000', 0)
        ON CONFLICT (user_id) DO NOTHING;
        """,
        (user_id,),
    )
    conn.commit()
    cur.execute(
        "SELECT user_id, xmr_balance, lightning_balance_msat, updated_at FROM user_balances WHERE user_id = %s;",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return BalanceResponse(
        user_id=row[0],
        xmr_balance=str(row[1]),
        lightning_balance_msat=row[2],
        updated_at=row[3].isoformat() if row[3] else None,
    )


@app.post("/payment/intent", response_model=PaymentIntentResponse)
def create_payment_intent(payload: PaymentIntentRequest):
    """Yeni ödeme talebi oluştur."""
    payment_id = uuid.uuid4()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO payment_intents (id, sender_id, recipient_id, amount_xmr, memo, status)
        VALUES (%s, %s, %s, %s, %s, 'pending');
        """,
        (
            str(payment_id),
            payload.sender_id,
            payload.recipient_id,
            payload.amount_xmr,
            payload.memo,
        ),
    )
    conn.commit()
    cur.execute(
        "SELECT id, sender_id, recipient_id, amount_xmr, status, created_at FROM payment_intents WHERE id = %s;",
        (str(payment_id),),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    return PaymentIntentResponse(
        id=str(row[0]),
        sender_id=row[1],
        recipient_id=row[2],
        amount_xmr=str(row[3]),
        status=row[4],
        created_at=row[5].isoformat(),
    )


@app.get("/payment/intent/{payment_id}", response_model=PaymentIntentResponse)
def get_payment_intent(payment_id: str):
    """Ödeme talebi durumunu getir."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, sender_id, recipient_id, amount_xmr, status, created_at FROM payment_intents WHERE id = %s;",
        (payment_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    return PaymentIntentResponse(
        id=str(row[0]),
        sender_id=row[1],
        recipient_id=row[2],
        amount_xmr=str(row[3]),
        status=row[4],
        created_at=row[5].isoformat(),
    )


@app.get("/monero/status", response_model=MoneroStatusResponse)
def monero_status():
    """Monero node senkronizasyon durumunu getir."""
    try:
        resp = requests.post(
            f"{MONEROD_RPC_URL}/json_rpc",
            json={
                "jsonrpc": "2.0",
                "id": "0",
                "method": "sync_info",
            },
            timeout=10,
        )
        data = resp.json()
        result = data.get("result", {})
        height = result.get("height", 0)
        target_height = result.get("target_height", height)
        return MoneroStatusResponse(
            height=height,
            target_height=target_height,
            synchronized=height >= target_height and target_height > 0,
            outgoing_connections=result.get("outgoing_connections_count", 0),
            incoming_connections=result.get("incoming_connections_count", 0),
            version=result.get("version", "unknown"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Monero node bağlantı hatası: {exc}",
        ) from exc


@app.get("/config")
def get_config():
    """Ödeme servisi yapılandırma özetini döndür."""
    return {
        "monero_rpc": MONEROD_RPC_URL,
        "lightning_enabled": bool(BREEZ_API_KEY),
        "features": [
            "balance_query",
            "payment_intents",
            "monero_status",
        ],
    }
