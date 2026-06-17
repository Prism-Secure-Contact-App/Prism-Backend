#!/usr/bin/env python3
"""
Bridge config'lerini yeniden generate et (mautrix generator mod)
"""
import paramiko
import time

def ssh_run(c, cmd, timeout=120):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
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
    print("🔄 BRIDGE CONFIG REGENERATION (Generator Mode)")
    print("=" * 70)
    
    # WhatsApp
    print("\n1️⃣  WhatsApp Config Regeneration:")
    print("   ⏳ Container'ı generator mod'da çalıştırıyor...")
    cmd = f"cd {BASE} && docker run --rm -v {BASE}/data/whatsapp:/data dock.mau.dev/mautrix/whatsapp:latest -c /data/config.yaml -r /data/registration.yaml -g"
    ssh_run(c, cmd, timeout=60)
    
    print("   ✅ WhatsApp config generated!")
    
    # Meta
    print("\n2️⃣  Meta Config Regeneration:")
    print("   ⏳ Container'ı generator mod'da çalıştırıyor...")
    cmd = f"cd {BASE} && docker run --rm -v {BASE}/data/meta:/data dock.mau.dev/mautrix/meta:latest -c /data/config.yaml -r /data/registration.yaml -g"
    ssh_run(c, cmd, timeout=60)
    
    print("   ✅ Meta config generated!")
    
    print("\n" + "=" * 70)
    print("🔧 CONFIGURE SCRIPTS RUNNING")
    print("=" * 70)
    
    # Local environment'dan configure scriptlerini sunucu'ya gönder
    print("\n📤 configure_whatsapp.py sunucu'ya upload ediliyor...")
    sftp = c.open_sftp()
    
    local_wa_config = r"c:\Users\knech\Projects\Prism\Backend\configure_whatsapp.py"
    local_meta_config = r"c:\Users\knech\Projects\Prism\Backend\configure_meta.py"
    
    remote_wa_config = f"{BASE}/Backend/configure_whatsapp.py"
    remote_meta_config = f"{BASE}/Backend/configure_meta.py"
    
    try:
        # Backend klasörünü oluştur
        stdin, stdout, stderr = c.exec_command(f"mkdir -p {BASE}/Backend")
        
        # Dosyaları transfer et
        sftp.put(local_wa_config, remote_wa_config)
        print(f"   ✅ {remote_wa_config}")
        
        sftp.put(local_meta_config, remote_meta_config)
        print(f"   ✅ {remote_meta_config}")
        
        sftp.close()
    except Exception as e:
        print(f"   ⚠️  Transfer hatası: {e}")
        sftp.close()
    
    # Configure scripts'i çalıştır
    print("\n🔄 configure_whatsapp.py çalıştırılıyor...")
    cmd = f"cd {BASE}/Backend && python3 configure_whatsapp.py"
    ssh_run(c, cmd)
    
    print("\n🔄 configure_meta.py çalıştırılıyor...")
    cmd = f"cd {BASE}/Backend && python3 configure_meta.py"
    ssh_run(c, cmd)
    
    print("\n" + "=" * 70)
    print("🔄 SERVISLERI RESTART ET")
    print("=" * 70)
    
    print("\n⏳ Containers restart ediliyor...")
    cmd = f"cd {BASE} && docker compose restart synapse whatsapp meta"
    ssh_run(c, cmd)
    
    print("\n⏳ 20 saniye bekleniyor...")
    time.sleep(20)
    
    print("\n" + "=" * 70)
    print("📊 KONTROL & LOGS")
    print("=" * 70)
    
    # Container status
    print("\n✅ Container Status:")
    cmd = "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'"
    ssh_run(c, cmd)
    
    # WhatsApp log
    print("\n📍 WhatsApp Bridge (son 15 satır):")
    cmd = "docker logs --tail 15 prism-whatsapp 2>&1"
    out, _ = ssh_run(c, cmd)
    lines = out.split("\n")[-15:]
    for line in lines:
        if line.strip():
            print(f"  {line}")
    
    # Meta log
    print("\n📍 Meta Bridge (son 15 satır):")
    cmd = "docker logs --tail 15 prism-meta 2>&1"
    out, _ = ssh_run(c, cmd)
    lines = out.split("\n")[-15:]
    for line in lines:
        if line.strip():
            print(f"  {line}")
    
    # Synapse log
    print("\n📍 Synapse AppService (son 20 satır):")
    cmd = "docker logs --tail 20 prism-synapse 2>&1 | grep -i 'appservice\\|registration\\|POST /_matrix/app' || echo '(event bulunamadı)'"
    out, _ = ssh_run(c, cmd)
    
    c.close()
    
    print("\n" + "=" * 70)
    print("✅ BRIDGE CONFIG REGENERATION TAMAMLANDI!")
    print("=" * 70)
    print("""
📝 Sonraki Adımlar:
1. Container'ların UP ve HEALTHY olduğunu kontrol et
2. Bridge log'larında error kalıp kalmadığını kontrol et
3. Test mesajı gönder ve bridge'in cevap verip vermediğini kontrol et
4. Sorun varsa check_bridges.py çalıştır
    """)

if __name__ == "__main__":
    main()
