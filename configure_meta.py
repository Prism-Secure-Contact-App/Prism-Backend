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
        password = "1234" # Fallback

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    print("⚙️  Meta config.yaml sıfırdan oluşturuluyor (V4 Uyumluluk)...")
    
    domain = "matrix.fathertkt.uk"
    postgres_url = f"postgres://synapse:{password}@db/mautrix_meta?sslmode=disable"
    
    # Minimal and complete V4 configuration for Meta bridge
    config_content = f"""homeserver:
    address: http://synapse:8008
    domain: {domain}
    software: standard
appservice:
    address: http://meta:29319
    hostname: 0.0.0.0
    port: 29319
    database:
        type: postgres
        uri: {postgres_url}
    id: meta
    bot:
        username: pmb-bot
        displayname: Instagram Bridge Bot
        avatar: mxc://maunium.net/NeXNQarUbrlQBiwhd5226463
    as_token: ''
    hs_token: ''
bridge:
    username_template: meta_{{}}
    displayname_template: '{{displayname}} (IG)'
    personal_filtering_spaces: false
    delivery_receipts: false
    message_status_events: false
    message_error_notices: false
    rest_api: false
    encryption:
        allow: true
        default: true
        require: false
        appservice: false
        client: false
    permissions:
        "*": admin
"""
    with open(CONFIG_FILE, "w") as f:
        f.write(config_content)
    print("✅ config.yaml oluşturuldu.")

    # 1.1. Registration Dosyasına Encryption Desteği Ekleme & Sender Localpart Fix
    REG_FILE = "./data/meta/registration.yaml"
    if os.path.exists(REG_FILE):
        with open(REG_FILE, "r") as f:
            reg_content = f.read()
        
        # encryption: true ekle
        if "encryption: true" not in reg_content:
            print("🔐 Registration dosyasına encryption desteği ekleniyor...")
            reg_content += "\\nencryption: true\\n"
        
        # sender_localpart MUST match bot.username and be inside the user namespace below.
        reg_content = re.sub(
            r"sender_localpart:\\s*[a-zA-Z0-9_-]+",
            "sender_localpart: pmb-bot",
            reg_content
        )
        
        # as_token, hs_token gibi önemli kısımları koru, namespaces kısmını baştan yaz
        pattern = r"(    users:.*?\\n)(de\\.sorunome|receive_ephemeral|encryption)"
        
        replacement = f"""    users:
        - regex: ^@pmb-bot:{domain}$
          exclusive: true
        - regex: ^@meta_.*:{domain}$
          exclusive: true
\\\\2"""
        
        if "    users:" in reg_content:
            reg_content = re.sub(pattern, replacement, reg_content, flags=re.DOTALL)
        else:
            reg_content = re.sub(
                r"namespaces:\\n",
                "namespaces:\\n" + replacement.replace("\\\\2", "de.sorunome"),
                reg_content
            )

        with open(REG_FILE, "w") as f:
            f.write(reg_content)
        
        # Kopya dosyaya da aktar
        SYNAPSE_REG = "./data/synapse/appservice-meta.yaml"
        with open(SYNAPSE_REG, "w") as f:
            f.write(reg_content)
        print("✅ registration.yaml güncellendi (encryption + sender_localpart)")

    # 2. Synapse homeserver.yaml'a AppService Eklemek
    if os.path.exists(SYNAPSE_CONFIG):
        with open(SYNAPSE_CONFIG, "r") as f:
            content = f.read()

        if "/data/appservice-meta.yaml" not in content:
            print("⚙️  Synapse'e Meta Registration Ekleniyor...")
            if "app_service_config_files:" in content:
                 content = re.sub(
                    r"app_service_config_files:\\s*\\n",
                    "app_service_config_files:\\n  - /data/appservice-meta.yaml\\n",
                    content
                )
            else:
                 content += "\\n\\napp_service_config_files:\\n  - /data/appservice-meta.yaml\\n"
            
            with open(SYNAPSE_CONFIG, "w") as f:
                f.write(content)
            print("✅ homeserver.yaml AppService ayarı eklendi.")

if __name__ == "__main__":
    main()
