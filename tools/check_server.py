#!/usr/bin/env python3
"""
PRISM Single-Server Health Check

Verifies all PRISM services running on the Contabo VPS.
Uses SSH key authentication to run checks directly on the server.
"""

import io
import json
import os
import sys
from pathlib import Path

import paramiko

# Force UTF-8 stdout/stderr so the ✓/✗ glyphs render on Windows code pages
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Server connection details
HOST = "5.189.159.214"
USER = "root"
SSH_KEY = str(Path.home() / ".ssh" / "prism_deploy")

EXPECTED_CONTAINERS = {
    "prism-db": "PostgreSQL",
    "prism-synapse": "Synapse",
    "prism-whatsapp": "WhatsApp Bridge",
    "monero-node": "Monero Node",
    "monero-wallet-rpc": "Monero Wallet RPC",
    "prism-monero-api": "Monero API",
    "prism-llm-api": "LLM API",
    "prism-retention": "Retention",
    "prism-tunnel": "Cloudflare Tunnel",
    "prism-website": "Website",
}


def ssh_exec(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def check_containers(client):
    code, out, err = ssh_exec(client, "cd /opt/prism && docker compose ps --format '{{.Names}}\t{{.Status}}'")
    if code != 0:
        return False, f"  ✗ docker compose ps failed: {err}"

    running = {}
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        if len(parts) == 2:
            running[parts[0]] = parts[1]

    results = []
    all_ok = True
    for container, desc in EXPECTED_CONTAINERS.items():
        if container in running:
            status = running[container]
            if "Up" in status:
                results.append(f"  ✓ {desc}: {status}")
            else:
                results.append(f"  ✗ {desc}: {status}")
                all_ok = False
        else:
            results.append(f"  ✗ {desc}: NOT RUNNING")
            all_ok = False
    return all_ok, "\n".join(results)


def check_url(client, cmd, desc, expected_code="200"):
    code, out, err = ssh_exec(client, cmd)
    if code == 0 and out.strip() == expected_code:
        return True, f"  ✓ {desc}: HTTP {out.strip()}"
    return False, f"  ✗ {desc}: HTTP {out.strip() if out else 'N/A'} (err: {err})"


def check_url_in_container(client, container, path, desc, expected_code="200"):
    cmd = (
        f"cd /opt/prism && docker compose exec -T {container} "
        f"sh -c \"curl -s -o /dev/null -w '%{{http_code}}' {path}\""
    )
    return check_url(client, cmd, desc, expected_code)


def _fetch_public(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "PRISM-HealthCheck/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read(200)


def check_public_matrix():
    """Run from the local machine (or wherever this script is executed)."""
    try:
        status, _ = _fetch_public("https://matrix.fathertkt.uk/_matrix/client/versions")
        return status == 200, f"  ✓ Public Matrix endpoint: HTTP {status}" if status == 200 else f"  ✗ Public Matrix endpoint: HTTP {status}"
    except Exception as exc:
        return False, f"  ✗ Public Matrix endpoint: {exc}"


def check_public_website():
    try:
        status, _ = _fetch_public("http://prismas.net/")
        return status == 200, f"  ✓ Public website (prismas.net): HTTP {status}" if status == 200 else f"  ✗ Public website: HTTP {status}"
    except Exception as exc:
        return False, f"  ✗ Public website (prismas.net): {exc}"


def check_monero_wallet_rpc(client):
    cmd = (
        "docker exec -T monero-wallet-rpc curl -s -X POST http://127.0.0.1:18083/json_rpc "
        "-H 'Content-Type: application/json' "
        "-d '{\"jsonrpc\":\"2.0\",\"id\":\"0\",\"method\":\"get_height\"}'"
    )
    code, out, err = ssh_exec(client, cmd)
    if code == 0 and out.strip().startswith("{"):
        try:
            data = json.loads(out)
            height = data.get("result", {}).get("height", "N/A")
            return True, f"  ✓ Monero Wallet RPC: height {height}"
        except Exception:
            return True, "  ✓ Monero Wallet RPC: responding"
    return False, "  ⚠ Monero Wallet RPC: not responding yet (likely waiting for node sync)"


def main():
    print("=" * 60)
    print("  PRISM Single-Server Health Check")
    print(f"  Host: {HOST}")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    overall_results = {}

    try:
        if not os.path.exists(SSH_KEY):
            print(f"  ✗ SSH key not found: {SSH_KEY}")
            return 1

        pkey = paramiko.Ed25519Key.from_private_key_file(SSH_KEY)
        client.connect(HOST, username=USER, pkey=pkey, timeout=15)
        print("  ✓ SSH Connected\n")

        ok, res = check_containers(client)
        print("[Docker Containers]")
        print(res)
        overall_results["Containers"] = ok

        print("\n[Local Service Endpoints]")
        ok, res = check_url_in_container(
            client,
            "synapse",
            "http://127.0.0.1:8008/_matrix/client/versions",
            "Synapse API (local)",
        )
        print(res)
        overall_results["Synapse Local"] = ok

        ok, res = check_url(
            client,
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/",
            "Website (local)",
        )
        print(res)
        overall_results["Website Local"] = ok

        ok, res = check_url_in_container(
            client,
            "monerod",
            "-X POST http://127.0.0.1:18081/json_rpc -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":\"0\",\"method\":\"get_info\"}'",
            "Monero Node RPC",
        )
        print(res)
        overall_results["Monero Node"] = ok

        ok, res = check_monero_wallet_rpc(client)
        print(res)
        overall_results["Monero Wallet RPC"] = ok

        print("\n[Public Endpoints]")
        ok, res = check_public_matrix()
        print(res)
        overall_results["Matrix Public"] = ok

        ok, res = check_public_website()
        print(res)
        overall_results["Website Public"] = ok

    except Exception as exc:
        print(f"  ✗ SSH Failed: {exc}")
        overall_results["SSH"] = False
    finally:
        client.close()

    print(f"\n{'=' * 60}")
    print("  FINAL STATUS SUMMARY")
    print(f"{'=' * 60}")
    for name, ok in overall_results.items():
        print(f"  [{'✓' if ok else '✗'}] {name}")

    all_ok = all(overall_results.values())
    print(f"\n  Result: {'SYSTEM HEALTHY' if all_ok else 'ATTENTION REQUIRED'}")
    print(f"{'=' * 60}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
