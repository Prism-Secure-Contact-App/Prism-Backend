#!/usr/bin/env python3
"""
PRISM RPi4 Deployment & Maintenance Tool

Handles the full bridge lifecycle:
  - Health checks (containers, APIs, DB)
  - Two-step bridge bootstrap (config → registration → start)
  - Registration token sync & sender_localpart fix
  - Encryption disable/enable (workaround for Synapse ≥1.151)
  - Bridge DB reset (nuclear option)
  - File ownership fix (uid 1337)

Usage:
    python3 tools/deploy_rpi4.py --check
    python3 tools/deploy_rpi4.py --bootstrap whatsapp
    python3 tools/deploy_rpi4.py --bootstrap meta
    python3 tools/deploy_rpi4.py --fix-registration
    python3 tools/deploy_rpi4.py --disable-encryption
    python3 tools/deploy_rpi4.py --reset-db whatsapp
    python3 tools/deploy_rpi4.py --restart-all

Requires:
    pip install paramiko pyyaml
"""

import argparse
import base64
import io
import os
import sys
import time

import paramiko
import yaml

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RPI_HOST = "100.125.63.77"
RPI_USER = "fathertkt"
RPI_PASS = "1234"
BASE_DIR = "/home/fathertkt/prism-backend"

BRIDGES = {
    "whatsapp": {
        "service": "whatsapp",
        "container": "prism-whatsapp",
        "data_dir": f"{BASE_DIR}/data/whatsapp",
        "config": f"{BASE_DIR}/data/whatsapp/config.yaml",
        "registration": f"{BASE_DIR}/data/whatsapp/registration.yaml",
        "synapse_reg": f"{BASE_DIR}/data/synapse/appservice-whatsapp.yaml",
        "db_name": "mautrix_whatsapp",
        "bot_username": "pwb-bot",
        "user_namespace": "whatsapp_",
        "port": 29318,
    },
    "meta": {
        "service": "meta",
        "container": "prism-meta",
        "data_dir": f"{BASE_DIR}/data/meta",
        "config": f"{BASE_DIR}/data/meta/config.yaml",
        "registration": f"{BASE_DIR}/data/meta/registration.yaml",
        "synapse_reg": f"{BASE_DIR}/data/synapse/appservice-meta.yaml",
        "db_name": "mautrix_meta",
        "bot_username": "pmb-bot",
        "user_namespace": "meta_",
        "port": 29319,
    },
}

CONTAINERS = {
    "db": "prism-db",
    "synapse": "prism-synapse",
    "tunnel": "prism-tunnel",
    "whatsapp": "prism-whatsapp",
    "meta": "prism-meta",
}

# ---------------------------------------------------------------------------
# SSH Helpers
# ---------------------------------------------------------------------------

def get_ssh() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(RPI_HOST, username=RPI_USER, password=RPI_PASS, timeout=15)
    return client


