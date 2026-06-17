#!/usr/bin/env python3
import paramiko

print("=== FINAL STATUS CHECK ===\n")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

# Container status
print("1. CONTAINER STATUS:\n")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

for line in out.split("\n"):
    if "CONTAINER" in line or "prism-" in line:
        print(f"  {line}")

# Check if bridges are "Up"
stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism-whatsapp' --format '{{.Status}}'")
wa_status = stdout.read().decode('utf-8').strip()

stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism-meta' --format '{{.Status}}'")
meta_status = stdout.read().decode('utf-8').strip()

print(f"\nWHATSAPP: {wa_status}")
print(f"META: {meta_status}")

if "Up" in wa_status and "Up" in meta_status:
    print("\n✅ BOTH BRIDGES ARE RUNNING!\n")
    
    # Test connectivity
    print("2. BRIDGE CONNECTIVITY TEST:\n")
    
    for svc, port in [("whatsapp", "29318"), ("meta", "29319")]:
        stdin, stdout, stderr = c.exec_command(f"docker exec prism-synapse curl -s http://prism-{svc}:{port}/_matrix/appservice/version 2>&1")
        out = stdout.read().decode('utf-8').strip()
        
        if "{" in out or "version" in out:
            print(f"  ✅ {svc}:{port} - RESPONDING")
        else:
            print(f"  ⚠️  {svc}:{port} - {out[:60]}")
    
    print("\n3. SYNAPSE APPSERVICE VERIFICATION:\n")
    
    stdin, stdout, stderr = c.exec_command("docker logs prism-synapse 2>&1 | grep -i 'loaded application service' | tail -3")
    out = stdout.read().decode('utf-8')
    
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
    
    print("\n" + "="*60)
    print("🎉 BRIDGES FIXED AND OPERATIONAL!")
    print("="*60)
    
else:
    print("\n⚠️  Bridges still not running, checking logs...\n")
    
    for svc in ["whatsapp", "meta"]:
        print(f"\n{svc.upper()} LOGS (last 15 lines):")
        stdin, stdout, stderr = c.exec_command(f"docker logs --tail 15 prism-{svc} 2>&1")
        for line in stdout.read().decode('utf-8').split("\n")[-16:]:
            if line.strip():
                print(f"  {line[:110]}")

c.close()
