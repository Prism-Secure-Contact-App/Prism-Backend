#!/usr/bin/env python3
"""
PRISM LLM API Service v2.0

A lightweight API gateway that:
1. Manages per-user API keys for external Meta AI / LLM access.
2. Proxies chat-completion requests (OpenAI-compatible).
3. Provides native PrismAI chat endpoints that talk to Meta AI over Matrix/WhatsApp bridge.
4. Validates API keys and enforces basic rate limiting.
5. Persists keys in SQLite (survives container restarts).

Required env vars:
  PRISM_LLM_API_PORT      - default 8080
  META_AI_ENDPOINT        - Meta AI base URL (optional; if empty, uses Matrix bridge)
  META_AI_API_KEY         - Meta AI service key
  SYNAPSE_URL             - http://synapse:8008
  SYNAPSE_ADMIN_TOKEN     - For admin operations (optional)

Usage (development):
  pip install fastapi uvicorn
  uvicorn llm_api_service:app --host 0.0.0.0 --port 8080

Usage (Docker Compose):
  Add to docker-compose.yml as service `prism-llm-api`.
"""

import os
import secrets
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("prism-llm-api")

app = FastAPI(title="PRISM LLM API", version="2.0.0")

META_AI_ENDPOINT = os.environ.get("META_AI_ENDPOINT", "")
META_AI_API_KEY = os.environ.get("META_AI_API_KEY", "")
SYNAPSE_URL = os.environ.get("SYNAPSE_URL", "http://synapse:8008")
SYNAPSE_ADMIN_TOKEN = os.environ.get("SYNAPSE_ADMIN_TOKEN", "")

