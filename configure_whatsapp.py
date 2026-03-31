import os
import re
import sys

CONFIG_FILE = "./data/whatsapp/config.yaml"
SYNAPSE_CONFIG = "./data/synapse/homeserver.yaml"
DOTENV_FILE = ".env"

def get_env_var(var_name):
    if not os.path.exists(DOTENV_FILE):
        return None
    with open(DOTENV_FILE, "r") as f:
        content = f.read()
        match = re.search(fr"{var_name}=(.*)", content)
        if match:
            return match.group(1).strip()
    return None

def main():
    password = get_env_var("POSTGRES_PASSWORD")
    if not password:
        print("❌ HATA: .env dosyasında POSTGRES_PASSWORD bulunamadı!")
        sys.exit(1)

    # 1. WhatsApp config.yaml Düzenleme
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            content = f.read()

        print("⚙️  WhatsApp config.yaml ayarlanıyor...")
        
        # Homeserver Adresi
        content = re.sub(
            r"address:\s*http://localhost:8008",
            "address: http://synapse:8008",
            content
        )
        
        # Domain name
        server_name = get_env_var("SERVER_NAME")
        if server_name:
            content = re.sub(
                r"domain:\s*localhost",
                f"domain: {server_name}",
                content
            )

        # Database Postgres Yapma
        postgres_url = f"postgres://synapse:{password}@db/whatsapp?sslmode=disable"
        content = re.sub(
            r"type:\s*sqlite3-nk\n\s*uri:\s*file:/data/mautrix-whatsapp.db\?_auth_founder=1",
            f"type: postgres\n\turi: {postgres_url}",
            content
        )
        # Bazen farklı bir sqlite şablonu olabilir
        content = re.sub(
            r"uri:\s*file:/data/mautrix-whatsapp.db\?[^\n]+",
            f"uri: {postgres_url}",
            content
        )
        content = re.sub(
            r"type:\s*sqlite3[^\n]*",
            "type: postgres",
            content
        )

        with open(CONFIG_FILE, "w") as f:
            f.write(content)
        print("✅ config.yaml güncellendi.")

    # 2. Synapse homeserver.yaml'a AppService Eklemek
    if os.path.exists(SYNAPSE_CONFIG):
        with open(SYNAPSE_CONFIG, "r") as f:
            content = f.read()

        if "app_service_config_files" not in content:
            print("⚙️  Synapse'e WhatsApp Registration Ekleniyor...")
            app_service_block = """app_service_config_files:
  - /data/registration.yaml"""
            
            # En güvenlisi en sonuna eklemek (Top-level)
            content += f"\n\n{app_service_block}\n"
            with open(SYNAPSE_CONFIG, "w") as f:
                f.write(content)
            print("✅ homeserver.yaml AppService ayarı eklendi.")
        else:
            if "/data/registration.yaml" not in content:
                print("⚙️  Mevcut app_service_config_files altına WhatsApp ekleniyor...")
                content = re.sub(
                    r"app_service_config_files:\s*\n",
                    "app_service_config_files:\n  - /data/registration.yaml\n",
                    content
                )
                with open(SYNAPSE_CONFIG, "w") as f:
                    f.write(content)

if __name__ == "__main__":
    main()
