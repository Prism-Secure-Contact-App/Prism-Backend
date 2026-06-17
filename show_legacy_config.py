#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("=" * 70)
print("📋 CURRENT LEGACY CONFIG STRUCTURE")
print("=" * 70)

for svc in ["whatsapp", "meta"]:
    print(f"\n{'='*70}")
    print(f"  {svc.upper()} config.yaml")
    print(f"{'='*70}\n")
    
    cfg_file = f"{BASE}/data/{svc}/config.yaml"
    
    stdin, stdout, stderr = c.exec_command(f"cat {cfg_file}")
    content = stdout.read().decode('utf-8')
    
    # First 100 lines
    lines = content.split("\n")[:50]
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}: {line}")
    
    if len(content.split("\n")) > 50:
        print("\n... [truncated] ...")

c.close()
