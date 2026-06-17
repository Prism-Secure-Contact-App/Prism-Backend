#!/usr/bin/env python3
"""mautrix-whatsapp bridge config.yaml dosyasını düzenler.

Kullanım:
    python3 configure-whatsapp.py [INSTANCE]

INSTANCE varsayılan olarak 'whatsapp'tır. 'whatsapp-2' gibi ek instance'lar için
kullanılabilir.
"""

import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def configure_instance(instance: str):
    env = load_env()
    server_name = env.get("SERVER_NAME", "localhost")
    password = env.get("POSTGRES_PASSWORD")
    admin_user = env.get("ADMIN_USER", f"@admin:{server_name}")

    if not password:
        print("❌ HATA: POSTGRES_PASSWORD .env dosyasında tanımlı değil.")
        return 1

    config_file = PROJECT_DIR / "data" / instance / "config.yaml"
    if not config_file.exists():
        print(f"⚠️  {config_file} bulunamadı, atlanıyor.")
        return 0

    content = config_file.read_text(encoding="utf-8")

    # Veritabanı adı instance'a göre (whatsapp veya whatsapp_2)
    db_name = instance.replace("-", "_")
    pg_uri = f"postgres://{env.get('POSTGRES_USER', 'synapse')}:{password}@db/{db_name}?sslmode=disable"

    # Bridge bot kullanıcı adını instance'a göre ayarla
    bot_suffix = "-2" if instance.endswith("-2") else ""
    bridge_username = f"whatsapp{bot_suffix}bot"

    # Homeserver ayarları
    content = re.sub(
        r"address:\s*https?://[^\n]+",
        "address: http://synapse:8008",
        content,
    )
    content = re.sub(
        r"domain:\s*[^\n]+",
        f"domain: {server_name}",
        content,
        count=1,
    )

    # Bridge bot username
    content = re.sub(
        r"username_template:\s*[^\n]+",
        f"username_template: {bridge_username}_{{{{.}}}}",
        content,
    )
    content = re.sub(
        r"username:\s*whatsappbot",
        f"username: {bridge_username}",
        content,
    )

    # Database ayarları
    content = re.sub(r"type:\s*sqlite3[^\n]*", "type: postgres", content)
    content = re.sub(
        r"uri:\s*file:/data/mautrix-whatsapp\.db\?[^\n]+",
        f"uri: {pg_uri}",
        content,
    )
    content = re.sub(
        r"uri:\s*file:[^\n]+",
        f"uri: {pg_uri}",
        content,
    )

    # Permissions
    admin_entry = f'    "{admin_user}": admin'
    if "permissions:" in content:
        if admin_user not in content:
            content = re.sub(
                r"(permissions:\s*\n)",
                rf"\g<1>{admin_entry}\n",
                content,
            )
    else:
        content += f"\npermissions:\n{admin_entry}\n"

    # Encryption
    content = re.sub(
        r"allow:\s*false(\s*#.*encryption)?",
        "allow: true",
        content,
        count=1,
    )

    # Logging
    content = re.sub(r"min_level:\s*\S+", "min_level: warn", content)

    # Displayname template (çoklu bridge ayırt etmek için)
    content = re.sub(
        r"displayname_template:\s*[^\n]+",
        f"displayname_template: '{{{{.DisplayName}}}} (WA{bot_suffix})'",
        content,
    )

    config_file.write_text(content, encoding="utf-8")
    print(f"✅ WhatsApp bridge ({instance}) config.yaml güncellendi.")
    return 0


def main():
    instance = sys.argv[1] if len(sys.argv) > 1 else "whatsapp"
    return configure_instance(instance)


if __name__ == "__main__":
    raise SystemExit(main())
