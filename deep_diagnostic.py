#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

print("="*70)
print("DETAILED BRIDGE DIAGNOSTICS")
print("="*70)

# Check if uploaded configs are there
print("\n1. CURRENT CONFIG FILES (on server):\n")

for svc in ["whatsapp", "meta"]:
    stdin, stdout, stderr = c.exec_command(f"head -15 {BASE}/data/{svc}/config.yaml | tail -5")
    out = stdout.read().decode('utf-8')
    print(f"{svc.upper()} - lines 11-15:")
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line}")
    print()

# Get full last 50 lines of bridge logs
print("\n2. WHATSAPP FULL LOGS (last 50 lines):\n")

stdin, stdout, stderr = c.exec_command("docker logs --tail 50 prism-whatsapp 2>&1")
wa_logs = stdout.read().decode('utf-8')
print(wa_logs)

print("\n" + "="*70)
print("3. META FULL LOGS (last 50 lines):\n")

stdin, stdout, stderr = c.exec_command("docker logs --tail 50 prism-meta 2>&1")
meta_logs = stdout.read().decode('utf-8')
print(meta_logs)

c.close()
