#!/usr/bin/env python3
"""
PRISM Delete All Users Script

Deactivates ALL non-system Matrix users on the Synapse homeserver.
Requires SYNAPSE_ADMIN_TOKEN with admin privileges.

Usage:
  export SYNAPSE_URL=http://localhost:8008
  export SYNAPSE_ADMIN_TOKEN=<your_admin_token>
  python delete_all_users.py
"""

import os
import sys
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("prism-delete-users")


def get_env(key: str, required: bool = True) -> str | None:
    val = os.environ.get(key)
    if required and not val:
        log.error("Missing required environment variable: %s", key)
        sys.exit(1)
    return val


def list_all_users(homeserver_url: str, admin_token: str) -> list[str]:
    """List all local users via Synapse Admin API."""
    users = []
    from_key = "0"
    while True:
        resp = requests.get(
            f"{homeserver_url}/_synapse/admin/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"from": from_key, "limit": 100, "guests": "false"},
        )
        resp.raise_for_status()
        data = resp.json()
        for user in data.get("users", []):
            users.append(user["name"])
        if not data.get("next_token"):
            break
        from_key = str(data["next_token"])
    return users


def deactivate_user(homeserver_url: str, admin_token: str, user_id: str) -> bool:
    """Deactivate a single user. Returns True if succeeded."""
    try:
        resp = requests.post(
            f"{homeserver_url}/_synapse/admin/v1/deactivate/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"erase": True},
        )
        resp.raise_for_status()
        log.info("Deactivated user: %s", user_id)
        return True
    except requests.exceptions.HTTPError as e:
        log.warning("Failed to deactivate %s: %s", user_id, e)
        return False


def main() -> None:
    log.info("PRISM Delete All Users starting...")

    synapse_url = get_env("SYNAPSE_URL", required=True)
    admin_token = get_env("SYNAPSE_ADMIN_TOKEN", required=True)
    server_name = get_env("SERVER_NAME", required=False) or "matrix.fathertkt.uk"

    # Exclude system / bridge / bot accounts
    excluded_prefixes = (
        f"@{server_name}",
        "@pwb-bot",
        "@pmb-bot",
        "@whatsapp_",
        "@meta_",
        "@slack_",
        "@telegram_",
    )

    users = list_all_users(synapse_url, admin_token)
    log.info("Found %d total users on server.", len(users))

    to_delete = [u for u in users if not u.startswith(excluded_prefixes)]
    log.info("Will deactivate %d non-system users.", len(to_delete))

    if not to_delete:
        log.info("No users to delete. Exiting.")
        return

    success = 0
    failed = 0
    for user_id in to_delete:
        if deactivate_user(synapse_url, admin_token, user_id):
            success += 1
        else:
            failed += 1

    log.info("Done. Deactivated: %d, Failed: %d", success, failed)


if __name__ == "__main__":
    main()
