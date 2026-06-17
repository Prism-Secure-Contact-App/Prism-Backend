#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"
meta_yaml = f"{BASE}/data/synapse/appservice-meta.yaml"

print("🔧 Meta AppService Registration Düzeltme:\n")

print("❌ HATALAR:")
print("  - URL: http://synapse:8008 (YANLIŞ)")
print("  - sender_localpart: RZtCoRO7VPcDPsJ0jOZLQhHzPZHsaDVp (YANLIŞ)")

print("\n✅ DÜZELTMELER:")
print("  - URL: http://meta:29319 (DOĞRU)")
print("  - sender_localpart: pmb-bot (DOĞRU)")

print("\n🔄 Düzeltiliyor...")

# Meta yaml'ı düzelt
cmd = f"""sed -i 's|url: http://synapse:8008|url: http://meta:29319|g' {meta_yaml}
sed -i 's|sender_localpart: RZtCoRO7VPcDPsJ0jOZLQhHzPZHsaDVp|sender_localpart: pmb-bot|g' {meta_yaml}
"""

stdin, stdout, stderr = c.exec_command(cmd)
stdout.read()

print("✅ Düzeltildi!")

print("\n✔️  Kontrol:")
stdin, stdout, stderr = c.exec_command(f"grep -E '^(id|url|sender_localpart)' {meta_yaml}")
for line in stdout.read().decode('utf-8').split("\n"):
    if line.strip():
        print(f"  {line}")

print("\n🔄 Services restart ediliyor...")

# Synapse restart (appservice config yüklenmek için)
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose restart synapse whatsapp meta")
stdout.read()

import time
time.sleep(15)

print("✅ Servisleri restart edildi\n")

# Status kontrol
print("📊 Durum:")
stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'")
print(stdout.read().decode('utf-8'))

c.close()