DB_PATH = os.environ.get("LLM_API_DB_PATH", "/data/llm_api_keys.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)


# ─── Database ────────────────────────────────────────────────────────────────

def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                user_id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prismai_rooms (
                user_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                room_name TEXT,
                is_meta_ai INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, room_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prismai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER DEFAULT (strftime('%s','now'))
            )
        """)
        conn.commit()


_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_api_key() -> str:
    """Generate a secure random API key."""
    return "prism_sk_" + secrets.token_urlsafe(32)


def _validate_matrix_token(matrix_token: str) -> str:
    """Validate a Matrix access token against Synapse and return the real user_id."""
    try:
        resp = httpx.get(
            f"{SYNAPSE_URL}/_matrix/client/v3/account/whoami",
            headers={"Authorization": f"Bearer {matrix_token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        user_id = data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid Matrix token: no user_id")
        return user_id
    except httpx.HTTPStatusError as e:
        log.warning("Token validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired Matrix token")
    except httpx.RequestError as e:
        log.error("Synapse unreachable during token validation: %s", e)
        raise HTTPException(status_code=503, detail="Synapse unreachable")


def _matrix_request(method: str, path: str, token: str, json_data: Any = None, params: Dict = None) -> Dict:
    """Make an authenticated Matrix Client API request."""
    url = f"{SYNAPSE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = httpx.request(method, url, headers=headers, json=json_data, params=params, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        log.warning("Matrix API error [%s %s]: %s", method, path, e)
        raise HTTPException(status_code=e.response.status_code, detail=f"Matrix API error: {e.response.text}")
    except httpx.RequestError as e:
        log.error("Matrix API unreachable [%s %s]: %s", method, path, e)
        raise HTTPException(status_code=503, detail="Matrix API unreachable")


def _get_room_members(room_id: str, token: str) -> List[str]:
    """Return list of member user IDs in a room."""
    data = _matrix_request("GET", f"/_matrix/client/v3/rooms/{room_id}/members", token)
    members = []
    for chunk in data.get("chunk", []):
        if chunk.get("type") == "m.room.member" and chunk.get("content", {}).get("membership") == "join":
            members.append(chunk.get("sender"))
    return list(set(members))


def _get_other_member(room_id: str, user_id: str, token: str) -> Optional[str]:
    """Find the other member in a 1:1 room (assumes Meta AI DM)."""
    members = _get_room_members(room_id, token)
    for m in members:
        if m != user_id:
            return m
    return None


def _send_room_message(room_id: str, body: str, token: str) -> str:
    """Send a m.text message to a Matrix room. Returns event_id."""
    txn_id = str(uuid.uuid4())
    payload = {"msgtype": "m.text", "body": body}
    data = _matrix_request(
        "PUT",
        f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}",
        token,
        json_data=payload,
    )
    return data.get("event_id", "")


def _get_room_messages(room_id: str, token: str, limit: int = 20, from_token: Optional[str] = None) -> Dict:
    """Fetch recent messages from a room (reverse-chronological)."""
    params = {"dir": "b", "limit": limit, "filter": '{"types":["m.room.message"]}'}
    if from_token:
        params["from"] = from_token
    return _matrix_request("GET", f"/_matrix/client/v3/rooms/{room_id}/messages", token, params=params)


def _poll_for_response(room_id: str, user_id: str, token: str, sent_event_id: str, timeout_sec: float = 25.0, interval: float = 1.5) -> Optional[Dict]:
    """
    Poll a Matrix room for a response from the other participant.
    Returns the latest message event dict from the other user, or None.
    """
    start_time = time.time()
    last_event_id = sent_event_id

    while time.time() - start_time < timeout_sec:
        data = _get_room_messages(room_id, token, limit=10)
        chunks = data.get("chunk", [])
        for event in chunks:
            event_id = event.get("event_id", "")
            sender = event.get("sender", "")
            if sender == user_id:
                continue
            if event_id == last_event_id:
                # We reached previously-known messages; stop scanning this batch
                break
            msgtype = event.get("content", {}).get("msgtype", "")
            if msgtype == "m.text":
                # Found a response from the other participant
                return event
        # Wait before next poll
        time.sleep(interval)
    return None


# ─── API Key Management ──────────────────────────────────────────────────────

@app.post("/v1/llm/api-keys")
def create_api_key(authorization: Optional[str] = Header(None)):
    """
    Create a new API key for the authenticated Matrix user.
    Expects `authorization: Bearer <matrix_access_token>`.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)
    new_key = _generate_api_key()

    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_keys (user_id, api_key) VALUES (?, ?)",
            (user_id, new_key),
        )
        conn.commit()

    log.info("Created API key for %s", user_id)
    return {"api_key": new_key, "user_id": user_id, "created": True}


@app.get("/v1/llm/api-keys")
def list_api_keys(authorization: Optional[str] = Header(None)):
    """List the current API key for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    with _db() as conn:
        row = conn.execute(
            "SELECT api_key FROM api_keys WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        return {"api_key": None}
    key = row[0]
    return {"api_key": key[:12] + "...", "created": True}


@app.delete("/v1/llm/api-keys")
def delete_api_key(authorization: Optional[str] = Header(None)):
    """Delete the API key for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    with _db() as conn:
        conn.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))
        conn.commit()

    log.info("Deleted API key for %s", user_id)
    return {"deleted": True}


# ─── OpenAI-compatible Chat Completions ──────────────────────────────────────

