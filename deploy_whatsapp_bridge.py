#!/usr/bin/env python3
"""
WhatsApp Bridge Deployment Script for Matrix Synapse (Raspberry Pi 4)

Bu script Raspberry Pi 4'e SSH ile bağlanıp mautrix-whatsapp bridge'ini
otomatik olarak kurup konfigüre eder.

Kullanım: python deploy_whatsapp_bridge.py
"""

import os
import paramiko
import time
import sys
import re
import textwrap
from pathlib import Path


def _load_env():
    """Proje kökündeki .env dosyasından ortam değişkenlerini yükler."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()

# ─── Configuration (.env dosyasından veya ortam değişkenlerinden okunur) ─────
def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"❌ HATA: '{key}' ortam değişkeni eksik. .env dosyasını kontrol edin.")
        sys.exit(1)
    return val

PI_HOST = _require_env("PI_HOST")
PI_USER = _require_env("PI_USER")
PI_PASS = _require_env("PI_PASS")
MATRIX_DIR = os.environ.get("MATRIX_DIR", "/opt/matrix-server")
POSTGRES_PASSWORD = _require_env("POSTGRES_PASSWORD")
SERVER_NAME = _require_env("SERVER_NAME")
# ─────────────────────────────────────────────────────────────────────────────


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


def step_1_check_current_state(client):
    """Mevcut durumu kontrol et"""
    print("\n" + "=" * 60)
    print("📋 ADIM 1: Mevcut Durum Kontrolü")
    print("=" * 60)

    out, _ = run_cmd(client, f"cd {MATRIX_DIR} && docker compose ps 2>&1")

    # Docker çalışıyor mu?
    if "prism-synapse" not in out and "synapse" not in out.lower():
        print("❌ Synapse container çalışmıyor! Önce başlatalım...")
        run_cmd(client, f"cd {MATRIX_DIR} && docker compose up -d db synapse tunnel 2>&1")
        time.sleep(10)

    # WhatsApp container durumunu kontrol et
    if "whatsapp" in out.lower():
        print("ℹ️  WhatsApp container mevcut, durdurup temizliyoruz...")
        run_cmd(client, f"cd {MATRIX_DIR} && docker compose stop whatsapp 2>&1")
        run_cmd(client, f"cd {MATRIX_DIR} && docker compose rm -f whatsapp 2>&1")

    return True


def step_2_create_database(client):
    """PostgreSQL'de whatsapp veritabanını oluştur"""
    print("\n" + "=" * 60)
    print("🗄️  ADIM 2: WhatsApp Veritabanı Oluşturma")
    print("=" * 60)

    # DB container çalışıyor mu?
    out, _ = run_cmd(client, "docker ps --filter name=prism-db --format '{{.Status}}'", print_output=False)
    if "Up" not in out:
        print("DB container bekleniyor...")
        run_cmd(client, f"cd {MATRIX_DIR} && docker compose up -d db 2>&1")
        time.sleep(10)

    # Veritabanı oluştur
    out, _ = run_cmd(client,
        "docker exec prism-db psql -U synapse -tc \"SELECT 1 FROM pg_database WHERE datname='whatsapp'\" 2>&1",
        print_output=False
    )

    if "1" in out:
        print("✅ 'whatsapp' veritabanı zaten mevcut.")
    else:
        print("📦 'whatsapp' veritabanı oluşturuluyor...")
        run_cmd(client, "docker exec prism-db psql -U synapse -c 'CREATE DATABASE whatsapp;' 2>&1")
        print("✅ Veritabanı oluşturuldu.")

    return True


def step_3_prepare_directories(client, password):
    """Dizinleri hazırla"""
    print("\n" + "=" * 60)
    print("📂 ADIM 3: Dizinleri Hazırlama")
    print("=" * 60)

    sudo_cmd(client, f"mkdir -p {MATRIX_DIR}/data/whatsapp", password)
    sudo_cmd(client, f"chown -R {PI_USER}:{PI_USER} {MATRIX_DIR}/data/whatsapp", password)
    sudo_cmd(client, f"chmod -R 755 {MATRIX_DIR}/data/whatsapp", password)
    print("✅ Dizinler hazırlandı.")
    return True


