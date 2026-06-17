#!/usr/bin/env python3
"""Synapse homeserver.yaml'a mevcut AppService kayıtlarını ekler.

data/synapse/ altındaki appservice-*.yaml dosyalarını otomatik bulur ve
homeserver.yaml'daki app_service_config_files listesine /data/... yollarıyla
ekler.
"""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SYNAPSE_CONFIG = PROJECT_DIR / "data" / "synapse" / "homeserver.yaml"
APPSERVICE_DIR = PROJECT_DIR / "data" / "synapse"


def discover_appservices():
    """data/synapse altındaki appservice-*.yaml dosyalarını bulur."""
    services = []
    for path in sorted(APPSERVICE_DIR.glob("appservice-*.yaml")):
        services.append(f"/data/{path.name}")
    return services


def main():
    if not SYNAPSE_CONFIG.exists():
        print(f"❌ HATA: {SYNAPSE_CONFIG} bulunamadı.")
        return 1

    appservices = discover_appservices()
    if not appservices:
        print("⚠️  Uyarı: Hiç appservice-*.yaml dosyası bulunamadı.")
        return 0

    print(f"ℹ️  Bulunan AppService dosyaları: {appservices}")

    content = SYNAPSE_CONFIG.read_text(encoding="utf-8")

    if "app_service_config_files:" in content:
        # Mevcut listeyi bul
        match_start = content.find("app_service_config_files:")
        block_start = content.find("\n", match_start) + 1
        block_end = block_start
        while block_end < len(content) and (
            content[block_end:block_end+4].strip().startswith("-") or
            content[block_end].strip() == ""
        ):
            block_end += 1
        block = content[block_start:block_end]
        existing_files = []
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("-"):
                existing_files.append(line[1:].strip())

        # Eksik olanları ekle
        for svc in appservices:
            if svc not in existing_files:
                content = content.replace(
                    "app_service_config_files:",
                    f"app_service_config_files:\n  - {svc}",
                    1,
                )
                print(f"✅ AppService eklendi: {svc}")
            else:
                print(f"ℹ️  AppService zaten mevcut: {svc}")
    else:
        # Yeni blok ekle
        block = "\n\napp_service_config_files:\n" + "\n".join(f"  - {svc}" for svc in appservices)
        content += block + "\n"
        print("✅ AppService bloğu eklendi.")

    SYNAPSE_CONFIG.write_text(content, encoding="utf-8")
    print("✅ Synapse AppService kayıtları güncellendi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
