#!/usr/bin/env python3
"""
Mautrix container'ları config migration mode'da çalıştır (generate mode)
Bu, legacy config'i yeni formata convert edecek
"""
import paramiko
import time

def ssh_run(c, cmd, timeout=180, show=True):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip():
            print(out.strip()[:500])
        if err.strip() and "pulled" not in err.lower():
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
    print("🔄 CONFIG MIGRATION (Bridge Generator Mode)")
    print("=" * 70)
    
    # Container'ları durdur
    print("\n1️⃣  Container'ları durdur...")
    ssh_run(c, f"cd {BASE} && docker compose stop whatsapp meta", show=False)
    time.sleep(5)
    
    # Config klasörleri temizle ama YAML'ları sakla
    print("\n2️⃣  Config'leri backup et...")
    ssh_run(c, f"cd {BASE}/data && cp -v whatsapp/config.yaml whatsapp/config.yaml.bak 2>/dev/null; cp -v meta/config.yaml meta/config.yaml.bak 2>/dev/null", show=False)
    
    # WhatsApp generator mod
    print("\n3️⃣  WhatsApp bridge'i migration mod'da çalıştır...")
    print("   ⏳ Container generator mod'da başlatılıyor...")
    
    cmd = f"""cd {BASE} && docker run --rm \\
  -v {BASE}/data/whatsapp:/data \\
  dock.mau.dev/mautrix/whatsapp:latest \\
  -c /data/config.yaml \\
  -r /data/registration.yaml \\
  --no-crypto \\
  2>&1 | head -50
"""
    out, _ = ssh_run(c, cmd, timeout=120, show=False)
    if "generated" in out.lower() or "config" in out.lower():
        print("   ✅ Migration yapıldı")
    else:
        print("   ⚠️  Sonuç belirsiz, log'ları kontrol edin")
    
    # Meta generator mod
    print("\n4️⃣  Meta bridge'i migration mod'da çalıştır...")
    print("   ⏳ Container generator mod'da başlatılıyor...")
    
    cmd = f"""cd {BASE} && docker run --rm \\
  -v {BASE}/data/meta:/data \\
  dock.mau.dev/mautrix/meta:latest \\
  -c /data/config.yaml \\
  -r /data/registration.yaml \\
  --no-crypto \\
  2>&1 | head -50
"""
    out, _ = ssh_run(c, cmd, timeout=120, show=False)
    if "generated" in out.lower() or "config" in out.lower():
        print("   ✅ Migration yapıldı")
    else:
        print("   ⚠️  Sonuç belirsiz, log'ları kontrol edin")
    
    # Configure scripts'i çalıştır (migration sonrası)
    print("\n5️⃣  Configure scripts'i çalıştır...")
    
    cmd = f"cd {BASE}/Backend && python3 configure_whatsapp.py 2>&1"
    out, _ = ssh_run(c, cmd, show=False)
    print("   ✅ WhatsApp configured")
    
    cmd = f"cd {BASE}/Backend && python3 configure_meta.py 2>&1"
    out, _ = ssh_run(c, cmd, show=False)
    print("   ✅ Meta configured")
    
    # Permission'ları düzelt
    print("\n6️⃣  Permission'ları düzelt...")
    ssh_run(c, f"sudo chmod 666 {BASE}/data/whatsapp/config.yaml {BASE}/data/meta/config.yaml", show=False)
    ssh_run(c, f"sudo chmod 666 {BASE}/data/synapse/appservice-*.yaml", show=False)
    print("   ✅ Permissions updated")
    
    # Container'ları başlat
    print("\n7️⃣  Container'ları başlat...")
    ssh_run(c, f"cd {BASE} && docker compose up -d whatsapp meta", show=False)
    
    print("   ⏳ 25 saniye bekleniyor...")
    time.sleep(25)
    
    print("\n" + "=" * 70)
    print("📊 FINAL DURUM KONTROLÜ")
    print("=" * 70)
    
    print("\n✅ Container Status:")
    ssh_run(c, "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'", show=True)
    
    print("\n📍 WhatsApp Bridge (son 10 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 10 prism-whatsapp 2>&1")
    for line in stdout.read().decode('utf-8').split("\n")[-10:]:
        if line.strip():
            if "error" in line.lower():
                print(f"  ❌ {line[:100]}")
            elif "matrix" in line.lower() or "started" in line.lower():
                print(f"  ✅ {line[:100]}")
            else:
                print(f"  {line[:100]}")
    
    print("\n📍 Meta Bridge (son 10 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 10 prism-meta 2>&1")
    for line in stdout.read().decode('utf-8').split("\n")[-10:]:
        if line.strip():
            if "error" in line.lower():
                print(f"  ❌ {line[:100]}")
            elif "matrix" in line.lower() or "started" in line.lower():
                print(f"  ✅ {line[:100]}")
            else:
                print(f"  {line[:100]}")
    
    # Synapse check
    print("\n📍 Synapse Appservice (son 5 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 5 prism-synapse 2>&1")
    out = stdout.read().decode('utf-8')
    if "permission" in out.lower():
        print("  ❌ Permission error detected")
    elif "error" in out.lower():
        print("  ❌ Error detected")
    else:
        print("  ✅ Synapse logs OK")
    
    c.close()
    
    print("\n" + "=" * 70)
    print("✅ SETUP TAMAMLANDI")
    print("=" * 70)

if __name__ == "__main__":
    main()
