#!/usr/bin/env python3
"""
Mautrix bridge image'larını stabil eski version'lara downgrade et
"""
import paramiko
import time

def ssh_run(c, cmd, timeout=120, show_out=True):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_out:
        if out.strip():
            print(out.strip())
        if err.strip() and "WARNING" not in err.upper():
            print(f"⚠️  {err.strip()[:200]}")
    return out, err

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("🔌 Sunucuya bağlanılıyor...")
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)
    print("✅ Bağlandı!\n")
    
    BASE = "/home/fathertkt/prism-backend"
    
    print("=" * 70)
    print("⬇️  MAUTRIX BRIDGE IMAGE DOWNGRADE")
    print("=" * 70)
    
    # docker-compose.yml'i transfer et
    print("\n📤 docker-compose.yml sunucu'ya upload ediliyor...")
    sftp = c.open_sftp()
    try:
        sftp.put(r"c:\Users\knech\Projects\Prism\Backend\docker-compose.yml", 
                f"{BASE}/docker-compose.yml")
        print("✅ Transferred!")
        sftp.close()
    except Exception as e:
        print(f"❌ Transfer hatası: {e}")
        sftp.close()
        return
    
    print("\n" + "=" * 70)
    print("🛑 ADIM 1: Bridge Container'larını Durdur")
    print("=" * 70)
    
    print("⏳ Konteynerler durduruluyor...")
    ssh_run(c, f"cd {BASE} && docker compose stop whatsapp meta", show_out=False)
    
    time.sleep(3)
    
    print("\n" + "=" * 70)
    print("🗑️  ADIM 2: Eski Container'ları Kaldır")
    print("=" * 70)
    
    print("⏳ Konteynerler kaldırılıyor...")
    ssh_run(c, f"cd {BASE} && docker compose rm -f whatsapp meta", show_out=False)
    print("✅ Kaldırıldı!")
    
    print("\n" + "=" * 70)
    print("⬇️  ADIM 3: Yeni Image'ları İndir")
    print("=" * 70)
    
    print("\n🔄 WhatsApp image (v0.11.2) indiriliyor...")
    ssh_run(c, "docker pull dock.mau.dev/mautrix/whatsapp:v0.11.2")
    
    print("\n🔄 Meta image (v0.3.2) indiriliyor...")
    ssh_run(c, "docker pull dock.mau.dev/mautrix/meta:v0.3.2")
    
    print("\n" + "=" * 70)
    print("▶️  ADIM 4: Container'ları Başlat")
    print("=" * 70)
    
    print("\n⏳ Yeni container'lar başlatılıyor...")
    ssh_run(c, f"cd {BASE} && docker compose up -d whatsapp meta")
    
    print("\n⏳ 15 saniye bekleniyor...")
    time.sleep(15)
    
    print("\n" + "=" * 70)
    print("📊 ADIM 5: Durum Kontrolü")
    print("=" * 70)
    
    print("\n✅ Container Status:")
    ssh_run(c, "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'", show_out=True)
    
    print("\n📍 WhatsApp Bridge Logs (son 20 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 20 prism-whatsapp 2>&1")
    lines = stdout.read().decode('utf-8').split("\n")
    
    has_errors = False
    for line in lines[-20:]:
        if line.strip():
            if "error" in line.lower() or "failed" in line.lower() or "legacy" in line.lower():
                print(f"  ❌ {line[:100]}")
                has_errors = True
            elif "listening" in line.lower() or "connected" in line.lower() or "matrix" in line.lower():
                print(f"  ✅ {line[:100]}")
            else:
                print(f"  {line[:100]}")
    
    print("\n📍 Meta Bridge Logs (son 20 satır):")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 20 prism-meta 2>&1")
    lines = stdout.read().decode('utf-8').split("\n")
    
    for line in lines[-20:]:
        if line.strip():
            if "error" in line.lower() or "failed" in line.lower() or "legacy" in line.lower():
                print(f"  ❌ {line[:100]}")
                has_errors = True
            elif "listening" in line.lower() or "connected" in line.lower() or "matrix" in line.lower():
                print(f"  ✅ {line[:100]}")
            else:
                print(f"  {line[:100]}")
    
    print("\n📍 Synapse Appservice Status:")
    stdin, stdout, stderr = c.exec_command("docker logs --tail 10 prism-synapse 2>&1 | grep -i 'appservice\\|loaded\\|registration'")
    out = stdout.read().decode('utf-8')
    if out.strip():
        for line in out.split("\n"):
            if line.strip():
                if "error" in line.lower():
                    print(f"  ❌ {line[:100]}")
                else:
                    print(f"  ✅ {line[:100]}")
    else:
        print("  ✅ No errors in appservice logs")
    
    c.close()
    
    print("\n" + "=" * 70)
    if not has_errors:
        print("✅ DOWNGRADE BAŞARILI!")
        print("=" * 70)
        print("""
Bridge'ler artık eski versiyonda çalışıyor (legacy config destekli).

Sonraki adımlar:
1. Matrix client'tan login yap
2. WhatsApp bridge bot'unu (@pwb-bot) cevaplarında test et
3. Meta bridge bot'unu (@pmb-bot) test et
4. Mesaj geçişini kontrol et

Hala sorun varsa:
- docker logs prism-whatsapp
- docker logs prism-meta
        """)
    else:
        print("⚠️  DOWNGRADE TAMAMLANDI AMA HATALAR VAR")
        print("=" * 70)
        print("Log'lardaki hataları kontrol edin yukarıda!")
    
if __name__ == "__main__":
    main()
