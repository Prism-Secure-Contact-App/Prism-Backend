#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("🔧 Config File'lara Legacy Config Migrator Flag Ekleniyor...\n")

for svc in ["whatsapp", "meta"]:
    cfg = f"{BASE}/data/{svc}/config.yaml"
    print(f"📝 {svc} config.yaml güncelleniyor...\n")
    
    cmd = f"""python3 << 'PYEOF'
import yaml

with open('{cfg}', 'r') as f:
    config = yaml.safe_load(f)

# Network section'na hacky migrator flag'i ekle
if 'network' not in config:
    config['network'] = {{}}

config['network']['hacky_legacy_config_migrator'] = True
print(f"✅ Config updated: hacky_legacy_config_migrator = True")

with open('{cfg}', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f"✅ File yazıldı")
PYEOF
"""
    
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode('utf-8')
    print(out)
    
    err = stderr.read().decode('utf-8')
    if err:
        print(f"⚠️  Error: {err[:100]}")

# Container'ları restart et
print("\n🔄 Container'lar Restarting...\n")

stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose restart whatsapp meta")
stdout.read()

import time
time.sleep(30)

# Check logs for migration success
print("✅ Restarted!\n")
print("📋 Checking for successful migration...\n")

for svc in ["whatsapp", "meta"]:
    print(f"  {svc}:")
    stdin, stdout, stderr = c.exec_command(f"docker logs --tail 10 prism-{svc} 2>&1 | grep -i 'legacy\\|migrat\\|error' | head -3")
    out = stdout.read().decode('utf-8')
    
    if not out.strip():
        print(f"    ✅ No legacy config warnings")
    else:
        for line in out.split("\n")[:3]:
            if line.strip():
                print(f"    {line[:80]}")

c.close()
