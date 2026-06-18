#!/usr/bin/env python3
"""
PRISM Session Retention Bridge

Periodically scans rooms for m.room.retention state events and purges
messages older than the retention period using Synapse Admin API.

Intended to run as a Docker container alongside Synapse.

Required env vars:
  SYNAPSE_URL          - e.g. http://synapse:8008
  SYNAPSE_ADMIN_TOKEN  - Synapse admin access token
  SCAN_INTERVAL_MIN    - default 60
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("prism-retention")

SYNAPSE_URL = os.environ.get("SYNAPSE_URL", "http://synapse:8008").rstrip("/")
ADMIN_TOKEN = os.environ.get("SYNAPSE_ADMIN_TOKEN", "")
SCAN_INTERVAL_MIN = int(os.environ.get("SCAN_INTERVAL_MIN", "60"))

RETENTION_EVENT_TYPE = "m.room.retention"


def admin_api_headers() -> dict:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def get_rooms_with_retention() -> list[dict]:
    """List all rooms and filter those with m.room.retention state."""
    rooms = []
    url = f"{SYNAPSE_URL}/_synapse/admin/v1/rooms"
    params = {}
    while True:
        resp = requests.get(url, headers=admin_api_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rooms.extend(data.get("rooms", []))
        if not data.get("next_batch"):
            break
        params["from"] = data["next_batch"]

    retention_rooms = []
    for room in rooms:
        room_id = room["room_id"]
        try:
            encoded_room_id = quote(room_id, safe='')
            state_url = f"{SYNAPSE_URL}/_matrix/client/v3/rooms/{encoded_room_id}/state/{RETENTION_EVENT_TYPE}"
            state_resp = requests.get(state_url, headers=admin_api_headers(), timeout=10)
            if state_resp.status_code == 200:
                event = state_resp.json()
                max_lifetime_ms = event.get("max_lifetime")
                if max_lifetime_ms:
                    retention_rooms.append({
                        "room_id": room_id,
                        "max_lifetime_ms": max_lifetime_ms,
                    })
                    log.info("Room %s has retention max_lifetime=%d ms", room_id, max_lifetime_ms)
        except Exception as exc:
            log.warning("Error checking retention state for %s: %s", room_id, exc)

    return retention_rooms


def purge_history(room_id: str, before_ts: int) -> bool:
    """Purge history in a room before the given timestamp using Synapse Admin API."""
    encoded_room_id = quote(room_id, safe='')
    url = f"{SYNAPSE_URL}/_synapse/admin/v1/purge_history/{encoded_room_id}"
    payload = {"purge_up_to_ts": before_ts, "delete_local_events": True}
    try:
        resp = requests.post(url, headers=admin_api_headers(), json=payload, timeout=60)
        if resp.status_code in (200, 202):
            log.info("Purged history for %s up to %s", room_id, datetime.fromtimestamp(before_ts / 1000, tz=timezone.utc))
            return True
        else:
            log.warning("Purge history for %s failed: %s %s", room_id, resp.status_code, resp.text)
            return False
    except Exception as exc:
        log.error("Exception purging history for %s: %s", room_id, exc)
        return False


def process_retention() -> None:
    log.info("Starting retention scan...")
    if not ADMIN_TOKEN:
        log.error("SYNAPSE_ADMIN_TOKEN not set. Exiting.")
        sys.exit(1)

    rooms = get_rooms_with_retention()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    for room in rooms:
        room_id = room["room_id"]
        max_lifetime_ms = room["max_lifetime_ms"]
        before_ts = now_ms - max_lifetime_ms
        purge_history(room_id, before_ts)

    log.info("Retention scan complete. Scanned %d rooms.", len(rooms))


def main() -> None:
    log.info("PRISM Session Retention Bridge started (interval=%d min)", SCAN_INTERVAL_MIN)
    while True:
        try:
            process_retention()
        except Exception as exc:
            log.exception("Retention scan error: %s", exc)
        time.sleep(SCAN_INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