def step_4_generate_config(client, password):
    """WhatsApp bridge config.yaml'ı üret"""
    print("\n" + "=" * 60)
    print("⚙️  ADIM 4: WhatsApp config.yaml Üretme")
    print("=" * 60)

    # Mevcut config var mı?
    out, _ = run_cmd(client, f"ls -la {MATRIX_DIR}/data/whatsapp/config.yaml 2>&1", print_output=False)
    if "No such file" in out or "cannot access" in out.lower():
        print("📄 config.yaml üretiliyor (ilk kez)...")
        # docker-compose.yml'de whatsapp servisi tanımlı olmalı
        run_cmd(client, f"cd {MATRIX_DIR} && docker compose run --rm whatsapp 2>&1", timeout=120)
        time.sleep(5)

        # Tekrar kontrol
        out, _ = run_cmd(client, f"ls -la {MATRIX_DIR}/data/whatsapp/config.yaml 2>&1", print_output=False)
        if "No such file" in out:
            print("❌ config.yaml üretilemedi! Docker imajı problemi olabilir.")
            return False
    else:
        print("ℹ️  config.yaml zaten mevcut.")

    print("✅ config.yaml hazır.")
    return True


def step_5_configure_bridge(client, password):
    """config.yaml'ı düzenle - bridge ayarlarını yap"""
    print("\n" + "=" * 60)
    print("🔧 ADIM 5: Bridge Konfigürasyonu")
    print("=" * 60)

    sftp = client.open_sftp()
    config_path = f"{MATRIX_DIR}/data/whatsapp/config.yaml"

    try:
        with sftp.open(config_path, "r") as f:
            config = f.read().decode("utf-8")
    except Exception as e:
        print(f"❌ config.yaml okunamadı: {e}")
        sftp.close()
        return False

    original_config = config

    # ── Homeserver Ayarları ──
    # address: http://localhost:8008 → http://synapse:8008
    config = re.sub(
        r"(address:\s*)https?://localhost:8008",
        r"\1http://synapse:8008",
        config
    )

    # domain: localhost → matrix.fathertkt.uk
    config = re.sub(
        r"(domain:\s*)localhost",
        rf"\g<1>{SERVER_NAME}",
        config
    )

    # ── Database Ayarları (SQLite → PostgreSQL) ──
    pg_uri = f"postgres://synapse:{POSTGRES_PASSWORD}@db/whatsapp?sslmode=disable"

    # sqlite3-fk-wal tipini postgres yap  
    config = re.sub(r"type:\s*sqlite3[^\n]*", "type: postgres", config)

    # URI'yi postgres'e çevir
    config = re.sub(
        r"uri:\s*file:/data/mautrix-whatsapp\.db\?[^\n]+",
        f"uri: {pg_uri}",
        config
    )

    # Eğer sqlite3 olan bir uri kaldıysa onu da düzelt
    if "sqlite3" in config.lower() and "uri:" in config:
        # Daha agresif regex
        config = re.sub(r"uri:\s*file:[^\n]+", f"uri: {pg_uri}", config)

    # ── Permissions ──
    # admin: "@admin:example.com" → kendi admin kullanıcını ekle
    if f"@admin:{SERVER_NAME}" not in config:
        config = re.sub(
            r'(permissions:\s*\n(?:\s+[^\n]+\n)*)',
            rf'\g<0>        "@admin:{SERVER_NAME}": admin\n',
            config,
            count=1
        )

    # ── Encryption (opsiyonel ama iyi) ──
    # Allow encryption
    config = re.sub(
        r"(allow:\s*)false(\s*#.*encryption.*)?",
        r"\1true",
        config,
        count=1
    )

    # ── Logging ──
    # Detaylı log seviyesi
    config = re.sub(r"(min_level:\s*)warn", r"\g<1>debug", config, count=1)

    if config != original_config:
        print("📝 config.yaml güncelleniyor...")
        with sftp.open(config_path, "w") as f:
            f.write(config)
        print("✅ config.yaml güncellendi.")
    else:
        print("ℹ️  config.yaml zaten güncel.")

    sftp.close()
    return True


