#!/usr/bin/env python3
"""Synapse homeserver.yaml dosyasını PostgreSQL ve güvenlik ayarlarıyla günceller."""

import os
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_DIR / "data" / "synapse" / "homeserver.yaml"
ENV_FILE = PROJECT_DIR / ".env"


def load_env():
    """.env dosyasından değişkenleri okur."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def main():
    env = load_env()
    password = env.get("POSTGRES_PASSWORD")
    if not password:
        print("❌ HATA: POSTGRES_PASSWORD .env dosyasında tanımlı değil.")
        return 1

    if not CONFIG_FILE.exists():
        print(f"❌ HATA: {CONFIG_FILE} bulunamadı. Önce setup.sh çalıştırın.")
        return 1

    content = CONFIG_FILE.read_text(encoding="utf-8")

    # --- 1. SQLite -> PostgreSQL ---
    postgres_config = f"""database:
  name: psycopg2
  args:
    user: {env.get('POSTGRES_USER', 'synapse')}
    password: "{password}"
    host: db
    database: {env.get('POSTGRES_DB', 'synapse')}
    cp_min: 5
    cp_max: 10"""

    # SQLite bloğunu değiştir
    content = re.sub(
        r"database:\s*\n\s*name:\s*sqlite3\s*\n\s*args:\s*\n\s*database:\s*[^\n]+",
        postgres_config,
        content,
    )

    # Eğer hala sqlite geçiyorsa (alternatif format)
    if "name: sqlite3" in content:
        lines = content.split("\n")
        output = []
        skip = False
        for line in lines:
            if line.strip() == "database:" and len(lines) > lines.index(line) + 1 and "name: sqlite3" in lines[lines.index(line) + 1]:
                output.append(postgres_config)
                skip = True
                continue
            if skip:
                if line.startswith("  ") or line.strip() == "":
                    continue
                skip = False
            output.append(line)
        content = "\n".join(output)

    # --- 2. Kayıt ayarları ---
    enable_reg = env.get("ENABLE_REGISTRATION", "no").lower() == "yes"
    content = re.sub(r"enable_registration:\s*\S+", f"enable_registration: {str(enable_reg).lower()}", content)

    if enable_reg:
        if "enable_registration_without_verification:" in content:
            content = re.sub(
                r"enable_registration_without_verification:\s*\S+",
                "enable_registration_without_verification: true",
                content,
            )
        else:
            content = content.replace("database:", "enable_registration_without_verification: true\n\ndatabase:", 1)
    else:
        # Güvenlik için doğrulamasız kaydı kapat
        content = re.sub(
            r"enable_registration_without_verification:\s*true",
            "enable_registration_without_verification: false",
            content,
        )

    # --- 3. Listeners - tüm arayüzlere bağlan ---
    # Cloudflare Tunnel ve Docker iç network için gerekli
    content = re.sub(
        r"bind_addresses:\s*\n\s*-\s*127\.0\.0\.1",
        "bind_addresses:\n      - '::'\n      - 0.0.0.0",
        content,
    )

    # --- 4. Public baseurl ---
    server_name = env.get("SERVER_NAME", "localhost")
    public_baseurl = f"https://{server_name}"
    if "public_baseurl:" in content:
        content = re.sub(r"public_baseurl:\s*[^\n]+", f"public_baseurl: {public_baseurl}", content)
    else:
        content = content.replace("server_name:", f"public_baseurl: {public_baseurl}\nserver_name:", 1)

    # --- 5. Görünen isim ---
    display_name = env.get("SERVER_DISPLAY_NAME", "PRISM Messenger")
    if "server_name:" in content:
        # server_name değerini güncelle
        content = re.sub(r"^server_name:\s*[^\n]+", f"server_name: {server_name}", content, flags=re.MULTILINE)

    # --- 6. Report stats kapat ---
    content = re.sub(r"report_stats:\s*\S+", "report_stats: false", content)

    # --- 7. Admin contact ---
    admin_user = env.get("ADMIN_USER", f"@admin:{server_name}")
    if "admin_contact:" not in content:
        content += f"\n\n# Yönetici iletişim\nadmin_contact: 'mailto:admin@{server_name}'\n"

    # --- 8. Log rotation ---
    log_config = """
# Log rotation
log_config: "/data/matrix.log.config"
"""
    if "log_config:" not in content:
        content += log_config

    # --- 9. Anonim / Session room varsayılanları ---
    # Yeni odalar varsayılan olarak uçtan uca şifreli olsun
    session_defaults = """
# PRISM: Session room defaults (anonymous/private communication)
encryption_enabled_by_default_for_room_type: invite
# Oda listesini herkese açık yayınlamayı kısıtla
room_list_publication_rules:
  - action: deny
    user_id: "*"
"""
    if "encryption_enabled_by_default_for_room_type:" not in content:
        content += session_defaults

    CONFIG_FILE.write_text(content, encoding="utf-8")
    print("✅ Synapse homeserver.yaml PostgreSQL ve güvenlik ayarlarıyla güncellendi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
