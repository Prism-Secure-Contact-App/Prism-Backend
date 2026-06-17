#!/usr/bin/env python3
import paramiko
import os
import time

print("Connecting to server...")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

print("\n1. Config files uploading...\n")

# Use SFTP for file transfer (more reliable)
sftp = c.open_sftp()

# Upload corrected configs
print("   WhatsApp config uploading...")
sftp.put("whatsapp_current_config.yaml", f"{BASE}/data/whatsapp/config.yaml")
print("   ✅ Uploaded")

print("   Meta config uploading...")
sftp.put("meta_current_config.yaml", f"{BASE}/data/meta/config.yaml")
print("   ✅ Uploaded")

sftp.close()

print("\n2. Bridge containers restarting...\n")

# Restart bridges
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose restart whatsapp meta")
stdout.read()
print("   🔄 Restart command sent")

time.sleep(15)

print("   ⏳ Waiting for containers to start...")
time.sleep(15)

# Check status
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

print("\n3. Container Status:\n")
for line in out.split("\n"):
    if "CONTAINER" in line or "prism-" in line:
        print(f"   {line}")

# Check for database connection in logs
print("\n4. Database Connection Check:\n")

for svc in ["whatsapp", "meta"]:
    stdin, stdout, stderr = c.exec_command(f"docker logs --tail 10 prism-{svc} 2>&1 | grep -i 'database\\|connection\\|error' | head -3")
    out = stdout.read().decode('utf-8')
    
    print(f"   {svc.upper()}:")
    if out.strip():
        for line in out.split("\n")[:3]:
            if line.strip():
                print(f"      {line[:100]}")
    else:
        print(f"      ✅ No database errors detected")

c.close()

print("\n✅ Done!")
