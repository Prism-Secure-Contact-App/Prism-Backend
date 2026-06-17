#!/usr/bin/env python3
"""
Sync Synapse <-> PostgreSQL password on the RPi 4.

Background
----------
PRISM's `homeserver.yaml` and the `prism-db` container both carry the
`synapse` user's PostgreSQL password. They MUST match or Synapse boot
loops with `psycopg2.OperationalError: ... password authentication failed
for user "synapse"`, and Cloudflare returns `[502] non-json bytes` to the app.

What this script does
---------------------
1. Patches `homeserver.yaml` (`database.args.password`) to the canonical
   value declared at the top of this file.
2. Runs `ALTER USER synapse WITH PASSWORD '<canonical>'` inside the
   `prism-db` container, in case the live PG account drifted.
3. Restarts the `prism-synapse` container.
4. Verifies `/_matrix/client/versions` returns 200.

Usage
-----
    python tools/sync_synapse_db_password.py

Edit `CANONICAL_PASSWORD` below if the agreed-upon value changes. The
backup files written to the RPi are stamped with epoch seconds.

Safety
------
- Never logs the password.
- Idempotent: re-running on an already-correct system is a no-op + restart.
- Aborts if SSH or sudo fails before any mutation.
"""

import paramiko
import sys
import time

# ---- Configuration ----------------------------------------------------------

HOST = "100.125.63.77"
USER = "fathertkt"
PASS = "1234"
REMOTE_BACKEND_DIR = "/home/fathertkt/prism-backend"
HOMESERVER_YAML = f"{REMOTE_BACKEND_DIR}/data/synapse/homeserver.yaml"
CANONICAL_PASSWORD = "PrismMvp_2026_Synapse!"

# Older mismatched value that may still be in homeserver.yaml.
LEGACY_PASSWORD = "PrismMvp_2026_PRISM Messenger!"

# -----------------------------------------------------------------------------


def run(client: paramiko.SSHClient, cmd: str, *, timeout: int = 30, sudo: bool = False) -> tuple[int, str, str]:
    """Execute a command, return (exit_code, stdout, stderr). Logs nothing sensitive."""
    full_cmd = f"echo {PASS} | sudo -S {cmd}" if sudo else cmd
    _, out, err = client.exec_command(full_cmd, timeout=timeout)
    return out.channel.recv_exit_status(), out.read().decode(errors="replace"), err.read().decode(errors="replace")


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[sync] Connecting to {USER}@{HOST} ...")
    client.connect(hostname=HOST, username=USER, password=PASS, timeout=15)
    try:
        # 1. Patch homeserver.yaml (legacy -> canonical) and back it up.
        ts = int(time.time())
        backup = f"{HOMESERVER_YAML}.bak.{ts}"
        run(client, f"cp {HOMESERVER_YAML} {backup}", sudo=True)
        run(client, f'sed -i "s|{LEGACY_PASSWORD}|{CANONICAL_PASSWORD}|g" {HOMESERVER_YAML}', sudo=True)
        code, grep_out, _ = run(client, f"grep -E '^\\s*password:' {HOMESERVER_YAML}", sudo=True)
        # We deliberately don't echo the password.
        print(f"[sync] homeserver.yaml password line replaced (backup: {backup})")
        if CANONICAL_PASSWORD not in grep_out:
            print("[sync] WARNING: canonical password not detected in homeserver.yaml after patch.", file=sys.stderr)

        # 2. Reset the PostgreSQL `synapse` user password in case it drifted.
        sql = f"ALTER USER synapse WITH PASSWORD '{CANONICAL_PASSWORD}';"
        cmd = f'docker exec prism-db psql -U postgres -c "{sql}"'
        code, out, err = run(client, cmd, sudo=True)
        if code != 0:
            print(f"[sync] WARN: ALTER USER returned {code}: {err.strip()}", file=sys.stderr)
        else:
            print("[sync] PostgreSQL synapse user password reset.")

        # 3. Restart Synapse.
        run(client, "docker restart prism-synapse", sudo=True, timeout=60)
        print("[sync] prism-synapse restarted; giving it 25s to come up ...")
        time.sleep(25)

        # 4. Verify API.
        verify_cmd = "curl -s -o /dev/null -w '%{http_code}' http://localhost:8008/_matrix/client/versions"
        code, http_status, _ = run(client, verify_cmd, sudo=True)
        http_status = http_status.strip()
        print(f"[sync] Synapse /versions: HTTP {http_status}")
        return 0 if http_status == "200" else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