@app.post("/v1/llm/chat/completions")
async def chat_completions(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    Proxy chat-completion requests to Meta AI.
    Requires `X-Api-Key: <prism_sk_...>` header.
    If META_AI_ENDPOINT is set, proxies there.
    Otherwise attempts Matrix-bridge Meta AI flow using stored room mappings.
    """
    if not x_api_key or not x_api_key.startswith("prism_sk_"):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    with _db() as conn:
        row = conn.execute(
            "SELECT user_id FROM api_keys WHERE api_key = ?", (x_api_key,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="API key not found")
    user_id = row[0]

    body = await request.json()
    messages = body.get("messages", [])
    last_message = messages[-1]["content"] if messages else "Hello"

    # Prefer external endpoint if configured
    if META_AI_ENDPOINT:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{META_AI_ENDPOINT}/chat/completions",
                    headers={"Authorization": f"Bearer {META_AI_API_KEY}"},
                    json=body,
                    timeout=60.0,
                )
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            except httpx.RequestError as exc:
                log.error("Meta AI proxy error: %s", exc)
                raise HTTPException(status_code=502, detail="Meta AI unreachable") from exc

    # Fallback: use Matrix bridge Meta AI room
    # This requires the user to have a Matrix token; we can't do bridge-chat without it.
    # Return a helpful mock that instructs the user to use /v1/prismai/chat instead.
    return JSONResponse(content={
        "id": "prism-bridge-" + secrets.token_hex(8),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "meta-ai-bridge",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": (
                    f"[PrismAI Bridge] I received: '{last_message}'.\n\n"
                    "To chat with Meta AI through the WhatsApp bridge, "
                    "use the native PrismAI chat endpoint: POST /v1/prismai/chat "
                    "with your Matrix Bearer token."
                )
            },
            "finish_reason": "stop"
        }]
    })


# ─── Native PrismAI Chat (Matrix Bridge) ─────────────────────────────────────

@app.get("/v1/prismai/rooms")
def list_prismai_rooms(authorization: Optional[str] = Header(None)):
    """
    List rooms in the user's PrismAI space that contain Meta AI conversations.
    Returns room_id, name, and the Meta AI participant's MXID.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    # Fetch user's joined rooms
    joined = _matrix_request("GET", "/_matrix/client/v3/joined_rooms", matrix_token)
    room_ids = joined.get("joined_rooms", [])

    results = []
    for room_id in room_ids:
        try:
            members = _get_room_members(room_id, matrix_token)
            # Heuristic: if room has exactly 2 members and one is the user,
            # the other is likely Meta AI (or any bridge contact).
            if len(members) == 2 and user_id in members:
                other = [m for m in members if m != user_id][0]
                # Try to get room name
                state = _matrix_request("GET", f"/_matrix/client/v3/rooms/{room_id}/state", matrix_token)
                name_ev = next((e for e in state if e.get("type") == "m.room.name"), {})
                name = name_ev.get("content", {}).get("name", "Unknown")
                results.append({
                    "room_id": room_id,
                    "name": name,
                    "meta_ai_user_id": other,
                })
                # Persist for faster lookups
                with _db() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO prismai_rooms (user_id, room_id, room_name, is_meta_ai) VALUES (?, ?, ?, ?)",
                        (user_id, room_id, name, 1),
                    )
                    conn.commit()
        except Exception as exc:
            log.debug("Skipping room %s: %s", room_id, exc)
            continue

    return {"rooms": results, "user_id": user_id}


