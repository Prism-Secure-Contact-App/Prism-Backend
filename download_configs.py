#!/usr/bin/env python3
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)

BASE = "/home/fathertkt/prism-backend"

# Read WhatsApp config
stdin, stdout, stderr = c.exec_command(f"cat {BASE}/data/whatsapp/config.yaml")
wa_config = stdout.read().decode('utf-8')

# Read Meta config
stdin, stdout, stderr = c.exec_command(f"cat {BASE}/data/meta/config.yaml")
meta_config = stdout.read().decode('utf-8')

c.close()

# Save locally
with open("c:\\Users\\knech\\Projects\\Prism\\Backend\\whatsapp_current_config.yaml", "w") as f:
    f.write(wa_config)

with open("c:\\Users\\knech\\Projects\\Prism\\Backend\\meta_current_config.yaml", "w") as f:
    f.write(meta_config)

print("✅ Config files downloaded locally")
print(f"✅ WhatsApp: {len(wa_config)} bytes")
print(f"✅ Meta: {len(meta_config)} bytes")
