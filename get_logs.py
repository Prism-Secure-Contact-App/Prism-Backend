#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120)

BASE = "/home/fathertkt/prism-backend"

# Container status
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')

print("CONTAINER STATUS:")
for line in out.split("\n"):
    if "CONTAINER" in line or "prism-" in line:
        print(line)

print("\n" + "="*60)
print("WHATSAPP LOGS (last 15 lines):")
print("="*60)

stdin, stdout, stderr = c.exec_command("docker logs --tail 15 prism-whatsapp 2>&1")
out = stdout.read().decode('utf-8')
for line in out.split("\n"):
    if line.strip():
        print(line[:120])

print("\n" + "="*60)
print("META LOGS (last 15 lines):")
print("="*60)

stdin, stdout, stderr = c.exec_command("docker logs --tail 15 prism-meta 2>&1")
out = stdout.read().decode('utf-8')
for line in out.split("\n"):
    if line.strip():
        print(line[:120])

c.close()
