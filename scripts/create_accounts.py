#!/usr/bin/env python3
"""
PRISM Account Creation Script

Creates 1 admin + 5 regular users using Synapse shared-secret registration.
Requires SYNAPSE_SHARED_SECRET from homeserver.yaml.

Usage:
  export SYNAPSE_URL=http://localhost:8008
  export SYNAPSE_SHARED_SECRET=<shared_secret_from_homeserver.yaml>
  python create_accounts.py
"""

import os
import sys
import requests
import hmac
import hashlib
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("prism-create-accounts")


def get_env(key: str, required: bool = True) -> str | None:
    val = os.environ.get(key)
    if required and not val:
        log.error("Missing required environment variable: %s", key)
        sys.exit(1)
    return val


def register_user(
    homeserver_url: str,
    shared_secret: str,
    username: str,
    password: str,
    displayname: str,
    admin: bool = False,
) -> dict:
    """Register a user via Synapse shared-secret registration endpoint."""
    nonce = requests.get(f"{homeserver_url}/_synapse/admin/v1/register").json()["nonce"]
    mac = hmac.new(
        shared_secret.encode("utf-8"),
        f"{nonce}\0{username}\0{password}\0{'admin' if admin else 'notadmin'}".encode("utf-8"),
        hashlib.sha1,
    ).hexdigest()

    payload = {
        "nonce": nonce,
        "username": username,
        "password": password,
        "mac": mac,
        "admin": admin,
        "displayname": displayname,
    }

    resp = requests.post(f"{homeserver_url}/_synapse/admin/v1/register", json=payload)
    resp.raise_for_status()
    return resp.json()


def ensure_user(
    homeserver_url: str,
    shared_secret: str,
    username: str,
    password: str,
    displayname: str,
    admin: bool = False,
) -> dict:
    """Idempotently create a user. If exists, log and skip."""
    try:
        result = register_user(homeserver_url, shared_secret, username, password, displayname, admin)
        log.info("Created %s: @%s", "admin" if admin else "user", username)
        return result
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            body = e.response.json()
            if body.get("errcode") == "M_USER_IN_USE":
                log.warning("User @%s already exists. Skipping.", username)
                return {}
        raise


def main() -> None:
    log.info("PRISM Account Creation starting...")

    synapse_url = get_env("SYNAPSE_URL", required=True)
    shared_secret = get_env("SYNAPSE_SHARED_SECRET", required=True)

    ACCOUNTS = [
        ("admin", "PrismAdmin2025!", "PRISM Admin", True),
        ("alice", "PrismUser1!", "Alice", False),
        ("bob", "PrismUser2!", "Bob", False),
        ("charlie", "PrismUser3!", "Charlie", False),
        ("diana", "PrismUser4!", "Diana", False),
        ("eve", "PrismUser5!", "Eve", False),
    ]

    created = []
    for username, password, displayname, is_admin in ACCOUNTS:
        result = ensure_user(synapse_url, shared_secret, username, password, displayname, is_admin)
        created.append({
            "username": username,
            "password": password,
            "displayname": displayname,
            "admin": is_admin,
            "access_token": result.get("access_token", "N/A") if result else "already exists",
        })

    print("\n" + "=" * 60)
    print("PRISM Account Creation Summary")
    print("=" * 60)
    for acc in created:
        role = "ADMIN" if acc["admin"] else "USER"
        print(f"  [{role}] @{acc['username']} / {acc['password']}  (display: {acc['displayname']})")
    print("=" * 60)


if __name__ == "__main__":
    main()