def step_6_generate_registration(client, password):
    """Registration dosyası üret"""
    print("\n" + "=" * 60)
    print("📋 ADIM 6: Registration Dosyası Üretme")
    print("=" * 60)

    # Registration üret
    print("🔑 registration.yaml üretiliyor...")
    out, err = run_cmd(client, f"cd {MATRIX_DIR} && docker compose run --rm whatsapp -g 2>&1", timeout=60)
    time.sleep(3)

    # Registration dosyası oluştu mu?
    out, _ = run_cmd(client,
        f"ls -la {MATRIX_DIR}/data/whatsapp/registration.yaml 2>&1",
        print_output=False
    )

    if "No such file" in out:
        print("❌ registration.yaml üretilemedi!")
        return False

    print("✅ registration.yaml oluşturuldu.")

    # Synapse'e kopyala
    print("📋 Registration dosyasını Synapse'e kopyalıyoruz...")
    sudo_cmd(client,
        f"cp {MATRIX_DIR}/data/whatsapp/registration.yaml {MATRIX_DIR}/data/synapse/appservice-whatsapp.yaml",
        password
    )
    sudo_cmd(client,
        f"chown {PI_USER}:{PI_USER} {MATRIX_DIR}/data/synapse/appservice-whatsapp.yaml",
        password
    )

    print("✅ Registration dosyası Synapse'e kopyalandı.")
    return True


def step_7_configure_synapse(client, password):
    """Synapse'e appservice kaydını ekle"""
    print("\n" + "=" * 60)
    print("🏠 ADIM 7: Synapse Konfigürasyonu (AppService)")
    print("=" * 60)

    sftp = client.open_sftp()
    hs_path = f"{MATRIX_DIR}/data/synapse/homeserver.yaml"

    try:
        with sftp.open(hs_path, "r") as f:
            hs_config = f.read().decode("utf-8")
    except Exception as e:
        print(f"❌ homeserver.yaml okunamadı: {e}")
        sftp.close()
        return False

    appservice_entry = "/data/appservice-whatsapp.yaml"

    if appservice_entry in hs_config:
        print("✅ Synapse zaten WhatsApp appservice'i tanıyor.")
    elif "app_service_config_files" in hs_config:
        print("📝 Mevcut app_service_config_files'a WhatsApp ekleniyor...")
        hs_config = re.sub(
            r"(app_service_config_files:\s*\n)",
            rf"\g<1>  - {appservice_entry}\n",
            hs_config
        )
        with sftp.open(hs_path, "w") as f:
            f.write(hs_config)
        print("✅ WhatsApp appservice eklendi.")
    else:
        print("📝 app_service_config_files bloğu ekleniyor...")
        hs_config += f"\n\napp_service_config_files:\n  - {appservice_entry}\n"
        with sftp.open(hs_path, "w") as f:
            f.write(hs_config)
        print("✅ AppService bloğu eklendi.")

    sftp.close()
    return True


def step_8_update_docker_compose(client, password):
    """docker-compose.yml'de whatsapp servisinin doğru ayarlandığından emin ol"""
    print("\n" + "=" * 60)
    print("🐳 ADIM 8: Docker Compose Kontrolü")
    print("=" * 60)

    sftp = client.open_sftp()
    compose_path = f"{MATRIX_DIR}/docker-compose.yml"

    try:
        with sftp.open(compose_path, "r") as f:
            compose = f.read().decode("utf-8")
    except Exception as e:
        print(f"❌ docker-compose.yml okunamadı: {e}")
        sftp.close()
        return False

    if "whatsapp" in compose:
        print("✅ WhatsApp servisi docker-compose.yml'de tanımlı.")
        
        # Network bağlantısı kontrolü - tüm servisler aynı default ağda olmalı
        # mautrix-whatsapp'ın synapse ve db'ye erişebilmesi lazım
        if "depends_on" in compose.split("whatsapp")[1].split("services:")[0] if "services:" in compose.split("whatsapp")[1] else compose.split("whatsapp")[1]:
            print("✅ WhatsApp depends_on ayarı mevcut.")
    else:
        print("❌ WhatsApp servisi docker-compose.yml'de yok! Ekleniyor...")
        whatsapp_service = textwrap.dedent("""
  whatsapp:
    image: dock.mau.dev/mautrix/whatsapp:latest
    container_name: prism-whatsapp
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./data/whatsapp:/data
""")
        compose = compose.rstrip() + "\n" + whatsapp_service
        with sftp.open(compose_path, "w") as f:
            f.write(compose)
        print("✅ WhatsApp servisi eklendi.")

    sftp.close()
    return True


