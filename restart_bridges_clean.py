#!/usr/bin/env python3
import paramiko
import time

print("Connecting and fixing bridge issues...")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)

BASE = "/home/fathertkt/prism-backend"

# Stop all containers
print("\n1. Stopping all containers...\n")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose down")
stdout.read()
print("   ✅ Stopped")

time.sleep(5)

# Use SFTP to upload corrected configs
print("\n2. Uploading corrected configs (with password=1234)...\n")

sftp = c.open_sftp()

try:
    sftp.put("whatsapp_current_config.yaml", f"{BASE}/data/whatsapp/config.yaml")
    print("   ✅ WhatsApp config uploaded")
except Exception as e:
    print(f"   ⚠️  WhatsApp upload: {e}")

try:
    sftp.put("meta_current_config.yaml", f"{BASE}/data/meta/config.yaml")
    print("   ✅ Meta config uploaded")
except Exception as e:
    print(f"   ⚠️  Meta upload: {e}")

sftp.close()

# Verify configs
print("\n3. Verifying uploaded configs...\n")

stdin, stdout, stderr = c.exec_command(f"grep 'PrismMvp\\|synapse:1234' {BASE}/data/whatsapp/config.yaml")
out = stdout.read().decode('utf-8')

if "1234" in out:
    print("   ✅ WhatsApp config: password updated to 1234")
elif "PrismMvp" in out:
    print("   ❌ WhatsApp config: STILL HAS OLD PASSWORD")
else:
    print("   ⚠️  WhatsApp config: couldn't verify")

# Start containers again
print("\n4. Starting all containers...\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose up -d")
stdout.read()
print("   ✅ Started")

time.sleep(15)

# Final status
print("\n5. Container Status:\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

for line in out.split("\n"):
    if "prism-" in line:
        print(f"   {line}")

c.close()

print("\n✅ Done!\n")
