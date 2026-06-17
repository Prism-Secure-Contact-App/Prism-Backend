#!/usr/bin/env python3
"""
Bridge Bot Setup & Registration Script
Oluşturur ve kaydeder: pwb-bot (WhatsApp), pmb-bot (Meta)
"""

import paramiko
import os
import sys
import re
from pathlib import Path


def _load_env():
    """Proje kökündeki .env dosyasından ortam değişkenlerini yükle."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"❌ HATA: '{key}' ortam değişkeni eksik. .env dosyasını kontrol edin.")
        sys.exit(1)
    return val


PI_HOST = _require_env("PI_HOST")
PI_USER = _require_env("PI_USER")
PI_PASS = _require_env("PI_PASS")
SERVER_NAME = _require_env("SERVER_NAME")
MATRIX_DIR = os.environ.get("MATRIX_DIR", "/opt/matrix-server")


def ssh_connect(host, user, password, timeout=30):
    """SSH bağlantısı kur"""
    print(f"🔌 {host} adresine SSH bağlantısı kuruluyor...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=timeout)
    print("✅ SSH bağlantısı başarılı!")
    return client


def run_cmd(client, cmd, timeout=60, print_output=True):
    """Komutu çalıştır ve sonucu döndür"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if print_output and out.strip():
        print(out.strip())
    if err.strip() and "WARNING" not in err.upper():
        print(f"⚠️  STDERR: {err.strip()}")
    return out, err


def sudo_cmd(client, cmd, password):
    """Sudo ile komut çalıştır (şifre stdin üzerinden iletilir)"""
    stdin, stdout, stderr = client.exec_command(f"sudo -S {cmd}")
    stdin.write(password + "\n")
    stdin.flush()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip())
    if err.strip() and "WARNING" not in err.upper() and "[sudo]" not in err:
        print(f"⚠️  STDERR: {err.strip()}")
    return out, err


def step_1_fix_appservices(client):
    """AppService registration dosyalarını düzelt"""
    print("\n" + "=" * 60)
    print("🔧 ADIM 1: AppService Registrations Düzeltme")
    print("=" * 60)

    # WhatsApp registration
    print("📝 WhatsApp registration düzeltiliyor...")
    wa_yaml = f"{MATRIX_DIR}/data/synapse/appservice-whatsapp.yaml"
    
    out, _ = run_cmd(client, f"grep 'sender_localpart' {wa_yaml} 2>&1", print_output=False)
    if "whatsapp-as" in out:
        print("❌ sender_localpart: whatsapp-as (YANLIŞŞ!) → pwb-bot'a düzeltiliyor...")
        run_cmd(client, f"sed -i 's/sender_localpart: whatsapp-as/sender_localpart: pwb-bot/' {wa_yaml}")
        print("✅ WhatsApp registration düzeltildi.")
    elif "pwb-bot" in out:
        print("✅ WhatsApp registration zaten doğru (pwb-bot).")
    
    # Meta registration
    print("📝 Meta registration düzeltiliyor...")
    meta_yaml = f"{MATRIX_DIR}/data/synapse/appservice-meta.yaml"
    
    out, _ = run_cmd(client, f"test -f {meta_yaml} && echo 'EXISTS' || echo 'MISSING'", print_output=False)
    if "MISSING" in out:
        print("⚠️  appservice-meta.yaml yok! configure_meta.py çalıştırılmış olmalı.")
        print("🔄 configure_meta.py çalıştırılıyor...")
        run_cmd(client, f"cd {MATRIX_DIR}/Backend && python3 configure_meta.py")
    else:
        print("✅ appservice-meta.yaml mevcut.")
    
    return True


def step_2_fix_meta_mode(client):
    """Meta bridge'in mode'unu facebook → instagram'a değiştir"""
    print("\n" + "=" * 60)
    print("🔧 ADIM 2: Meta Bridge Mode (instagram)")
    print("=" * 60)

    meta_config = f"{MATRIX_DIR}/data/meta/config.yaml"
    
    out, _ = run_cmd(client, f"grep -A1 'network:' {meta_config} 2>&1 | head -3", print_output=False)
    
    if "mode: instagram" in out:
        print("✅ Meta mode zaten instagram'a ayarlı.")
    else:
        print("🔄 Meta mode instagram'a ayarlanıyor...")
        python_cmd = f"""python3 << 'EOF'
import yaml
cfg_path = '{meta_config}'
with open(cfg_path, 'r') as f:
    cfg = yaml.safe_load(f) or {{}}
cfg.setdefault('network', {{}})
cfg['network']['mode'] = 'instagram'
cfg['network']['receive_instagram_typing_indicators'] = True
with open(cfg_path, 'w') as f:
    yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
print('✅ Meta mode = instagram')
EOF"""
        run_cmd(client, python_cmd)
    
    return True


