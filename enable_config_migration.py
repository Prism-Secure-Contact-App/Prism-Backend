#!/usr/bin/env python3
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("🔧 Bridge Container'lara Config Migration Flag Ekleniyor...\n")

# docker-compose.yml'yi oku
print("1️⃣  docker-compose.yml güncelleniyor...\n")

cmd = f"""python3 << 'PYEOF'
import yaml

with open('{BASE}/docker-compose.yml', 'r') as f:
    dc = yaml.safe_load(f)

# WhatsApp service'ine env variable ekle
if 'services' in dc and 'whatsapp' in dc['services']:
    svc = dc['services']['whatsapp']
    if 'environment' not in svc:
        svc['environment'] = []
    
    # Varsa bunu kaldır
    svc['environment'] = [e for e in svc['environment'] if 'MAUTRIX_LEGACY_CONFIG_MIGRATOR' not in str(e)]
    
    # Yeni değeri ekle
    svc['environment'].append({{'MAUTRIX_LEGACY_CONFIG_MIGRATOR': 'true'}})
    print("✅ WhatsApp service updated")

# Meta service'ine env variable ekle
if 'services' in dc and 'meta' in dc['services']:
    svc = dc['services']['meta']
    if 'environment' not in svc:
        svc['environment'] = []
    
    # Varsa bunu kaldır
    svc['environment'] = [e for e in svc['environment'] if 'MAUTRIX_LEGACY_CONFIG_MIGRATOR' not in str(e)]
    
    # Yeni değeri ekle
    svc['environment'].append({{'MAUTRIX_LEGACY_CONFIG_MIGRATOR': 'true'}})
    print("✅ Meta service updated")

with open('{BASE}/docker-compose.yml', 'w') as f:
    yaml.dump(dc, f, default_flow_style=False, sort_keys=False)

print("✅ docker-compose.yml yazıldı")
PYEOF
"""

stdin, stdout, stderr = c.exec_command(cmd)
out = stdout.read().decode('utf-8')
print(out)

err = stderr.read().decode('utf-8')
if err:
    print(f"⚠️  Stderr: {err[:200]}")

# Container'ları restart et
print("\n2️⃣  Bridge containers restarting...\n")

for svc in ['whatsapp', 'meta']:
    print(f"  🔄 {svc} restarting...")
    stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose restart {svc}")
    stdout.read()

print("\n✅ Restarting!")
time.sleep(20)

# Status check
print("\n📊 Status:\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps")
out = stdout.read().decode('utf-8')
for line in out.split("\n"):
    if "prism-" in line and ("whatsapp" in line or "meta" in line or "synapse" in line):
        print(line[:100])

# Logs check
print("\n📋 WhatsApp Logs (son 5 satır):")
stdin, stdout, stderr = c.exec_command("docker logs --tail 5 prism-whatsapp 2>&1")
for line in stdout.read().decode('utf-8').split("\n")[-6:-1]:
    if line.strip():
        print(f"  {line[:90]}")

c.close()
