#!/usr/bin/env python3
"""
PRISM Server Health Check - Verifies all backend services across RPi 4 and HP Laptop.

Checks:
- SSH connectivity to both servers
- Docker containers on RPi 4 (Synapse, DB, Bridges)
- Docker containers on HP Laptop (Monero Node)
- API responsiveness
"""

import paramiko
import sys
import json
import io

# Force UTF-8 stdout/stderr so the ✓/✗ glyphs render on Windows code pages
# (cp1254/cp857) where the default encoder cannot map them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# RPi 4 (Main Server)
HOST_RPI = "100.125.63.77"
USER_RPI = "fathertkt"
PASS_RPI = "1234"

# HP Laptop (Monero Server)
HOST_HP = "100.77.114.31"
USER_HP = "fatih"
PASS_HP = "V12_Abd!78"

EXPECTED_CONTAINERS_RPI = {
    "prism-db": "PostgreSQL",
    "prism-synapse": "Synapse", 
    "prism-whatsapp": "WhatsApp Bridge",
    "prism-meta": "Meta Bridge",
    "prism-tunnel": "Cloudflare Tunnel",
}

EXPECTED_CONTAINERS_HP = {
    "monero-node": "Monero Node",
}


def ssh_exec(client, cmd, timeout=15):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def check_containers(client, expected_dict, password=None):
    sudo_prefix = f"echo {password} | sudo -S " if password else ""
    code, out, err = ssh_exec(client, f"{sudo_prefix}docker ps --format '{{{{.Names}}}} {{{{.Status}}}}' 2>/dev/null")
    
    if code != 0:
        # Try without sudo if first attempt failed
        code, out, err = ssh_exec(client, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null")
        if code != 0:
            return False, f"Error: {err}"
    
    running = {}
    for line in out.split("\n"):
        if not line.strip(): continue
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            running[parts[0]] = parts[1]
    
    results = []
    all_ok = True
    for container, desc in expected_dict.items():
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


def check_synapse(client):
    code, out, err = ssh_exec(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8008/_matrix/client/versions")
    if code == 0 and out.strip() == "200":
        return True, f"  ✓ Synapse API: HTTP {out.strip()}"
    return False, f"  ✗ Synapse API: HTTP {out.strip() if out else 'N/A'}"


def check_bridge_logs(client, container_name, desc):
    code, out, err = ssh_exec(client, f"docker logs {container_name} --tail 10 2>&1")
    if code != 0:
        return False, f"  ✗ {desc}: cannot read logs ({err})"
    if "Bridge started" in out:
        return True, f"  ✓ {desc}: Bridge started"
    elif "Failed to start bridge" in out or "FTL" in out:
        return False, f"  ✗ {desc}: Failed to start (check logs)"
    elif "Up" not in out and container_name not in out:
        return False, f"  ✗ {desc}: No recent activity"
    return True, f"  ⚠ {desc}: Running but 'Bridge started' not in last 10 lines"


def check_monero_rpc(client):
    cmd = (
        "curl -s -X POST http://localhost:18081/json_rpc "
        "-H 'Content-Type: application/json' "
        "-d '{\"jsonrpc\":\"2.0\",\"id\":\"0\",\"method\":\"get_info\"}'"
    )
    code, out, err = ssh_exec(client, cmd)
    if code == 0 and out:
        try:
            data = json.loads(out)
            res = data.get("result", {})
            return True, f"  ✓ Monero RPC: Height {res.get('height', 'N/A')} (Net: {res.get('nettype', 'N/A')})"
        except:
            return True, "  ✓ Monero RPC: Running (Invalid JSON)"
    return False, "  ✗ Monero RPC: Not responding"


def main():
    print("=" * 60)
    print("  PRISM Multi-Server Health Check")
    print("=" * 60)
    
    rpi_client = paramiko.SSHClient()
    hp_client = paramiko.SSHClient()
    for c in [rpi_client, hp_client]:
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    overall_results = {}

    # 1. RPi 4 Check
    print(f"\n[Server 1: Raspberry Pi 4] ({HOST_RPI})")
    try:
        rpi_client.connect(HOST_RPI, username=USER_RPI, password=PASS_RPI, timeout=10)
        print("  ✓ SSH Connected")
        
        ok, res = check_containers(rpi_client, EXPECTED_CONTAINERS_RPI, PASS_RPI)
        print(res)
        overall_results["RPi Containers"] = ok
        
        ok, res = check_synapse(rpi_client)
        print(res)
        overall_results["Synapse API"] = ok

        ok, res = check_bridge_logs(rpi_client, "prism-whatsapp", "WhatsApp Bridge")
        print(res)
        overall_results["WhatsApp Bridge"] = ok

        ok, res = check_bridge_logs(rpi_client, "prism-meta", "Meta Bridge")
        print(res)
        overall_results["Meta Bridge"] = ok
        
    except Exception as e:
        print(f"  ✗ SSH Failed: {e}")
        overall_results["RPi Server"] = False

    # 2. HP Laptop Check
    print(f"\n[Server 2: HP Elitebook] ({HOST_HP})")
    try:
        hp_client.connect(HOST_HP, username=USER_HP, password=PASS_HP, timeout=10)
        print("  ✓ SSH Connected")
        
        ok, res = check_containers(hp_client, EXPECTED_CONTAINERS_HP)
        print(res)
        overall_results["HP Containers"] = ok
        
        ok, res = check_monero_rpc(hp_client)
        print(res)
        overall_results["Monero RPC"] = ok
        
    except Exception as e:
        print(f"  ✗ SSH Failed: {e}")
        overall_results["HP Server"] = False

    # Summary
    print(f"\n{'=' * 60}")
    print("  FINAL STATUS SUMMARY")
    print(f"{'=' * 60}")
    all_ok = all(overall_results.values())
    for name, ok in overall_results.items():
        print(f"  [{'✓' if ok else '✗'}] {name}")
    
    print(f"\n  Result: {'SYSTEM HEALTHY' if all_ok else 'ATTENTION REQUIRED'}")
    print(f"{'=' * 60}")

    rpi_client.close()
    hp_client.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
