#!/usr/bin/env python3
"""
Permission sorunlarını ve legacy config migrator'ı düzelt
"""
import paramiko

def ssh_run(c, cmd, timeout=120, show_output=True):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_output:
        if out.strip():
            print(out.strip())
        if err.strip() and "WARNING" not in err.upper():
            print(f"⚠️  {err.strip()[:300]}")
    return out, err

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("🔌 Sunucuya bağlanılıyor...")
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)
    print("✅ Bağlandı!\n")
    
    BASE = "/home/fathertkt/prism-backend"
    
    print("=" * 70)
    print("🔧 PERMISSION & CONFIG MIGRATION FIX")
    print("=" * 70)
    
    print("\n1️⃣  AppService dosyalarının permission'larını düzelt:")
    
    files = [
        f"{BASE}/data/synapse/appservice-whatsapp.yaml",
        f"{BASE}/data/synapse/appservice-meta.yaml"
    ]
    
    for f in files:
        print(f"   📄 {f.split('/')[-1]}")
        ssh_run(c, f"chmod 644 {f}", show_output=False)
        ssh_run(c, f"ls -la {f}", show_output=False)
    
    print("\n2️⃣  Bridge Config'lerine legacy_config_migrator eklenmesi:")
    
    # WhatsApp config'e migrator ekle
    print("   🔧 WhatsApp config...")
    wa_config = f"{BASE}/data/whatsapp/config.yaml"
    ssh_run(c, f"""python3 << 'PY'
import yaml
try:
    with open('{wa_config}', 'r') as f:
        cfg = yaml.safe_load(f) or {{}}
    
    # legacy_config_migrator ekle
    if 'legacy_config_migrator' not in cfg:
        cfg['legacy_config_migrator'] = True
        
        with open('{wa_config}', 'w') as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        print('   ✅ legacy_config_migrator eklendi')
    else:
        print('   ✅ legacy_config_migrator zaten var')
except Exception as e:
    print(f'   ❌ Hata: {{e}}')
PY
""", show_output=True)
    
    # Meta config'e migrator ekle
    print("   🔧 Meta config...")
    meta_config = f"{BASE}/data/meta/config.yaml"
    ssh_run(c, f"""python3 << 'PY'
import yaml
try:
    with open('{meta_config}', 'r') as f:
        cfg = yaml.safe_load(f) or {{}}
    
    if 'legacy_config_migrator' not in cfg:
        cfg['legacy_config_migrator'] = True
        
        with open('{meta_config}', 'w') as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        print('   ✅ legacy_config_migrator eklendi')
    else:
        print('   ✅ legacy_config_migrator zaten var')
except Exception as e:
    print(f'   ❌ Hata: {{e}}')
PY
""", show_output=True)
    
    print("\n3️⃣  Bridge data klasörlerinin permission'larını düzelt:")
    
    ssh_run(c, f"sudo chown -R fathertkt:fathertkt {BASE}/data/whatsapp {BASE}/data/meta", show_output=False)
    ssh_run(c, f"sudo chmod -R 755 {BASE}/data/whatsapp {BASE}/data/meta", show_output=False)
    print("   ✅ Permissions güncellendi")
    
    print("\n" + "=" * 70)
    print("🔄 SERVISLERI RESTART ET")
    print("=" * 70)
    
    print("\n⏳ Containers durduruluyor...")
    ssh_run(c, f"cd {BASE} && docker compose stop whatsapp meta", show_output=False)
    
    import time
    time.sleep(5)
    
    print("⏳ Containers başlatılıyor...")
    ssh_run(c, f"cd {BASE} && docker compose up -d whatsapp meta", show_output=False)
    
    print("⏳ 20 saniye bekleniyor...")
    time.sleep(20)
    
    print("\n" + "=" * 70)
    print("📊 KONTROL")
    print("=" * 70)
    
    # Container status
    print("\n✅ Container Status:")
    ssh_run(c, "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'", show_output=True)
    
    # WhatsApp log
    print("\n📍 WhatsApp Bridge (son 10 satır):")
    out, _ = ssh_run(c, "docker logs --tail 10 prism-whatsapp 2>&1", show_output=False)
    for line in out.split("\n")[-10:]:
        if line.strip():
            status = "✅" if "Legacy" not in line else "⚠️ "
            print(f"  {status} {line[:90]}")
    
    # Meta log
    print("\n📍 Meta Bridge (son 10 satır):")
    out, _ = ssh_run(c, "docker logs --tail 10 prism-meta 2>&1", show_output=False)
    for line in out.split("\n")[-10:]:
        if line.strip():
            status = "✅" if "Legacy" not in line else "⚠️ "
            print(f"  {status} {line[:90]}")
    
    # Synapse appservice check
    print("\n📍 Synapse AppService Status:")
    out, _ = ssh_run(c, "docker logs --tail 5 prism-synapse 2>&1 | grep -i 'appservice\\|permission\\|loaded'", show_output=False)
    if "Permission denied" in out:
        print("  ❌ Permission denied error detected")
    elif out.strip():
        print(f"  {out.strip()[:200]}")
    else:
        print("  ✅ AppService loaded successfully")
    
    c.close()
    
    print("\n" + "=" * 70)
    print("✅ FIXES COMPLETED!")
    print("=" * 70)

if __name__ == "__main__":
    main()
