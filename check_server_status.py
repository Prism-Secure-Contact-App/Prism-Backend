#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

print("=" * 70)
print("📊 SUNUCU DURUM KONTROLÜ")
print("=" * 70)

# Container status
print("\n✅ Container Status:")
stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'")
print(stdout.read().decode('utf-8'))

# WhatsApp logs
print("\n📍 WhatsApp Bridge (son 20 satır):")
stdin, stdout, stderr = c.exec_command("docker logs --tail 20 prism-whatsapp 2>&1")
lines = stdout.read().decode('utf-8').split("\n")
for line in lines[-20:]:
    if line.strip():
        if "error" in line.lower() or "failed" in line.lower():
            print(f"  ❌ {line[:100]}")
        elif "listening" in line.lower() or "started" in line.lower() or "connected" in line.lower():
            print(f"  ✅ {line[:100]}")
        else:
            print(f"  {line[:100]}")

# Meta logs
print("\n📍 Meta Bridge (son 20 satır):")
stdin, stdout, stderr = c.exec_command("docker logs --tail 20 prism-meta 2>&1")
lines = stdout.read().decode('utf-8').split("\n")
for line in lines[-20:]:
    if line.strip():
        if "error" in line.lower() or "failed" in line.lower():
            print(f"  ❌ {line[:100]}")
        elif "listening" in line.lower() or "started" in line.lower() or "connected" in line.lower():
            print(f"  ✅ {line[:100]}")
        else:
            print(f"  {line[:100]}")

# Synapse appservice
print("\n📍 Synapse AppService Status:")
stdin, stdout, stderr = c.exec_command("docker logs --tail 30 prism-synapse 2>&1 | grep -i 'appservice\\|registration\\|permission' | tail -5")
out = stdout.read().decode('utf-8')
if out.strip():
    for line in out.split("\n"):
        if line.strip():
            if "error" in line.lower() or "permission" in line.lower():
                print(f"  ❌ {line[:100]}")
            else:
                print(f"  ✅ {line[:100]}")
else:
    print("  ✅ AppService status OK")

c.close()
