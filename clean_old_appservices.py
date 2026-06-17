#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"
homeserver_yaml = f"{BASE}/data/synapse/homeserver.yaml"

print("🔧 AppService Config Temizleme:\n")

print("❌ SORUN: appservice-instagram.yaml (eski ad) hala homeserver.yaml'da")
print("   Bu appservice-meta.yaml ile çakışıyor!\n")

# appservice-instagram.yaml satırını kaldır
print("🔄 Kaldırılıyor...")

cmd = f"""sed -i '/appservice-instagram.yaml/d' {homeserver_yaml}
"""

stdin, stdout, stderr = c.exec_command(cmd)

print("✅ Kaldırıldı!")

# Kontrol
print("\n✔️  Güncellenmiş durum:")
stdin, stdout, stderr = c.exec_command(f"grep -A5 'app_service_config_files:' {homeserver_yaml}")
print(stdout.read().decode('utf-8'))

# Sunucudaki eski dosyayı da sil
print("\n🗑️  Eski dosya sunucudan siliniyor...")
stdin, stdout, stderr = c.exec_command(f"rm -f {BASE}/data/synapse/appservice-instagram.yaml")
print("✅ Silindi!")

# Synapse restart
print("\n🔄 Synapse restart ediliyor...")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose restart synapse")
stdout.read()

import time
time.sleep(15)

print("✅ Restarted!\n")

# Final check
print("📊 Final Status:")
stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism-synapse' --format '{{.Status}}'")
print(f"  Synapse: {stdout.read().decode('utf-8').strip()}")

stdin, stdout, stderr = c.exec_command("docker logs --tail 5 prism-synapse 2>&1 | grep -i 'error\\|appservice' | tail -3")
out = stdout.read().decode('utf-8')
if out.strip():
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
else:
    print("  ✅ No errors in logs")

c.close()
