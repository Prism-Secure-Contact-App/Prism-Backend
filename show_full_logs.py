#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

# Get FULL output (not logs but actual stdout/stderr from last start attempt)
print("WHATSAPP CONTAINER FULL OUTPUT:\n")

stdin, stdout, stderr = c.exec_command("docker logs --timestamps prism-whatsapp 2>&1 | head -100")
lines = stdout.read().decode('utf-8').split("\n")

# Show first 30 lines
for line in lines[:30]:
    if line.strip():
        print(line[:120])

print("\n" + "="*70)
print("META CONTAINER FULL OUTPUT:\n")

stdin, stdout, stderr = c.exec_command("docker logs --timestamps prism-meta 2>&1 | head -100")
lines = stdout.read().decode('utf-8').split("\n")

for line in lines[:30]:
    if line.strip():
        print(line[:120])

c.close()
