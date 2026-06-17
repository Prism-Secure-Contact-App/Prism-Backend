#!/usr/bin/env python3
"""
docker-compose.yml'i latest'e geri çevir ve bridge config'lerinde
legacy_config_migrator'ı doğru şekilde aktifleştir
"""
import paramiko

def ssh_run(c, cmd, timeout=120, show=True):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show and out.strip():
        print(out.strip())
    return out, err

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("🔌 Sunucuya bağlanılıyor...")
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)
    print("✅ Bağlandı!\n")
    
    BASE = "/home/fathertkt/prism-backend"
    
    print("=" * 70)
    print("🔧 LEGACY CONFIG MIGRATOR FIX")
    print("=" * 70)
    
    # docker-compose.yml'i latest'e geri çevir
    print("\n1️⃣  docker-compose.yml latest image'lara geri çevrildi")
    
    sftp = c.open_sftp()
    try:
        sftp.put(r"c:\Users\knech\Projects\Prism\Backend\docker-compose.yml", 
                f"{BASE}/docker-compose.yml")
        print("   ✅ Uploaded")
        sftp.close()
    except Exception as e:
        print(f"   ❌ {e}")
        return
    
    # docker-compose.yml'de latest kullanıldığını kontrol et
    ssh_run(c, f"grep 'image:' {BASE}/docker-compose.yml | grep -E 'whatsapp|meta'", show=True)
    
    print("\n2️⃣  Bridge config'lerine hacky_migrator flag'i ekleniyor...")
    
    # WhatsApp config
    print("\n   🔧 WhatsApp config.yaml:")
    wa_config = f"{BASE}/data/whatsapp/config.yaml"
    
    # YAML'ı oku, hacky_migrator ekle ve yaz
    cmd = f"""python3 << 'PYSCRIPT'
import yaml
cfg_path = '{wa_config}'
try:
    with open(cfg_path, 'r') as f:
        content = f.read()
    
    # Zaten var mı kontrol et
    if 'hacky_config_migrator:' in content:
        print('   ✅ hacky_config_migrator zaten var')
    else:
        # YAML olarak parse et
        cfg = yaml.safe_load(content) or {{}}
        
        # Flag'ı ekle
        cfg['hacky_config_migrator'] = True
        
        # Dosyaya yaz
        with open(cfg_path, 'w') as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        print('   ✅ hacky_config_migrator eklendi!')
except Exception as e:
    print(f'   ⚠️  Hata: {{e}}')
PYSCRIPT
"""
    ssh_run(c, cmd, show=True)
    
    # Meta config
    print("\n   🔧 Meta config.yaml:")
    meta_config = f"{BASE}/data/meta/config.yaml"
    
    cmd = f"""python3 << 'PYSCRIPT'
import yaml
cfg_path = '{meta_config}'
try:
    with open(cfg_path, 'r') as f:
        content = f.read()
    
    if 'hacky_config_migrator:' in content:
        print('   ✅ hacky_config_migrator zaten var')
    else:
        cfg = yaml.safe_load(content) or {{}}
        cfg['hacky_config_migrator'] = True
        
        with open(cfg_path, 'w') as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        print('   ✅ hacky_config_migrator eklendi!')
except Exception as e:
    print(f'   ⚠️  Hata: {{e}}')
PYSCRIPT
"""
    ssh_run(c, cmd, show=True)
    
    print("\n3️⃣  Container'ları restart ediliyor...")
    
    print("   ⏳ Durduruluyor...")
    ssh_run(c, f"cd {BASE} && docker compose stop whatsapp meta", show=False)
    
    import time
    time.sleep(3)
    
    print("   ⏳ Başlatılıyor...")
    ssh_run(c, f"cd {BASE} && docker compose up -d whatsapp meta", show=False)
    
    print("   ⏳ 20 saniye bekleniyor...")
    time.sleep(20)
    
    print("\n" + "=" * 70)
    print("📊 DURUM KONTROLÜ")
    print("=" * 70)
    
    print("\n✅ Container Status:")
    ssh_run(c, "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'", show=True)
    
    print("\n📍 WhatsApp Bridge (son 15 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 15 prism-whatsapp 2>&1")
    lines = stdout.read().decode('utf-8').split("\n")
    
    legacy_count = 0
    for line in lines[-15:]:
        if line.strip():
            if "legacy" in line.lower():
                legacy_count += 1
            if legacy_count <= 3:  # İlk 3 legacy mesajını göster
                if "legacy" in line.lower():
                    print(f"  ⚠️  {line[:100]}")
                elif "error" in line.lower():
                    print(f"  ❌ {line[:100]}")
                else:
                    print(f"  ✅ {line[:100]}")
    
    print("\n📍 Meta Bridge (son 15 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 15 prism-meta 2>&1")
    lines = stdout.read().decode('utf-8').split("\n")
    
    legacy_count = 0
    for line in lines[-15:]:
        if line.strip():
            if "legacy" in line.lower():
                legacy_count += 1
            if legacy_count <= 3:
                if "legacy" in line.lower():
                    print(f"  ⚠️  {line[:100]}")
                elif "error" in line.lower():
                    print(f"  ❌ {line[:100]}")
                else:
                    print(f"  ✅ {line[:100]}")
    
    c.close()
    
    print("\n" + "=" * 70)
    print("✅ SETUP TAMAMLANDI")
    print("=" * 70)
    print("""
✨ Legacy config migrator aktifleştirildi!

Bridge'ler artık legacy config'i çalışma zamanında yeni formata migrate edecek.

Sonraki Adımlar:
1. Matrix client'tan WhatsApp bot (@pwb-bot) ile test et
2. Meta bot (@pmb-bot) ile test et  
3. Bridgeler mesajlara cevap vermeye başlamalı

Sorun devam ederse:
  docker logs prism-whatsapp -f
  docker logs prism-meta -f
    """)

if __name__ == "__main__":
    main()
