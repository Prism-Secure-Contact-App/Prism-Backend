#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"
homeserver_yaml = f"{BASE}/data/synapse/homeserver.yaml"

print("🔍 homeserver.yaml'da app_service_config_files:\n")

stdin, stdout, stderr = c.exec_command(f"grep -A10 'app_service_config_files:' {homeserver_yaml}")
content = stdout.read().decode('utf-8')
print(content)

print("\n" + "=" * 70)

# Duplicate kontrol
lines = content.split("\n")
config_files = []
for line in lines:
    if ".yaml" in line:
        config_files.append(line.strip())

print(f"\n📋 AppService files ({len(config_files)} toplam):")
for f in config_files:
    print(f"  {f}")

if len(config_files) != len(set(config_files)):
    print("\n⚠️  DUPLICATE APPSERVICE BULUNDU!")
    
    # Duplicates'i kaldır
    print("\n🔧 Düzeltiliyor...")
    
    cmd = f"""python3 << 'PY'
import re

with open('{homeserver_yaml}', 'r') as f:
    content = f.read()

# app_service_config_files section'ını bul ve duplicate'leri kaldır
match = re.search(r'app_service_config_files:.*?(?=\n[a-z_]|$)', content, re.DOTALL)
if match:
    section = match.group()
    lines = section.split('\n')
    
    # Unique entries koru
    seen = set()
    new_lines = [lines[0]]  # app_service_config_files: header'ı koru
    
    for line in lines[1:]:
        if line.strip() and '.yaml' in line:
            if line.strip() not in seen:
                new_lines.append(line)
                seen.add(line.strip())
        elif line.strip():
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    new_section = '\n'.join(new_lines)
    content = content[:match.start()] + new_section + content[match.end():]
    
    with open('{homeserver_yaml}', 'w') as f:
        f.write(content)
    
    print('✅ Duplicates kaldırıldı!')
else:
    print('❌ app_service_config_files section bulunamadı')
PY
"""
    stdin, stdout, stderr = c.exec_command(cmd)
    print(stdout.read().decode('utf-8'))
else:
    print("\n✅ Duplicate yok")

print("\n✔️  Güncellenmiş durum:")
stdin, stdout, stderr = c.exec_command(f"grep -A5 'app_service_config_files:' {homeserver_yaml}")
print(stdout.read().decode('utf-8'))

c.close()
