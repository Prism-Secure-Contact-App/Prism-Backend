#!/usr/bin/env python3
"""
PRISM Admin Setup Script

Reads admin credentials from environment variables and ensures the admin
account exists on the Synapse homeserver. Designed to run during first-time
setup or via Docker entrypoint.

Required env vars (in .env or shell):
  PRISM_ADMIN_USERNAME    - e.g. 'admin'
  PRISM_ADMIN_PASSWORD    - strong password, min 8 chars
  PRISM_ADMIN_DISPLAYNAME - optional, defaults to 'PRISM Admin'
  SYNAPSE_URL             - e.g. 'http://localhost:8008'
  SYNAPSE_SHARED_SECRET   - from homeserver.yaml registration_shared_secret

Usage:
  python setup_admin.py
"""

import os
import sys
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("prism-admin-setup")


def get_env(key: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(key, default)
    if required and not val:
        log.error("Missing required environment variable: %s", key)
        sys.exit(1)
    return val


def register_admin_shared_secret(
    homeserver_url: str,
    shared_secret: str,
    username: str,
    password: str,
    displayname: str,
    admin: bool = True,
) -> dict:
    """
    Register a user using Synapse's shared-secret registration endpoint.
    Returns the registration response JSON.
    """
    import hmac
    import hashlib

    # Build HMAC of nonce
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


def ensure_admin_exists(
    homeserver_url: str,
    shared_secret: str,
    username: str,
    password: str,
    displayname: str,
) -> None:
    """
    Idempotently ensure the admin account exists. If the user already exists,
    log a warning and continue (password is NOT updated for security).
    """
    try:
        result = register_admin_shared_secret(
            homeserver_url, shared_secret, username, password, displayname, admin=True
        )
        log.info("Admin account '@%s:%s' created successfully.", username, homeserver_url)
        log.info("Access token (store securely): %s", result.get("access_token", "N/A"))
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            body = e.response.json()
            errcode = body.get("errcode")
            if errcode == "M_USER_IN_USE":
                log.warning("Admin user '@%s:%s' already exists. Skipping creation.", username, homeserver_url)
                return
        raise


def main() -> None:
    log.info("PRISM Admin Setup starting...")

    admin_user = get_env("PRISM_ADMIN_USERNAME", default="admin", required=True)
    admin_pass = get_env("PRISM_ADMIN_PASSWORD", required=True)
    admin_display = get_env("PRISM_ADMIN_DISPLAYNAME", default="PRISM Admin")
    synapse_url = get_env("SYNAPSE_URL", default="http://localhost:8008", required=True)
    shared_secret = get_env("SYNAPSE_SHARED_SECRET", required=True)

    # Validate password policy
    if len(admin_pass) < 8:
        log.error("PRISM_ADMIN_PASSWORD must be at least 8 characters.")
        sys.exit(1)
    if not any(c.isupper() for c in admin_pass):
        log.error("PRISM_ADMIN_PASSWORD must contain at least one uppercase letter.")
        sys.exit(1)
    if not any(c.islower() for c in admin_pass):
        log.error("PRISM_ADMIN_PASSWORD must contain at least one lowercase letter.")
        sys.exit(1)
    if not any(c.isdigit() for c in admin_pass):
        log.error("PRISM_ADMIN_PASSWORD must contain at least one digit.")
        sys.exit(1)
    if not any(not c.isalnum() for c in admin_pass):
        log.error("PRISM_ADMIN_PASSWORD must contain at least one special character.")
        sys.exit(1)

    ensure_admin_exists(synapse_url, shared_secret, admin_user, admin_pass, admin_display)
    log.info("PRISM Admin Setup complete.")


if __name__ == "__main__":
    main()
