#!/usr/bin/env python3
import paramiko
import time

print("Updating bridge images to versions with legacy config support...\n")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)

BASE = "/home/fathertkt/prism-backend"

# Upload updated docker-compose.yml
print("1. Uploading updated docker-compose.yml...\n")

sftp = c.open_sftp()
sftp.put("docker-compose.yml", f"{BASE}/docker-compose.yml")
sftp.close()

print("   ✅ Uploaded")

# Pull new images
print("\n2. Pulling new image versions...\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose pull whatsapp meta")
output = stdout.read().decode('utf-8')

for line in output.split("\n"):
    if "Pulling\|Downloaded\|Digest" in line or "v0." in line:
        print(f"   {line[:100]}")

# Stop old containers
print("\n3. Stopping old containers...\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose down")
stdout.read()
print("   ✅ Stopped")

time.sleep(5)

# Start new containers
print("\n4. Starting containers with new images...\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose up -d whatsapp meta")
stdout.read()
print("   ✅ Started")

time.sleep(20)

# Check status
print("\n5. Container Status:\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

for line in out.split("\n"):
    if "prism-whatsapp\|prism-meta" in line or "CONTAINER" in line:
        print(f"   {line}")

print("\n✅ Update complete!")

c.close()
