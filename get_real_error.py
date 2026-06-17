#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

# Get first real error/status from logs (skip the repeated warnings)
stdin, stdout, stderr = c.exec_command("docker logs prism-whatsapp 2>&1 | grep -v 'Legacy bridge config' | head -50")
out = stdout.read().decode('utf-8')

if not out.strip():
    print("WhatsApp logs (filtered - no real errors found):")
    print("  Only showing: Legacy bridge config warnings")
    print("\nTrying full output (first 100 lines):")
    stdin, stdout, stderr = c.exec_command("docker logs prism-whatsapp 2>&1 | head -100")
    out = stdout.read().decode('utf-8')
    print(out[:1500])
else:
    print("WhatsApp logs (without warnings):")
    print(out)

c.close()
