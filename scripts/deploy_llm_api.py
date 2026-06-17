#!/usr/bin/env python3
"""
PRISM LLM API Service Deployment Script

Safely deploys llm_api_service.py to RPi4 with:
- Pre-flight health checks
- Automatic backup of previous version
- Zero-downtime container rebuild
- Post-deployment verification
- Automatic rollback on failure

Usage:
    python3 Backend/scripts/deploy_llm_api.py
"""

import paramiko
import time
import sys
import os
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RPI_HOST = "100.125.63.77"
RPI_USER = "fathertkt"
RPI_PASS = "1234"
REMOTE_BASE = "/home/fathertkt/prism-backend"
REMOTE_SERVICE_FILE = f"{REMOTE_BASE}/llm_api_service.py"
LOCAL_SERVICE_FILE = "Backend/llm_api_service.py"
CONTAINER_NAME = "prism-llm-api"
HEALTH_URL = "http://localhost:8080/health"

# ---------------------------------------------------------------------------
# SSH Helpers
# ---------------------------------------------------------------------------

def get_ssh() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(RPI_HOST, username=RPI_USER, password=RPI_PASS, timeout=15)
    return client


def run(client: paramiko.SSHClient, cmd: str, sudo: bool = False) -> tuple:
    """Execute remote command and return (stdout, stderr, exit_status)."""
    full_cmd = f"echo {RPI_PASS} | sudo -S {cmd}" if sudo else cmd
    stdin, stdout, stderr = client.exec_command(full_cmd)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    exit_status = stdout.channel.recv_exit_status()
    return out, err, exit_status


def check_container(client: paramiko.SSHClient) -> dict:
    """Check current container status."""
    out, err, code = run(client, f"cd {REMOTE_BASE} && docker compose ps {CONTAINER_NAME} --format json")
    if code != 0:
        return {"running": False, "error": err or out}
    return {"running": "running" in out.lower() or "Up" in out, "output": out}


def health_check(client: paramiko.SSHClient, retries: int = 6, delay: int = 5) -> bool:
    """Poll health endpoint until healthy or exhausted."""
    for i in range(retries):
        out, err, code = run(client, f"curl -sf {HEALTH_URL} || echo FAIL")
        if code == 0 and "FAIL" not in out and "ok" in out.lower():
            print(f"  ✅ Health check passed (attempt {i+1}/{retries}): {out}")
            return True
        print(f"  ⏳ Health check attempt {i+1}/{retries}... (response: {out or 'no response'})")
        time.sleep(delay)
    return False


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------

def deploy():
    print("=" * 60)
    print("🚀 PRISM LLM API Service Deployment")
    print(f"   Target: {RPI_HOST} ({RPI_USER})")
    print(f"   File:   {LOCAL_SERVICE_FILE}")
    print("=" * 60)

    # Verify local file exists
    if not os.path.exists(LOCAL_SERVICE_FILE):
        print(f"❌ Local file not found: {LOCAL_SERVICE_FILE}")
        sys.exit(1)

    client = get_ssh()
    try:
        # 1. Pre-flight: container status
        print("\n🔍 Pre-flight checks...")
        status = check_container(client)
        if status.get("running"):
            print(f"  ✅ Container '{CONTAINER_NAME}' is currently running.")
        else:
            print(f"  ⚠️ Container '{CONTAINER_NAME}' is not running. Will start after deploy.")

        # 2. Backup current version
        print("\n💾 Creating backup...")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{REMOTE_SERVICE_FILE}.bak.{ts}"
        out, err, code = run(client, f"test -f {REMOTE_SERVICE_FILE} && cp {REMOTE_SERVICE_FILE} {backup_path}")
        if code == 0:
            print(f"  ✅ Backup saved: {backup_path}")
        else:
            print(f"  ⚠️ No existing file to backup (fresh deploy).")

        # 3. Upload new file via SFTP
        print("\n📤 Uploading new llm_api_service.py...")
        sftp = client.open_sftp()
        sftp.put(LOCAL_SERVICE_FILE, REMOTE_SERVICE_FILE)
        sftp.close()
        print(f"  ✅ Uploaded to {REMOTE_SERVICE_FILE}")

        # Verify upload
        out, err, code = run(client, f"head -c 50 {REMOTE_SERVICE_FILE}")
        if code != 0:
            raise RuntimeError(f"Upload verification failed: {err}")

        # 4. Rebuild & restart container
        print("\n🔧 Rebuilding and restarting container...")
        out, err, code = run(
            client,
            f"cd {REMOTE_BASE} && docker compose up -d --build --force-recreate {CONTAINER_NAME}",
            sudo=True,
        )
        if code != 0:
            raise RuntimeError(f"Docker compose failed:\nSTDOUT: {out}\nSTDERR: {err}")
        print(f"  ✅ Container rebuilt and restarted.")
        print(f"     Docker output:\n{out[:500]}")

        # 5. Post-deployment health check
        print("\n🏥 Post-deployment health check (waiting for service startup)...")
        time.sleep(3)  # Give uvicorn a moment to boot
        if health_check(client):
            print("\n" + "=" * 60)
            print("🎉 DEPLOYMENT SUCCESSFUL!")
            print("=" * 60)
            print(f"   Backup:  {backup_path}")
            print(f"   Service: {HEALTH_URL}")
            return
        else:
            raise RuntimeError("Health check failed after deployment.")

    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        rollback(client, backup_path if 'backup_path' in dir() else None)
        sys.exit(1)
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback(client: paramiko.SSHClient, backup_path: str = None):
    print("\n🔄 Rolling back to previous version...")
    try:
        if backup_path:
            out, err, code = run(client, f"cp {backup_path} {REMOTE_SERVICE_FILE}")
            if code == 0:
                print(f"  ✅ Restored from backup: {backup_path}")
            else:
                print(f"  ⚠️ Failed to restore backup: {err}")
                return

            out, err, code = run(
                client,
                f"cd {REMOTE_BASE} && docker compose up -d --build --force-recreate {CONTAINER_NAME}",
                sudo=True,
            )
            if code == 0:
                print(f"  ✅ Previous version restarted.")
            else:
                print(f"  ❌ Failed to restart previous version:\n{err}")
        else:
            print("  ⚠️ No backup available for rollback.")
    except Exception as e:
        print(f"  ❌ Rollback error: {e}")


if __name__ == "__main__":
    deploy()
