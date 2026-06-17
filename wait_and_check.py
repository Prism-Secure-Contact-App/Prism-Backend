#!/usr/bin/env python3
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("⏳ Container başlatılmasını bekliyorum...\n")
time.sleep(30)

# Final check
print("📊 FINAL STATUS:\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

print(out)

# Bridge logs
print("\n📋 Bridge Logs Check:\n")

for svc in ["whatsapp", "meta"]:
    print(f"  {svc.upper()}:")
    stdin, stdout, stderr = c.exec_command(f"docker logs --tail 3 prism-{svc} 2>&1")
    for line in stdout.read().decode('utf-8').split("\n")[-4:-1]:
        if line.strip():
            print(f"    {line[:95]}")

c.close()