def step_3_verify_homeserver_yaml(client):
    """homeserver.yaml'ın app_service_config_files'ı kontrol et"""
    print("\n" + "=" * 60)
    print("✔️  ADIM 3: homeserver.yaml Doğrulama")
    print("=" * 60)

    homeserver_yaml = f"{MATRIX_DIR}/data/synapse/homeserver.yaml"
    
    out, _ = run_cmd(client, f"grep -A5 'app_service_config_files:' {homeserver_yaml} 2>&1", print_output=False)
    
    print("📋 Geçerli konfigürasyon:")
    print(out.strip() if out.strip() else "  (boş veya bulunamadı)")
    
    has_wa = "appservice-whatsapp.yaml" in out
    has_meta = "appservice-meta.yaml" in out
    
    if has_wa and has_meta:
        print("✅ Her iki appservice de homeserver.yaml'da kayıtlı!")
    else:
        print("❌ Eksik appservice'ler var!")
        if not has_wa:
            print("  ❌ appservice-whatsapp.yaml eksik")
        if not has_meta:
            print("  ❌ appservice-meta.yaml eksik")
    
    return has_wa and has_meta


def step_4_verify_bot_users(client):
    """pwb-bot ve pmb-bot kullanıcılarının var olup olmadığını kontrol et"""
    print("\n" + "=" * 60)
    print("👤 ADIM 4: Bot Kullanıcılarını Doğrula")
    print("=" * 60)

    # WhatsApp bot
    print("🔍 pwb-bot (WhatsApp bridge bot) kontrol ediliyor...")
    out, _ = run_cmd(
        client,
        f"docker exec prism-db psql -U synapse synapse -tc \"SELECT EXISTS(SELECT 1 FROM users WHERE name = '@pwb-bot:{SERVER_NAME}')\" 2>&1",
        print_output=False
    )
    
    if "t" in out.lower():
        print("✅ pwb-bot kullanıcısı mevcut.")
    else:
        print("⚠️  pwb-bot kullanıcısı bulunamadı. Manual oluşturman gerekebilir.")
    
    # Meta bot
    print("🔍 pmb-bot (Meta bridge bot) kontrol ediliyor...")
    out, _ = run_cmd(
        client,
        f"docker exec prism-db psql -U synapse synapse -tc \"SELECT EXISTS(SELECT 1 FROM users WHERE name = '@pmb-bot:{SERVER_NAME}')\" 2>&1",
        print_output=False
    )
    
    if "t" in out.lower():
        print("✅ pmb-bot kullanıcısı mevcut.")
    else:
        print("⚠️  pmb-bot kullanıcısı bulunamadı. Manual oluşturman gerekebilir.")
    
    return True


def step_5_restart_services(client):
    """Bridge'leri ve Synapse'yi restart et"""
    print("\n" + "=" * 60)
    print("🔄 ADIM 5: Servisleri Restart Etme")
    print("=" * 60)

    print("⏳ Synapse, WhatsApp ve Meta bridge'leri restart ediliyor...")
    run_cmd(client, f"cd {MATRIX_DIR} && docker compose restart synapse whatsapp meta")
    
    print("⏳ 10 saniye bekleniyor...")
    import time
    time.sleep(10)
    
    print("✅ Servisleri restart edildi.")
    return True


def step_6_check_bridge_logs(client):
    """Bridge log'larını kontrol et"""
    print("\n" + "=" * 60)
    print("📊 ADIM 6: Bridge Log'ları")
    print("=" * 60)

    print("\n📍 Synapse appservice kayıtları:")
    out, _ = run_cmd(client, f"docker logs --tail 50 prism-synapse 2>&1 | grep -i 'appservice'", print_output=False)
    print(out.strip()[:500] if out.strip() else "  (log bulunamadı)")
    
    print("\n📍 WhatsApp bridge başlama log'u:")
    out, _ = run_cmd(client, f"docker logs --tail 20 prism-whatsapp 2>&1", print_output=False)
    print(out.strip()[:300] if out.strip() else "  (log bulunamadı)")
    
    print("\n📍 Meta bridge başlama log'u:")
    out, _ = run_cmd(client, f"docker logs --tail 20 prism-meta 2>&1", print_output=False)
    print(out.strip()[:300] if out.strip() else "  (log bulunamadı)")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("🚀 PRISM Bridge Setup & Fix Script")
    print("=" * 60)
    
    client = ssh_connect(PI_HOST, PI_USER, PI_PASS)
    
    try:
        step_1_fix_appservices(client)
        step_2_fix_meta_mode(client)
        step_3_verify_homeserver_yaml(client)
        step_4_verify_bot_users(client)
        step_5_restart_services(client)
        step_6_check_bridge_logs(client)
        
        print("\n" + "=" * 60)
        print("✅ SETUP TAMAMLANDI")
        print("=" * 60)
        print("""
⚠️  SONRAKI ADIMLAR:
1. Bridge'lerin mesaj geçişini kontrol et (test mesajı gönder)
2. Log'larda hata varsa docs/Build/bridge-troubleshooting.md'ye bak
3. Bot user'ları manuel oluşturman gerekirse:
   - Admin API: POST /_synapse/admin/v1/register
   - veya SQL: INSERT INTO users (name, password_hash, ...) VALUES (...)
        """)
    
    finally:
        client.close()


if __name__ == "__main__":
    main()