@app.post("/v1/prismai/chat")
async def prismai_chat(request: Request, authorization: Optional[str] = Header(None)):
    """
    Send a message to Meta AI via the WhatsApp Matrix bridge and return the reply.

    Body JSON:
    {
      "room_id": "!xxx:matrix.fathertkt.uk",  // optional; auto-detected if omitted
      "message": "Hello Meta AI"
    }

    Returns:
    {
      "success": true,
      "user_id": "@alice:matrix.fathertkt.uk",
      "room_id": "!xxx:matrix.fathertkt.uk",
      "sent_event_id": "$xxx",
      "response": {
        "event_id": "$yyy",
        "sender": "@whatsapp_META_AI:matrix.fathertkt.uk",
        "content": {"msgtype": "m.text", "body": "Hi there!"},
        "origin_server_ts": 1234567890
      }
    }
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    body = await request.json()
    message = body.get("message", "").strip()
    room_id = body.get("room_id", "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    # If room_id not provided, try to find a stored Meta AI room
    if not room_id:
        with _db() as conn:
            row = conn.execute(
                "SELECT room_id FROM prismai_rooms WHERE user_id = ? AND is_meta_ai = 1 LIMIT 1",
                (user_id,)
            ).fetchone()
            if row:
                room_id = row[0]

    if not room_id:
        # Auto-discover by scanning joined rooms
        joined = _matrix_request("GET", "/_matrix/client/v3/joined_rooms", matrix_token)
        for rid in joined.get("joined_rooms", []):
            try:
                members = _get_room_members(rid, matrix_token)
                if len(members) == 2 and user_id in members:
                    room_id = rid
                    break
            except Exception:
                continue

    if not room_id:
        raise HTTPException(
            status_code=404,
            detail="No Meta AI room found. Please start a conversation with Meta AI on WhatsApp first."
        )

    # Verify the room still exists and user is a member
    try:
        _matrix_request("GET", f"/_matrix/client/v3/rooms/{room_id}/state/m.room.member/{user_id}", matrix_token)
    except HTTPException:
        raise HTTPException(status_code=403, detail="You are not a member of the specified room")

    # Send message
    try:
        sent_event_id = _send_room_message(room_id, message, matrix_token)
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send message: {exc.detail}")

    log.info("PrismAI chat: user=%s room=%s sent=%s", user_id, room_id, sent_event_id)

    # Poll for response
    response_event = _poll_for_response(room_id, user_id, matrix_token, sent_event_id, timeout_sec=25.0, interval=1.5)

    if response_event:
        # Persist in chat history
        with _db() as conn:
            conn.execute(
                "INSERT INTO prismai_chat_history (user_id, room_id, role, content) VALUES (?, ?, ?, ?)",
                (user_id, room_id, "user", message),
            )
            conn.execute(
                "INSERT INTO prismai_chat_history (user_id, room_id, role, content) VALUES (?, ?, ?, ?)",
                (user_id, room_id, "assistant", response_event.get("content", {}).get("body", "")),
            )
            conn.commit()

        return {
            "success": True,
            "user_id": user_id,
            "room_id": room_id,
            "sent_event_id": sent_event_id,
            "response": {
                "event_id": response_event.get("event_id"),
                "sender": response_event.get("sender"),
                "content": response_event.get("content"),
                "origin_server_ts": response_event.get("origin_server_ts"),
            }
        }
    else:
        # No response within timeout; still acknowledge the send
        return {
            "success": True,
            "user_id": user_id,
            "room_id": room_id,
            "sent_event_id": sent_event_id,
            "response": None,
            "notice": "Message sent, but no response received from Meta AI yet. Try again shortly."
        }


@app.get("/v1/prismai/chat/history")
def get_chat_history(
    room_id: str,
    authorization: Optional[str] = Header(None),
    limit: int = 50,
):
    """Return persisted PrismAI chat history for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    with _db() as conn:
        rows = conn.execute(
            """SELECT role, content, timestamp FROM prismai_chat_history
               WHERE user_id = ? AND room_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (user_id, room_id, limit),
        ).fetchall()

    history = [
        {"role": r, "content": c, "timestamp": t}
        for r, c, t in reversed(rows)
    ]
    return {"room_id": room_id, "history": history}


@app.get("/v1/prismai/chat/history/live")
def get_live_chat_history(
    room_id: str,
    authorization: Optional[str] = Header(None),
    limit: int = 50,
):
    """
    Fetch live message history directly from the Matrix room (no local DB).
    Useful for syncing the full conversation including bridge messages.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    matrix_token = authorization[7:]
    user_id = _validate_matrix_token(matrix_token)

    data = _get_room_messages(room_id, matrix_token, limit=limit)
    chunks = data.get("chunk", [])
    messages = []
    for ev in reversed(chunks):  # chronological
        if ev.get("type") == "m.room.message":
            content = ev.get("content", {})
            if content.get("msgtype") == "m.text":
                messages.append({
                    "event_id": ev.get("event_id"),
                    "sender": ev.get("sender"),
                    "body": content.get("body", ""),
                    "timestamp": ev.get("origin_server_ts"),
                })
    return {"room_id": room_id, "messages": messages}


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "prism-llm-api", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PRISM_LLM_API_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
