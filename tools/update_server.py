#!/usr/bin/env python3
"""
PRISM Single-Server Update Tool

Pulls the latest Backend code on the Contabo VPS and restarts containers.
Uses SSH key authentication.
"""

import io
import os
import sys
from pathlib import Path

import paramiko

# Force UTF-8 stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HOST = "5.189.159.214"
USER = "root"
SSH_KEY = str(Path.home() / ".ssh" / "prism_deploy")
REMOTE_DIR = "/opt/prism"


def ssh_exec(client, cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def update_server():
    if not os.path.exists(SSH_KEY):
        print(f"✗ SSH key not found: {SSH_KEY}")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(SSH_KEY)
        print(f"Connecting to {HOST}...")
        client.connect(HOST, username=USER, pkey=pkey, timeout=15)
        print("✓ SSH Connected\n")

        print("Pulling latest code...")
        code, out, err = ssh_exec(client, f"cd {REMOTE_DIR} && git pull origin master")
        print(out)
        if err:
            print(err)
        if code != 0:
            print("✗ git pull failed")
            return 1

        print("\nBuilding and restarting containers...")
        code, out, err = ssh_exec(
            client,
            f"cd {REMOTE_DIR} && docker compose up -d --build --remove-orphans",
            timeout=600,
        )
        print(out)
        if err:
            print(err)
        if code != 0:
            print("✗ docker compose up failed")
            return 1

        print("\n✓ Update Successful!")
        return 0

    except Exception as exc:
        print(f"✗ An error occurred: {exc}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(update_server())
