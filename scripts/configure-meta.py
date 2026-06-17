#!/usr/bin/env python3
"""mautrix-meta bridge config.yaml dosyasını düzenler."""

import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_DIR / "data" / "meta" / "config.yaml"
ENV_FILE = PROJECT_DIR / ".env"


def load_env():
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
    server_name = env.get("SERVER_NAME", "localhost")
    password = env.get("POSTGRES_PASSWORD")
    admin_user = env.get("ADMIN_USER", f"@admin:{server_name}")

    if not password:
        print("❌ HATA: POSTGRES_PASSWORD .env dosyasında tanımlı değil.")
        return 1

    if not CONFIG_FILE.exists():
        print(f"⚠️  {CONFIG_FILE} bulunamadı. Meta bridge atlanıyor.")
        return 0

    content = CONFIG_FILE.read_text(encoding="utf-8")

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

    # Database ayarları
    pg_uri = f"postgres://{env.get('POSTGRES_USER', 'synapse')}:{password}@db/meta?sslmode=disable"
    content = re.sub(r"type:\s*sqlite3[^\n]*", "type: postgres", content)
    content = re.sub(
        r"uri:\s*file:/data/mautrix-meta\.db\?[^\n]+",
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

    # Logging
    content = re.sub(r"min_level:\s*\S+", "min_level: warn", content)

    CONFIG_FILE.write_text(content, encoding="utf-8")
    print("✅ Meta bridge config.yaml güncellendi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
