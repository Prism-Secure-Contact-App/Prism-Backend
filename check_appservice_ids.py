#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("🔍 AppService Registration ID'lerini kontrol et:\n")

for svc in ["whatsapp", "meta"]:
    yaml_file = f"{BASE}/data/synapse/appservice-{svc}.yaml"
    
    print(f"📄 {svc}.yaml:")
    
    stdin, stdout, stderr = c.exec_command(f"head -5 {yaml_file}")
    content = stdout.read().decode('utf-8')
    
    for line in content.split("\n"):
        if "id:" in line:
            print(f"   {line}")
    
    # Tüm içeriği göster
    stdin, stdout, stderr = c.exec_command(f"cat {yaml_file}")
    full = stdout.read().decode('utf-8')
    print(f"\n   Full content:")
    for line in full.split("\n")[:15]:
        print(f"   {line}")
    print()

c.close()
