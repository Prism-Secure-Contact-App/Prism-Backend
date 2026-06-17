#!/usr/bin/env python3
import paramiko
import time

print("Starting SSH connection...")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30, auth_timeout=30)

print("Connected. Reading WhatsApp config...")
BASE = "/home/fathertkt/prism-backend"

# Use docker exec instead to avoid SSH timeout
stdin, stdout, stderr = c.exec_command(f'docker exec prism-synapse cat /data/whatsapp/config.yaml', timeout=30)
wa_config = stdout.read(timeout=30).decode('utf-8')

print(f"WhatsApp config retrieved: {len(wa_config)} bytes")

# Read Meta config
stdin, stdout, stderr = c.exec_command(f'docker exec prism-synapse cat /data/meta/config.yaml', timeout=30)
meta_config = stdout.read(timeout=30).decode('utf-8')

print(f"Meta config retrieved: {len(meta_config)} bytes")

c.close()

# Save
with open("whatsapp_config.yaml", "w") as f:
    f.write(wa_config)
with open("meta_config.yaml", "w") as f:
    f.write(meta_config)

print("✅ Saved locally")
