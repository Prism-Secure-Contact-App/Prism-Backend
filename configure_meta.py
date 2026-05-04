import os
import re
import sys

CONFIG_FILE = "./data/meta/config.yaml"
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

    # 1. Meta config.yaml Düzenleme
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            content = f.read()

        print("⚙️  Meta (Instagram) config.yaml ayarlanıyor...")
        
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
                r"domain:\s*[a-zA-Z0-9.-]+",
                f"domain: {server_name}",
                content
            )

        # Database Postgres Yapma
        postgres_url = f"postgres://synapse:{password}@db/meta?sslmode=disable"
        content = re.sub(
            r"type:\s*sqlite3[^\n]*",
            "type: postgres",
            content
        )
        content = re.sub(
            r"uri:\s*file:/data/mautrix-meta.db\?[^\n]+",
            f"uri: {postgres_url}",
            content
        )

        # Homeserver Adresi
        content = re.sub(
            r"address:\s*http://[a-zA-Z0-9_-]+:8008",
            "address: http://synapse:8008",
            content
        )
        
        # Appservice Address (How Synapse reaches the bridge)
        content = re.sub(
            r"address:\s*http://[a-zA-Z0-9_-]+:29319",
            "address: http://meta:29319",
            content
        )

        # Sender Localpart — MUST match bot.username and be covered by user namespace regex.
        # Why: Synapse rejects AS transactions whose sender MXID isn't in the declared namespace
        # (M_EXCLUSIVE). Previously set to "meta-as" which wasn't in namespace → bridge silent.
        content = re.sub(
            r"sender_localpart:\s*[a-zA-Z0-9_-]+",
            "sender_localpart: pmb-bot",
            content,
            count=1
        )
        
        # Bot Username (Changed to avoid appservice sync restriction and reservation issues)
        content = re.sub(
            r"username:\s*[a-zA-Z0-9_-]+bot",
            "username: pmb-bot",
            content
        )

        # Bridge Autojoin & Auto-leave
        content = re.sub(r"autojoin:\s*false", "autojoin: true", content)
        content = re.sub(r"auto_join_on_invite:\s*false", "auto_join_on_invite: true", content)

        # Encryption Support - Aggressive Update
        print("🔐 Encryption (E2EE) aktif ediliyor...")
        content = re.sub(r"allow:\s*false", "allow: true", content)
        content = re.sub(r"default:\s*false", "default: true", content)
        # 3. Encryption bloğunu tamamen zorla (appservice: true dahil)
        if "encryption:" in content:
            if "appservice:" in content:
                content = re.sub(r"appservice:\s*true", "appservice: false", content)
            else:
                content = re.sub(r"(encryption:.*?\n)", r"\1    appservice: false\n", content)
            
            content = re.sub(r"allow:\s*false", "allow: true", content)
            content = re.sub(r"default:\s*false", "default: true", content)

        # Namespaces Fix
        if server_name:
            content = re.sub(
                r"regex:\s*'?@([a-zA-Z0-9_-]+):[a-zA-Z0-9.-]+'?",
                fr"regex: '@\1:{server_name}'",
                content
            )

        with open(CONFIG_FILE, "w") as f:
            f.write(content)
        print("✅ config.yaml güncellendi.")

    # 1.1. Registration Dosyasına Encryption Desteği Ekleme & Sender Localpart Fix
    REG_FILE = "./data/meta/registration.yaml"
    if os.path.exists(REG_FILE):
        with open(REG_FILE, "r") as f:
            reg_content = f.read()
        
        # encryption: true ekle
        if "encryption: true" not in reg_content:
            print("🔐 Registration dosyasına encryption desteği ekleniyor...")
            reg_content += "\nencryption: true\n"
        
        # sender_localpart MUST match bot.username and be inside the user namespace below.
        reg_content = re.sub(
            r"sender_localpart:\s*[a-zA-Z0-9_-]+",
            "sender_localpart: pmb-bot",
            reg_content
        )
        
        # namespaces bloğunu tamamen temizle ve yeniden oluştur
        
        # as_token, hs_token gibi önemli kısımları koru, namespaces kısmını baştan yaz
        pattern = r"(    users:.*?\n)(de\.sorunome|receive_ephemeral|encryption)"
        replacement = """    users:
        - regex: ^@pmb-bot:matrix\.fathertkt\.uk$
          exclusive: true
        - regex: ^@meta_.*:matrix\.fathertkt\.uk$
          exclusive: true
\\2"""
        
        if "    users:" in reg_content:
            reg_content = re.sub(pattern, replacement, reg_content, flags=re.DOTALL)
        else:
            reg_content = re.sub(
                r"namespaces:\n",
                "namespaces:\n" + replacement.replace("\\2", "de.sorunome"),
                reg_content
            )

        with open(REG_FILE, "w") as f:
            f.write(reg_content)
        
        # Kopya dosyaya da aktar
        SYNAPSE_REG = "./data/synapse/appservice-instagram.yaml"
        with open(SYNAPSE_REG, "w") as f:
            f.write(reg_content)
        print("✅ registration.yaml güncellendi (encryption + sender_localpart)")

    # 2. Synapse homeserver.yaml'a AppService Eklemek
    if os.path.exists(SYNAPSE_CONFIG):
        with open(SYNAPSE_CONFIG, "r") as f:
            content = f.read()

        if "/data/appservice-instagram.yaml" not in content:
            print("⚙️  Synapse'e Meta Registration Ekleniyor...")
            if "app_service_config_files:" in content:
                content = re.sub(
                    r"app_service_config_files:\s*\n",
                    "app_service_config_files:\n  - /data/appservice-instagram.yaml\n",
                    content
                )
            else:
                content += "\n\napp_service_config_files:\n  - /data/appservice-instagram.yaml\n"
            
            with open(SYNAPSE_CONFIG, "w") as f:
                f.write(content)
            print("✅ homeserver.yaml AppService ayarı eklendi.")

if __name__ == "__main__":
    main()