def run(client: paramiko.SSHClient, cmd: str, sudo: bool = False) -> str:
    """Execute a remote command and return stdout. Raises on stderr."""
    full_cmd = f"sudo {cmd}" if sudo else cmd
    stdin, stdout, stderr = client.exec_command(full_cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if err and "sudo: " in err:
        raise RuntimeError(f"Remote command failed: {full_cmd}\n{err}")
    # Some commands write harmless info to stderr (docker progress, etc.)
    return out


def sudo_run(client: paramiko.SSHClient, cmd: str) -> str:
    return run(client, cmd, sudo=True)


def read_remote_yaml(client: paramiko.SSHClient, path: str) -> dict:
    out = sudo_run(client, f"cat {path}")
    return yaml.safe_load(out) or {}


def write_remote_yaml(client: paramiko.SSHClient, path: str, data: dict):
    payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    sudo_run(client, f"echo {b64} | base64 -d | tee {path} > /dev/null")


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

def check_containers(client: paramiko.SSHClient) -> dict:
    print("🔍 Checking Docker containers...")
    out = run(client, f"cd {BASE_DIR} && docker compose ps --format json 2>/dev/null || docker compose ps")
    status = {}
    for name in CONTAINERS.values():
        status[name] = "down"
        if name in out:
            # Simple heuristic; docker compose ps --format json is preferred
            for line in out.splitlines():
                if name in line and "running" in line.lower():
                    status[name] = "up"
                elif name in line and "healthy" in line.lower():
                    status[name] = "healthy"
    return status


def check_synapse_api(client: paramiko.SSHClient) -> bool:
    try:
        out = run(client, f"curl -sf http://localhost:8008/_matrix/client/versions || echo FAIL")
        return "FAIL" not in out
    except Exception:
        return False


def check_bridge_logs(client: paramiko.SSHClient, container: str) -> str:
    try:
        out = run(client, f"docker logs {container} --tail 5 2>&1")
        return out
    except Exception as e:
        return str(e)


def cmd_check(args):
    client = get_ssh()
    try:
        status = check_containers(client)
        for name, state in status.items():
            emoji = "✅" if state in ("up", "healthy") else "❌"
            print(f"  {emoji} {name}: {state}")

        print("\n🔍 Synapse API...")
        if check_synapse_api(client):
            print("  ✅ Synapse responding on :8008")
        else:
            print("  ❌ Synapse not responding")

        for key, cfg in BRIDGES.items():
            print(f"\n🔍 {key.title()} bridge logs (last 3 lines)...")
            logs = check_bridge_logs(client, cfg["container"])
            for line in logs.strip().splitlines()[-3:]:
                print(f"  {line}")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Bootstrap (two-step)
# ---------------------------------------------------------------------------

def cmd_bootstrap(args):
    bridge = BRIDGES.get(args.bridge)
    if not bridge:
        print(f"❌ Unknown bridge: {args.bridge}")
        sys.exit(1)

    client = get_ssh()
    try:
        print(f"🚀 Bootstrapping {args.bridge} bridge...")

        # Step 1: fix permissions
        print("  Fixing file permissions...")
        sudo_run(client, f"chmod -R 777 {bridge['data_dir']}")

        # Step 2: generate config if missing
        if not run(client, f"test -f {bridge['config']} && echo EXISTS").strip():
            print("  Generating default config.yaml (container will auto-exit)...")
            run(client, f"cd {BASE_DIR} && docker compose run --rm {bridge['service']}")
        else:
            print("  config.yaml already exists, skipping generation.")

        # Step 3: patch config
        print("  Patching config.yaml...")
        patch_bridge_config(client, bridge)

        # Step 4: generate registration if missing
        if not run(client, f"test -f {bridge['registration']} && echo EXISTS").strip():
            print("  Generating registration.yaml (container will auto-exit)...")
            run(client, f"cd {BASE_DIR} && docker compose run --rm {bridge['service']}")
        else:
            print("  registration.yaml already exists, skipping generation.")

        # Step 5: patch registration & sync to synapse
        print("  Patching registration.yaml & syncing to Synapse...")
        patch_bridge_registration(client, bridge)

        # Step 6: restart synapse
        print("  Restarting Synapse to load appservice config...")
        run(client, f"cd {BASE_DIR} && docker compose restart synapse")
        time.sleep(5)

        # Step 7: start bridge
        print("  Starting bridge container...")
        run(client, f"cd {BASE_DIR} && docker compose up -d {bridge['service']}")
        time.sleep(10)

        logs = check_bridge_logs(client, bridge["container"])
        if "Bridge started" in logs:
            print(f"  ✅ {args.bridge.title()} bridge started successfully!")
        else:
            print(f"  ⚠️ Bridge started but check logs manually:")
            print(logs[-500:])
    finally:
        client.close()


def patch_bridge_config(client: paramiko.SSHClient, bridge: dict):
    """Apply PRISM-specific patches to bridge config.yaml."""
    cfg = read_remote_yaml(client, bridge["config"])
    domain = "matrix.fathertkt.uk"
    password = os.environ.get("POSTGRES_PASSWORD", "PrismMvp_2026_Synapse!")

    cfg.setdefault("homeserver", {})
    cfg["homeserver"]["address"] = "http://synapse:8008"
    cfg["homeserver"]["domain"] = domain
    cfg["homeserver"]["software"] = "standard"

    cfg.setdefault("database", {})
    cfg["database"]["type"] = "postgres"
    cfg["database"]["uri"] = f"postgres://synapse:{password}@db/{bridge['db_name']}?sslmode=disable"

    cfg.setdefault("appservice", {})
    cfg["appservice"]["address"] = f"http://{bridge['service']}:{bridge['port']}"
    cfg["appservice"]["hostname"] = "0.0.0.0"
    cfg["appservice"]["port"] = bridge["port"]
    cfg["appservice"]["id"] = bridge["service"]
    cfg["appservice"].setdefault("bot", {})
    cfg["appservice"]["bot"]["username"] = bridge["bot_username"]
    cfg["appservice"]["bot"]["displayname"] = f"{bridge['service'].title()} bridge bot"
    cfg["appservice"]["ephemeral_events"] = True

    cfg.setdefault("encryption", {})
    cfg["encryption"]["allow"] = True
    cfg["encryption"]["default"] = True
    cfg["encryption"]["require"] = False
    cfg["encryption"]["appservice"] = False
    cfg["encryption"]["msc4190"] = False
    cfg["encryption"].setdefault("pickle_key", "mautrix.bridge.e2ee")

    cfg.setdefault("bridge", {})
    cfg["bridge"]["permissions"] = {"*": "relay", domain: "user"}

    cfg["logging"] = {
        "min_level": "info",
        "writers": [{"type": "stdout", "format": "pretty-colored"}],
    }

    if bridge["service"] == "meta":
        cfg.setdefault("network", {})
        cfg["network"]["mode"] = "instagram"

    write_remote_yaml(client, bridge["config"], cfg)


def patch_bridge_registration(client: paramiko.SSHClient, bridge: dict):
    """Fix sender_localpart, namespaces, and copy to Synapse dir."""
    reg = read_remote_yaml(client, bridge["registration"])
    domain = "matrix.fathertkt.uk"

    reg["sender_localpart"] = bridge["bot_username"]
    reg["url"] = f"http://{bridge['service']}:{bridge['port']}"
    reg["rate_limited"] = False
    reg["de.sorunome.msc2409.push_ephemeral"] = True
    reg["receive_ephemeral"] = True
    reg["encryption"] = True

    reg.setdefault("namespaces", {})
    import re
    reg["namespaces"]["users"] = [
        {"regex": f"^@{bridge['bot_username']}:{re.escape(domain)}$", "exclusive": True},
        {"regex": f"^@{bridge['user_namespace']}.*:{re.escape(domain)}$", "exclusive": True},
    ]

    write_remote_yaml(client, bridge["registration"], reg)

    # Copy to synapse dir
    sudo_run(client, f"mkdir -p {os.path.dirname(bridge['synapse_reg'])}")
    sudo_run(client, f"cp {bridge['registration']} {bridge['synapse_reg']}")


# ---------------------------------------------------------------------------
# Fix Registration (idempotent token sync + sender_localpart repair)
# ---------------------------------------------------------------------------

def cmd_fix_registration(args):
    client = get_ssh()
    try:
        for key, bridge in BRIDGES.items():
            print(f"🔧 Fixing {key} registration...")
            if run(client, f"test -f {bridge['registration']} && echo OK").strip() != "OK":
                print(f"  ❌ {bridge['registration']} not found. Run --bootstrap {key} first.")
                continue
            patch_bridge_registration(client, bridge)
            print(f"  ✅ {key} registration synced.")

        print("\n🔄 Restarting Synapse...")
        run(client, f"cd {BASE_DIR} && docker compose restart synapse")
        time.sleep(5)

        for key, bridge in BRIDGES.items():
            run(client, f"cd {BASE_DIR} && docker compose restart {bridge['service']}")
            print(f"  🔄 {key} bridge restarted.")

        print("\n✅ Registration fix complete.")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Disable/Enable Encryption
# ---------------------------------------------------------------------------

def cmd_disable_encryption(args):
    client = get_ssh()
    try:
        for key, bridge in BRIDGES.items():
            print(f"🔒 Disabling encryption for {key}...")
            cfg = read_remote_yaml(client, bridge["config"])
            cfg.setdefault("encryption", {})
            cfg["encryption"]["allow"] = False
            cfg["encryption"]["default"] = False
            write_remote_yaml(client, bridge["config"], cfg)
            run(client, f"cd {BASE_DIR} && docker compose restart {bridge['service']}")
            print(f"  ✅ {key} encryption disabled & restarted.")
    finally:
        client.close()


def cmd_enable_encryption(args):
    client = get_ssh()
    try:
        for key, bridge in BRIDGES.items():
            print(f"🔓 Enabling encryption for {key}...")
            cfg = read_remote_yaml(client, bridge["config"])
            cfg.setdefault("encryption", {})
            cfg["encryption"]["allow"] = True
            cfg["encryption"]["default"] = True
            write_remote_yaml(client, bridge["config"], cfg)
            run(client, f"cd {BASE_DIR} && docker compose restart {bridge['service']}")
            print(f"  ✅ {key} encryption enabled & restarted.")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Patch Synapse sync.py (permanent fix for v1.151+)
# ---------------------------------------------------------------------------

SYNC_HOST_PATH = f"{BASE_DIR}/data/synapse/synapse_handlers_sync.py"
SYNC_CONTAINER_PATH = "/usr/local/lib/python3.13/site-packages/synapse/handlers/sync.py"

def cmd_patch_synapse(args):
    client = get_ssh()
    try:
        print("🔧 Patching Synapse sync.py to re-allow appservice /sync...")

        # Ensure Synapse is running so we can copy the file out
        print("  Ensuring Synapse container is up...")
        run(client, f"cd {BASE_DIR} && docker compose up -d synapse")
        time.sleep(10)

        print("  Copying sync.py from container to host...")
        run(client, f"docker cp prism-synapse:{SYNC_CONTAINER_PATH} {SYNC_HOST_PATH}")

        print("  Applying patch (replace raise NotImplementedError with pass)...")
        sudo_run(client, f"sed -i 's/            raise NotImplementedError()/            pass/' {SYNC_HOST_PATH}")

        print("  Verifying patch...")
        out = sudo_run(client, f"grep -n -A 2 'if app_service:' {SYNC_HOST_PATH} | head -5")
        print(f"    {out.strip()}")

        print("  Adding volume mount to docker-compose.yml...")
        stdin, stdout, stderr = client.exec_command(f'cat {BASE_DIR}/docker-compose.yml')
        compose = stdout.read().decode('utf-8', errors='replace')
        mount_line = f"      - {SYNC_HOST_PATH}:{SYNC_CONTAINER_PATH}:ro"
        if mount_line not in compose:
            compose = compose.replace(
                '      - ./data/synapse:/data',
                f'      - ./data/synapse:/data\n{mount_line}'
            )
            b64 = base64.b64encode(compose.encode('utf-8')).decode('ascii')
            sudo_run(f'echo {b64} | base64 -d | tee {BASE_DIR}/docker-compose.yml > /dev/null')
            print("    Mount added.")
        else:
            print("    Mount already present.")

        print("  Restarting Synapse with patched sync.py...")
        run(client, f"cd {BASE_DIR} && docker compose up -d --force-recreate synapse")
        time.sleep(20)

        out = run(client, "curl -sf http://localhost:8008/_matrix/client/versions || echo FAIL")
        if 'FAIL' in out:
            print("❌ Synapse failed to start after patch. Please investigate logs.")
        else:
            print("✅ Synapse patched and running successfully.")
            print("   Bridges can now use /sync with encryption enabled.")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Reset Bridge DB
# ---------------------------------------------------------------------------

def cmd_reset_db(args):
    bridge = BRIDGES.get(args.bridge)
    if not bridge:
        print(f"❌ Unknown bridge: {args.bridge}")
        sys.exit(1)

    print(f"⚠️  WARNING: This will DROP the {bridge['db_name']} database and")
    print(f"    DELETE all {args.bridge} bridge state (logins, portals, etc.).")
    confirm = input("Type the bridge name to confirm: ")
    if confirm.strip().lower() != args.bridge.lower():
        print("Aborted.")
        return

    client = get_ssh()
    try:
        print(f"🛑 Stopping {args.bridge}...")
        run(client, f"cd {BASE_DIR} && docker compose stop {bridge['service']}")

        print(f"💥 Dropping {bridge['db_name']}...")
        run(client, f"docker exec prism-db psql -U synapse -d postgres -c \"DROP DATABASE IF EXISTS {bridge['db_name']};\"")
        run(client, f"docker exec prism-db psql -U synapse -d postgres -c \"CREATE DATABASE {bridge['db_name']} OWNER synapse;\"")

        print(f"🧹 Cleaning config dir...")
        sudo_run(client, f"rm -f {bridge['data_dir']}/*.db*")

        print(f"🚀 Re-bootstrapping {args.bridge}...")
        # Re-run bootstrap logic inline
        sudo_run(client, f"chmod -R 777 {bridge['data_dir']}")
        run(client, f"cd {BASE_DIR} && docker compose run --rm {bridge['service']}")
        patch_bridge_config(client, bridge)
        run(client, f"cd {BASE_DIR} && docker compose run --rm {bridge['service']}")
        patch_bridge_registration(client, bridge)
        run(client, f"cd {BASE_DIR} && docker compose restart synapse")
        time.sleep(5)
        run(client, f"cd {BASE_DIR} && docker compose up -d {bridge['service']}")
        time.sleep(10)

        logs = check_bridge_logs(client, bridge["container"])
        if "Bridge started" in logs:
            print(f"  ✅ {args.bridge.title()} bridge reset & started!")
        else:
            print(f"  ⚠️ Check logs manually.")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Restart All
# ---------------------------------------------------------------------------

def cmd_restart_all(args):
    client = get_ssh()
    try:
        print("🔄 Restarting all PRISM services...")
        run(client, f"cd {BASE_DIR} && docker compose restart")
        time.sleep(10)
        status = check_containers(client)
        for name, state in status.items():
            emoji = "✅" if state in ("up", "healthy") else "❌"
            print(f"  {emoji} {name}: {state}")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PRISM RPi4 deployment tool")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Health-check all containers & APIs")

    p_boot = sub.add_parser("bootstrap", help="Two-step bootstrap a bridge")
    p_boot.add_argument("bridge", choices=list(BRIDGES.keys()))

    sub.add_parser("fix-registration", help="Sync tokens & fix sender_localpart for both bridges")

    sub.add_parser("patch-synapse", help="Patch Synapse sync.py to re-allow appservice /sync (permanent fix for v1.151+)")
    sub.add_parser("disable-encryption", help="Disable e2ee in both bridges")
    sub.add_parser("enable-encryption", help="Re-enable e2ee in both bridges")

    p_reset = sub.add_parser("reset-db", help="Nuclear reset: drop bridge DB and re-bootstrap")
    p_reset.add_argument("bridge", choices=list(BRIDGES.keys()))

    sub.add_parser("restart-all", help="Restart docker compose stack")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "check": cmd_check,
        "bootstrap": cmd_bootstrap,
        "fix-registration": cmd_fix_registration,
        "patch-synapse": cmd_patch_synapse,
        "disable-encryption": cmd_disable_encryption,
        "enable-encryption": cmd_enable_encryption,
        "reset-db": cmd_reset_db,
        "restart-all": cmd_restart_all,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
