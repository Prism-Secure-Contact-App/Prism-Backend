#!/usr/bin/env python3
"""
PRISM Monero API Wrapper

A lightweight FastAPI service that wraps monero-wallet-rpc to provide:
- GET /balance          -> XMR balance + USD equivalent
- GET /deposit          -> Fresh deposit subaddress
- POST /withdraw        -> Send XMR to an address

Requires env vars:
  MONERO_WALLET_RPC_URL  - default http://monero-wallet-rpc:18083/json_rpc
  PRISM_MONERO_API_PORT  - default 18084
  COINGECKO_API_URL      - default https://api.coingecko.com/api/v3
"""

import os
import sys
import json
import httpx
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("prism-monero-api")

app = FastAPI(title="PRISM Monero API", version="1.0.0")

WALLET_RPC_URL = os.environ.get("MONERO_WALLET_RPC_URL", "http://monero-wallet-rpc:18083/json_rpc")
COINGECKO_URL = os.environ.get("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")


# ─── Helpers ────────────────────────────────────────────────────────────────

async def _wallet_rpc(method: str, params: dict = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": "0", "method": method}
    if params:
        payload["params"] = params
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(WALLET_RPC_URL, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise HTTPException(status_code=500, detail=f"Wallet RPC error: {data['error']}")
            return data.get("result", {})
        except httpx.RequestError as exc:
            log.error("Wallet RPC unreachable: %s", exc)
            raise HTTPException(status_code=503, detail="Monero wallet RPC unreachable")


async def _get_xmr_usd_rate() -> float:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{COINGECKO_URL}/simple/price",
                params={"ids": "monero", "vs_currencies": "usd"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data["monero"]["usd"])
    except Exception as exc:
        log.warning("Failed to fetch XMR/USD rate: %s", exc)
        return 0.0


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "prism-monero-api", "version": "1.0.0"}


@app.get("/balance")
async def get_balance():
    """
    Get the wallet balance.
    Returns unlocked balance, total balance, and USD equivalent.
    """
    result = await _wallet_rpc("get_balance", {"account_index": 0})
    balance_atomic = result.get("balance", 0)
    unlocked_atomic = result.get("unlocked_balance", 0)
    
    xmr_total = balance_atomic / 1e12
    xmr_unlocked = unlocked_atomic / 1e12
    
    usd_rate = await _get_xmr_usd_rate()
    usd_total = round(xmr_total * usd_rate, 2)
    usd_unlocked = round(xmr_unlocked * usd_rate, 2)
    
    return {
        "xmr_total": xmr_total,
        "xmr_unlocked": xmr_unlocked,
        "usd_total": usd_total,
        "usd_unlocked": usd_unlocked,
        "usd_rate": usd_rate,
        "currency": "USD",
    }


@app.get("/deposit")
async def get_deposit_address():
    """
    Generate a fresh subaddress for deposit.
    Returns the new subaddress and its index.
    """
    result = await _wallet_rpc("create_address", {"account_index": 0})
    address = result.get("address", "")
    address_index = result.get("address_index", 0)
    
    log.info("Generated deposit subaddress: %s (index %d)", address, address_index)
    return {
        "address": address,
        "address_index": address_index,
        "account_index": 0,
    }


class WithdrawRequest(BaseModel):
    destination: str
    amount: float  # in XMR
    payment_id: Optional[str] = None


@app.post("/withdraw")
async def withdraw(req: WithdrawRequest):
    """
    Withdraw XMR to an external address.
    Amount is specified in XMR (e.g., 0.5).
    """
    amount_atomic = int(req.amount * 1e12)
    if amount_atomic <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    destinations = [{"amount": amount_atomic, "address": req.destination}]
    params = {
        "destinations": destinations,
        "account_index": 0,
        "priority": 0,
        "ring_size": 16,
        "get_tx_keys": True,
    }
    if req.payment_id:
        params["payment_id"] = req.payment_id
    
    result = await _wallet_rpc("transfer", params)
    
    tx_hash = result.get("tx_hash", "")
    tx_key = result.get("tx_key", "")
    amount_sent = result.get("amount", 0) / 1e12
    fee = result.get("fee", 0) / 1e12
    
    log.info("Withdrawal: %f XMR to %s, tx_hash=%s", amount_sent, req.destination, tx_hash)
    
    return {
        "success": True,
        "tx_hash": tx_hash,
        "tx_key": tx_key,
        "amount": amount_sent,
        "fee": fee,
        "destination": req.destination,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PRISM_MONERO_API_PORT", "18084"))
    uvicorn.run(app, host="0.0.0.0", port=port)
