#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("=" * 70)
print("📊 CURRENT STATUS")
print("=" * 70)

# Docker ps
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps --filter 'status=running' --filter 'status=restarting'")
output = stdout.read().decode('utf-8')

print("\n✅ RUNNING/RESTARTING CONTAINERS:")
for line in output.split("\n"):
    if "CONTAINER ID" not in line and line.strip():
        print(f"  {line}")

# Synapse logs for appservice errors
stdin, stdout, stderr = c.exec_command("docker logs prism-synapse 2>&1 | grep -i 'appservice' | tail -3")
out = stdout.read().decode('utf-8')

if out.strip():
    print("\n🔍 SYNAPSE APPSERVICE LOGS:")
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
else:
    print("\n✅ SYNAPSE: No appservice errors")

# Check if bridges have generated bridgev2 config
print("\n🔧 BRIDGE CONFIG STATUS:")

for svc in ["whatsapp", "meta"]:
    stdin, stdout, stderr = c.exec_command(f"ls -la {BASE}/data/{svc}/ | grep -E '\\.yaml|\\.yml'")
    out = stdout.read().decode('utf-8')
    
    if "config" in out:
        print(f"  {svc}: Config exists")
        
        # Check if it's bridgev2 format
        stdin, stdout, stderr = c.exec_command(f"grep -c '\"version\".*\"2\"' {BASE}/data/{svc}/config.yaml")
        out = stdout.read().decode('utf-8').strip()
        
        if out == "0":
            print(f"         └─ Still legacy format")
        else:
            print(f"         └─ ✅ Migrated to bridgev2 format")

c.close()
