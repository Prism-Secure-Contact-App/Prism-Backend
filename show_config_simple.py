#!/usr/bin/env python3
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

# WhatsApp config
print("WHATSAPP CONFIG.YAML (ilk 40 satır):\n")
stdin, stdout, stderr = c.exec_command(f"head -40 {BASE}/data/whatsapp/config.yaml")
print(stdout.read().decode('utf-8'))

print("\n" + "="*70 + "\n")

# Meta config  
print("META CONFIG.YAML (ilk 40 satır):\n")
stdin, stdout, stderr = c.exec_command(f"head -40 {BASE}/data/meta/config.yaml")
print(stdout.read().decode('utf-8'))

c.close()
