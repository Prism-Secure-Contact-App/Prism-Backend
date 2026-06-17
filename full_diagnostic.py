#!/usr/bin/env python3
import paramiko
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

print("="*80)
print("🔍 COMPREHENSIVE BRIDGE DIAGNOSTICS")
print("="*80)

# 1. Container status
print("\n1️⃣  CONTAINER STATUS:\n")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
lines = stdout.read().decode('utf-8').split("\n")
for line in lines:
    if any(x in line for x in ["CONTAINER", "prism-whatsapp", "prism-meta", "prism-synapse"]):
        print(f"   {line}")

# 2. Check config files exist
print("\n2️⃣  CONFIG FILES:\n")
for svc in ["whatsapp", "meta"]:
    stdin, stdout, stderr = c.exec_command(f"ls -lh {BASE}/data/{svc}/config.yaml")
    out = stdout.read().decode('utf-8').strip()
    if "No such file" in out or not out:
        print(f"   ❌ {svc}: CONFIG FILE MISSING!")
    else:
        print(f"   ✅ {svc}: {out.split()[-1]} ({out.split()[4]})")

# 3. Check for registration files
print("\n3️⃣  APPSERVICE REGISTRATIONS:\n")
for f in ["appservice-whatsapp.yaml", "appservice-meta.yaml"]:
    stdin, stdout, stderr = c.exec_command(f"ls -lh {BASE}/data/synapse/{f}")
    out = stdout.read().decode('utf-8').strip()
    if "No such file" in out or not out:
        print(f"   ❌ {f}: NOT FOUND")
    else:
        print(f"   ✅ {f}: OK")

# 4. Last 30 lines of each bridge log (COMPLETE ERROR MESSAGE)
print("\n4️⃣  WHATSAPP BRIDGE LOGS (last 30 lines):\n")
stdin, stdout, stderr = c.exec_command("docker logs --tail 30 prism-whatsapp 2>&1")
wa_logs = stdout.read().decode('utf-8')
for line in wa_logs.split("\n")[-35:]:
    if line.strip():
        print(f"   {line[:100]}")

print("\n5️⃣  META BRIDGE LOGS (last 30 lines):\n")
stdin, stdout, stderr = c.exec_command("docker logs --tail 30 prism-meta 2>&1")
meta_logs = stdout.read().decode('utf-8')
for line in meta_logs.split("\n")[-35:]:
    if line.strip():
        print(f"   {line[:100]}")

# 5. Check Synapse for errors
print("\n6️⃣  SYNAPSE LOGS (appservice section):\n")
stdin, stdout, stderr = c.exec_command("docker logs --tail 50 prism-synapse 2>&1 | grep -i 'appservice\\|meta\\|whatsapp\\|error' | tail -20")
out = stdout.read().decode('utf-8')
for line in out.split("\n"):
    if line.strip():
        print(f"   {line[:100]}")

# 6. Check if containers can reach each other
print("\n7️⃣  NETWORK CONNECTIVITY TEST:\n")
stdin, stdout, stderr = c.exec_command("docker network ls | grep prism")
out = stdout.read().decode('utf-8').strip()
print(f"   Network: {out.split()[0] if out else 'default'}")

# 7. Check database
print("\n8️⃣  DATABASE STATUS:\n")
stdin, stdout, stderr = c.exec_command("docker exec prism-db psql -U synapse -c '\\l' 2>&1 | grep -E 'synapse|whatsapp|meta|List'")
out = stdout.read().decode('utf-8')
for line in out.split("\n"):
    if line.strip():
        print(f"   {line[:80]}")

# 8. Docker exec test
print("\n9️⃣  DOCKER EXEC CONNECTIVITY:\n")
stdin, stdout, stderr = c.exec_command("docker exec prism-synapse echo 'Synapse OK'")
print(f"   Synapse: {stdout.read().decode('utf-8').strip()}")

stdin, stdout, stderr = c.exec_command("docker exec prism-db echo 'DB OK'")
print(f"   Database: {stdout.read().decode('utf-8').strip()}")

stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism-whatsapp' --format '{{.State}}'")
state = stdout.read().decode('utf-8').strip()
print(f"   WhatsApp state: {state if state else 'unknown'}")

c.close()

print("\n" + "="*80)