def step_9_start_services(client, password):
    """Servisleri başlat"""
    print("\n" + "=" * 60)
    print("🚀 ADIM 9: Servisleri Başlatma")
    print("=" * 60)

    # Synapse restart (appservice config yüklenmesi için)
    print("🔄 Synapse yeniden başlatılıyor...")
    run_cmd(client, f"cd {MATRIX_DIR} && docker compose restart synapse 2>&1")
    time.sleep(10)

    # WhatsApp bridge başlat
    print("🚀 WhatsApp bridge başlatılıyor...")
    run_cmd(client, f"cd {MATRIX_DIR} && docker compose up -d whatsapp 2>&1")
    time.sleep(15)

    # Durumu kontrol et
    print("\n📊 Container Durumları:")
    run_cmd(client, f"cd {MATRIX_DIR} && docker compose ps 2>&1")

    return True


def step_10_check_logs_and_qr(client):
    """Log'ları kontrol et ve QR kodu göster"""
    print("\n" + "=" * 60)
    print("📱 ADIM 10: WhatsApp Bridge Log Kontrolü & QR Kod")
    print("=" * 60)

    time.sleep(5)
    out, _ = run_cmd(client, "docker logs prism-whatsapp --tail 100 2>&1")

    if "error" in out.lower() and "Starting" not in out:
        print("\n⚠️  Bridge log'larında hata var! Detaylar yukarıda.")
        return False

    print("\n" + "=" * 60)
    print("✅ KURULUM TAMAMLANDI!")
    print("=" * 60)
    print("""
📱 WhatsApp'ı bağlamak için:

1. PRISM uygulamasına giriş yapın (matrix.fathertkt.uk)
2. Yeni bir DM başlatın → @whatsappbot:matrix.fathertkt.uk
3. "login" yazın
4. QR kod gelecek → WhatsApp → Bağlı Cihazlar → QR Tara
5. Mesajlar otomatik senkronize olacak!

📊 Canlı log takibi için Pi'de:
   docker logs -f prism-whatsapp

🔄 Bridge'i yeniden başlatmak için:
   cd /opt/matrix-server && docker compose restart whatsapp
""")
    return True


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🟢 Matrix WhatsApp Bridge Otomatik Kurulum Scripti   ║")
    print("║   📍 Hedef: {}                       ║".format(PI_HOST))
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        client = ssh_connect(PI_HOST, PI_USER, PI_PASS)
    except Exception as e:
        print(f"\n❌ SSH bağlantısı kurulamadı: {e}")
        print("\n💡 Olası çözümler:")
        print("   1. Pi'nin açık ve ağa bağlı olduğundan emin olun")
        print("   2. Tailscale'in aktif olduğunu kontrol edin")
        print("   3. SSH servisinin çalıştığını kontrol edin: sudo systemctl status ssh")
        print("   4. IP adresini doğrulayın: tailscale ip -4")
        print("\n📋 Alternatif: Pi'ye doğrudan bağlanıp setup_whatsapp_local.sh çalıştırabilirsiniz")
        sys.exit(1)

    steps = [
        ("Mevcut Durum Kontrolü", lambda: step_1_check_current_state(client)),
        ("Veritabanı Oluşturma", lambda: step_2_create_database(client)),
        ("Dizin Hazırlığı", lambda: step_3_prepare_directories(client, PI_PASS)),
        ("Config Üretme", lambda: step_4_generate_config(client, PI_PASS)),
        ("Bridge Konfigürasyonu", lambda: step_5_configure_bridge(client, PI_PASS)),
        ("Registration Üretme", lambda: step_6_generate_registration(client, PI_PASS)),
        ("Synapse Konfigürasyonu", lambda: step_7_configure_synapse(client, PI_PASS)),
        ("Docker Compose Kontrolü", lambda: step_8_update_docker_compose(client, PI_PASS)),
        ("Servisleri Başlatma", lambda: step_9_start_services(client, PI_PASS)),
        ("Log Kontrolü & QR", lambda: step_10_check_logs_and_qr(client)),
    ]

    for name, step_func in steps:
        try:
            result = step_func()
            if not result:
                print(f"\n❌ '{name}' adımı başarısız oldu. Devam edilemiyor.")
                break
        except Exception as e:
            print(f"\n❌ '{name}' adımında hata: {e}")
            import traceback
            traceback.print_exc()
            break

    try:
        client.close()
    except:
        pass


if __name__ == "__main__":
    main()
