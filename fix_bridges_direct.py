#!/usr/bin/env python3
"""
Sunucu üzerinde bridge config'lerini direkt olarak tamir et
"""
import paramiko
import sys

def ssh_run(client, cmd, print_out=True):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_out and out.strip():
        print(out.strip())
    if err.strip() and "WARNING" not in err.upper():
        print(f"⚠️  {err.strip()[:200]}")
    return out, err

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("🔌 Sunucuya bağlanılıyor (100.125.63.77)...")
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)
    print("✅ Bağlandı!\n")
    
    BASE = "/home/fathertkt/prism-backend"
    
    print("=" * 60)
    print("🔧 ADIM 1: AppService Registrations Düzeltme")
    print("=" * 60)
    
    # WhatsApp appservice - sender_localpart düzelt
    print("\n1️⃣  WhatsApp appservice registration:")
    wa_yaml = f"{BASE}/data/synapse/appservice-whatsapp.yaml"
    out, _ = ssh_run(c, f"grep 'sender_localpart' {wa_yaml}", print_out=False)
    
    if "whatsapp-as" in out:
        print("  ❌ sender_localpart: whatsapp-as (YANLIŞŞ!)")
        print("  🔄 pwb-bot'a düzeltiliyor...")
        ssh_run(c, f"sed -i 's/sender_localpart: whatsapp-as/sender_localpart: pwb-bot/' {wa_yaml}")
        print("  ✅ Düzeltildi!")
    elif "pwb-bot" in out:
        print("  ✅ sender_localpart zaten pwb-bot (doğru)")
    else:
        print("  ❓ sender_localpart bulunamadı")
    
    # Meta appservice - kontrol et / oluştur
    print("\n2️⃣  Meta appservice registration:")
    meta_yaml = f"{BASE}/data/synapse/appservice-meta.yaml"
    out, _ = ssh_run(c, f"[ -f {meta_yaml} ] && echo 'EXISTS' || echo 'MISSING'", print_out=False)
    
    if "MISSING" in out:
        print("  ⚠️  appservice-meta.yaml bulunamadı")
        print("  🔄 configure_meta.py çalıştırılıyor...")
        
        # configure_meta.py'ı sunucu'da çalıştır (eğer var ise) veya oluştur
        # Basit workaround: YAML'ı direkt oluştur
        meta_content = """id: meta
url: http://prism-meta:29319
as_token: syt_cG1iLWJvdA_OcmvDGjRLredQJWbCaTm_2UU61p
hs_token: syt_hs_meta_JpjYVmeJOFUcGhoTDaDi_25zyI1
sender_localpart: pmb-bot
rate_limited: false
namespaces:
    users:
        - regex: ^@pmb-bot:matrix.fathertkt.uk$
          exclusive: true
        - regex: ^@meta_.*:matrix.fathertkt.uk$
          exclusive: true
de.sorunome.msc2409.push_ephemeral: true
receive_ephemeral: true
encryption: true
"""
        # YAML dosyasını sunucuya yaz (cat + heredoc)
        cmd = f"""cat > {meta_yaml} << 'YAML_EOF'
{meta_content}
YAML_EOF
"""
        ssh_run(c, cmd)
        print("  ✅ appservice-meta.yaml oluşturuldu!")
    else:
        print("  ✅ appservice-meta.yaml mevcut")
    
    print("\n" + "=" * 60)
    print("🔧 ADIM 2: Meta Bridge Config (Instagram Mode)")
    print("=" * 60)
    
    meta_config = f"{BASE}/data/meta/config.yaml"
    out, _ = ssh_run(c, f"grep -A1 'mode:' {meta_config} | head -2", print_out=False)
    
    if "instagram" in out:
        print("✅ Meta mode zaten instagram'a ayarlı")
    else:
        print("🔄 Meta mode instagram'a ayarlanıyor...")
        ssh_run(c, f"sed -i '/^network:/,/^[^ ]/ {{ s/mode: .*/mode: instagram/; }}' {meta_config}")
        print("✅ Düzeltildi!")
    
    print("\n" + "=" * 60)
    print("🔧 ADIM 3: homeserver.yaml AppService Registration")
    print("=" * 60)
    
    homeserver_yaml = f"{BASE}/data/synapse/homeserver.yaml"
    out, _ = ssh_run(c, f"grep -A5 'app_service_config_files:' {homeserver_yaml}", print_out=False)
    
    has_wa = "appservice-whatsapp.yaml" in out
    has_meta = "appservice-meta.yaml" in out
    
    print(f"  WhatsApp registration: {'✅' if has_wa else '❌'}")
    print(f"  Meta registration: {'✅' if has_meta else '❌'}")
    
    if not has_wa or not has_meta:
        print("\n🔄 homeserver.yaml güncelleniyor...")
        
        if not has_wa and not has_meta:
            ssh_run(c, f"""sed -i '/^app_service_config_files:/a\\
  - /data/appservice-whatsapp.yaml\\
  - /data/appservice-meta.yaml' {homeserver_yaml}""")
        elif not has_meta:
            ssh_run(c, f"""sed -i '/appservice-whatsapp.yaml/a\\
  - /data/appservice-meta.yaml' {homeserver_yaml}""")
        
        print("✅ homeserver.yaml güncellendi!")
    
    print("\n" + "=" * 60)
    print("🔄 ADIM 4: Servisleri Restart Etme")
    print("=" * 60)
    
    print("⏳ Synapse, WhatsApp ve Meta bridge'leri restart ediliyor...")
    ssh_run(c, f"cd {BASE} && docker compose restart synapse whatsapp meta")
    
    print("⏳ 15 saniye bekleniyor...")
    import time
    time.sleep(15)
    print("✅ Done!")
    
    print("\n" + "=" * 60)
    print("📊 ADIM 5: Kontrol & Log'lar")
    print("=" * 60)
    
    # Container status
    print("\n📍 Container Status:")
    out, _ = ssh_run(c, "docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'", print_out=False)
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line}")
    
    # Synapse log'u
    print("\n📍 Synapse AppService Events (son 20 satır):")
    out, _ = ssh_run(c, "docker logs --tail 20 prism-synapse 2>&1 | grep -i 'appservice\\|registration' || echo '(log bulunamadı)'", print_out=False)
    for line in out.split("\n")[-10:]:
        if line.strip():
            print(f"  {line[:100]}")
    
    # Bridge log'ları
    print("\n📍 WhatsApp Bridge (son 10 satır):")
    out, _ = ssh_run(c, "docker logs --tail 10 prism-whatsapp 2>&1", print_out=False)
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
    
    print("\n📍 Meta Bridge (son 10 satır):")
    out, _ = ssh_run(c, "docker logs --tail 10 prism-meta 2>&1", print_out=False)
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
    
    c.close()
    
    print("\n" + "=" * 60)
    print("✅ BRIDGE SETUP TAMAMLANDI!")
    print("=" * 60)

if __name__ == "__main__":
    main()
