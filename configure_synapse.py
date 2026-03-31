import os
import re

CONFIG_FILE = "./data/synapse/homeserver.yaml"
DOTENV_FILE = ".env"

def get_env_var(var_name):
    if not os.path.exists(DOTENV_FILE):
        print(f"❌ HATA: {DOTENV_FILE} dosyası bulunamadı!")
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
        return

    if not os.path.exists(CONFIG_FILE):
        print(f"❌ HATA: {CONFIG_FILE} dosyası bulunamadı! Önce generate-config çalıştırmalısınız.")
        return

    with open(CONFIG_FILE, "r") as f:
        content = f.read()

    # SQLite ayarlarını PostgreSQL ile değiştirme
    postgres_config = f"""database:
  name: psycopg2
  args:
    user: synapse
    password: "{password}"
    host: db
    database: synapse
    cp_min: 5
    cp_max: 10"""

    # database: bloğunu bul ve değiştir
    # Varsayılan SQLite bloğu genellikle şöyledir:
    # database:
    #   name: sqlite3
    #   args:
    #     database: /data/homeserver.db
    
    new_content = re.sub(
        r"database:\s*\n\s*name:\s*sqlite3\s*\n\s*args:\s*\n\s*database:\s*[^\n]+",
        postgres_config,
        content
    )

    if new_content == content:
        print("⚠️ Bilgi: SQLite bloğu regex ile bulunamadı. Alternatif bir arama yapılıyor...")
        # Alternatif: Sadece name: sqlite3 kısmını ve altındaki args'ı değiştirmeyi deneriz.
        # Ama en garantisi dosyaya append etmek veya yedekli gitmek.
        # Daha basit bir string replace deneyelim:
        if "name: sqlite3" in content:
            # name: sqlite3 bloğunu kesip yerine postgres ekleme
            lines = content.split("\n")
            output = []
            skip = False
            found = False
            for line in lines:
                if line.strip() == "database:" and "name: sqlite3" in lines[lines.index(line)+1]:
                    output.append(postgres_config)
                    skip = True
                    found = True
                    continue
                if skip:
                    if line.startswith("  ") or line.strip() == "":
                        # args altındaki girintili satırları atla
                        continue
                    else:
                        skip = False
                if not skip:
                    output.append(line)
            new_content = "\n".join(output)

    # Halka Açık Kayıt (Registration) Ayarı
    enable_reg = get_env_var("ENABLE_REGISTRATION")
    if enable_reg and enable_reg.lower() == "yes":
        print("🔓 Halka açık kayıt ve doğrulamasız kayıt aktif ediliyor...")
        # enable_registration: true yap
        new_content = re.sub(
            r"enable_registration:\s*false",
            "enable_registration: true",
            new_content
        )
        
        # enable_registration_without_verification ayarını ekle veya güncelle
        if "enable_registration_without_verification:" in new_content:
            new_content = re.sub(
                r"enable_registration_without_verification:\s*false",
                "enable_registration_without_verification: true",
                new_content
            )
        else:
            # Bulunamazsa database: bloğunun hemen üzerine ekleyebiliriz
            if "database:" in new_content:
                new_content = new_content.replace(
                    "database:",
                    "enable_registration_without_verification: true\n\ndatabase:"
                )

    with open(CONFIG_FILE, "w") as f:
        f.write(new_content)

    print("✅ database/homeserver.yaml dosyası PostgreSQL için başarıyla güncellendi.")

if __name__ == "__main__":
    main()
