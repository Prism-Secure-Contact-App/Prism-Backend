#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  🟢 Matrix WhatsApp Bridge - Tam Otomatik Kurulum (Yerel)
#  Bu scripti doğrudan Raspberry Pi 4 üzerinde çalıştırın.
#  
#  Kullanım: 
#    cd /opt/matrix-server
#    chmod +x setup_whatsapp_local.sh
#    ./setup_whatsapp_local.sh
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

MATRIX_DIR="/opt/matrix-server"

# Şifreyi .env dosyasından oku (hardcoded kullanma)
if [ -f "$MATRIX_DIR/.env" ]; then
    source "$MATRIX_DIR/.env"
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ HATA: POSTGRES_PASSWORD tanımlı değil. .env dosyasını kontrol edin."
    exit 1
fi

if [ -z "$SERVER_NAME" ]; then
    SERVER_NAME="matrix.fathertkt.uk"
fi

cd "$MATRIX_DIR"

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   🟢 Matrix WhatsApp Bridge Otomatik Kurulum            ║"
echo "║   📍 Sunucu: ${SERVER_NAME}                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── ADIM 1: Docker Durum Kontrolü ─────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 1: Docker Durum Kontrolü ═══${NC}"

if ! docker compose ps | grep -q "prism-synapse"; then
    echo -e "${YELLOW}⚠️  Synapse çalışmıyor, başlatılıyor...${NC}"
    docker compose up -d db synapse tunnel
    echo "⏳ Synapse'in hazır olması bekleniyor (30s)..."
    sleep 30
else
    echo -e "${GREEN}✅ Synapse çalışıyor.${NC}"
fi

# Whatsapp container varsa durdur
if docker compose ps | grep -q "whatsapp"; then
    echo -e "${YELLOW}ℹ️  Mevcut WhatsApp container durduruluyor...${NC}"
    docker compose stop whatsapp 2>/dev/null || true
    docker compose rm -f whatsapp 2>/dev/null || true
fi

# ─── ADIM 2: Veritabanı ────────────────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 2: WhatsApp Veritabanı ═══${NC}"

DB_EXISTS=$(docker exec prism-db psql -U synapse -tc "SELECT 1 FROM pg_database WHERE datname='whatsapp'" 2>/dev/null | tr -d ' ')

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${GREEN}✅ 'whatsapp' veritabanı zaten mevcut.${NC}"
else
    echo -e "${YELLOW}📦 'whatsapp' veritabanı oluşturuluyor...${NC}"
    docker exec prism-db psql -U synapse -c "CREATE DATABASE whatsapp;" 2>/dev/null || true
    echo -e "${GREEN}✅ Veritabanı oluşturuldu.${NC}"
fi

# ─── ADIM 3: Dizin Hazırlığı ───────────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 3: Dizin Hazırlığı ═══${NC}"

mkdir -p data/whatsapp
chmod -R 755 data/whatsapp
echo -e "${GREEN}✅ Dizinler hazır.${NC}"

# ─── ADIM 4: Config Üretme ─────────────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 4: config.yaml Üretme ═══${NC}"

if [ ! -f "data/whatsapp/config.yaml" ]; then
    echo -e "${YELLOW}📄 config.yaml üretiliyor (ilk kez)...${NC}"
    docker compose run --rm whatsapp 2>&1 || true
    sleep 3
    
    if [ ! -f "data/whatsapp/config.yaml" ]; then
        echo -e "${RED}❌ config.yaml üretilemedi!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}ℹ️  config.yaml zaten mevcut.${NC}"
fi

# ─── ADIM 5: Bridge Konfigürasyonu ─────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 5: Bridge Konfigürasyonu ═══${NC}"

CONFIG_FILE="data/whatsapp/config.yaml"
PG_URI="postgres://synapse:${POSTGRES_PASSWORD}@db/whatsapp?sslmode=disable"

# Homeserver adresi
sed -i "s|address: https\?://localhost:8008|address: http://synapse:8008|g" "$CONFIG_FILE"

# Domain
sed -i "s|domain: localhost|domain: ${SERVER_NAME}|g" "$CONFIG_FILE"

# Database tipi
sed -i "s|type: sqlite3.*|type: postgres|g" "$CONFIG_FILE"

# Database URI
sed -i "s|uri: file:/data/mautrix-whatsapp.db.*|uri: ${PG_URI}|g" "$CONFIG_FILE"

# Permissions - Admin kullanıcısı ekle
if ! grep -q "@admin:${SERVER_NAME}" "$CONFIG_FILE" 2>/dev/null; then
    # Tüm kullanıcılara user izni ver, admin'e admin izni ver
    sed -i "s|\"\\*\": relay|\"*\": relay\n        \"${SERVER_NAME}\": user\n        \"@admin:${SERVER_NAME}\": admin|g" "$CONFIG_FILE" 2>/dev/null || true
fi

echo -e "${GREEN}✅ config.yaml güncellendi.${NC}"
echo -e "${CYAN}   → Homeserver: http://synapse:8008${NC}"
echo -e "${CYAN}   → Domain: ${SERVER_NAME}${NC}"
echo -e "${CYAN}   → Database: PostgreSQL${NC}"

# ─── ADIM 6: Registration Dosyası ──────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 6: Registration Dosyası ═══${NC}"

echo -e "${YELLOW}🔑 registration.yaml üretiliyor...${NC}"
docker compose run --rm whatsapp -g 2>&1 || true
sleep 3

if [ ! -f "data/whatsapp/registration.yaml" ]; then
    echo -e "${RED}❌ registration.yaml üretilemedi!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ registration.yaml oluşturuldu.${NC}"

# Synapse'e kopyala
cp data/whatsapp/registration.yaml data/synapse/appservice-whatsapp.yaml
chmod 644 data/synapse/appservice-whatsapp.yaml
echo -e "${GREEN}✅ Registration dosyası Synapse'e kopyalandı.${NC}"

# ─── ADIM 7: Synapse Konfigürasyonu ────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 7: Synapse Konfigürasyonu ═══${NC}"

HS_CONFIG="data/synapse/homeserver.yaml"
APPSERVICE_ENTRY="/data/appservice-whatsapp.yaml"

if grep -q "$APPSERVICE_ENTRY" "$HS_CONFIG" 2>/dev/null; then
    echo -e "${GREEN}✅ Synapse zaten WhatsApp appservice'i tanıyor.${NC}"
elif grep -q "app_service_config_files" "$HS_CONFIG" 2>/dev/null; then
    echo -e "${YELLOW}📝 Mevcut app_service_config_files'a WhatsApp ekleniyor...${NC}"
    sed -i "/app_service_config_files:/a\\  - ${APPSERVICE_ENTRY}" "$HS_CONFIG"
    echo -e "${GREEN}✅ WhatsApp appservice eklendi.${NC}"
else
    echo -e "${YELLOW}📝 app_service_config_files bloğu oluşturuluyor...${NC}"
    echo -e "\n\napp_service_config_files:\n  - ${APPSERVICE_ENTRY}" >> "$HS_CONFIG"
    echo -e "${GREEN}✅ AppService bloğu eklendi.${NC}"
fi

# ─── ADIM 8: Servisleri Başlatma ───────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 8: Servisleri Başlatma ═══${NC}"

echo -e "${YELLOW}🔄 Synapse yeniden başlatılıyor (appservice yüklenmesi için)...${NC}"
docker compose restart synapse
echo "⏳ Synapse'in hazır olması bekleniyor (15s)..."
sleep 15

echo -e "${YELLOW}🚀 WhatsApp bridge başlatılıyor...${NC}"
docker compose up -d whatsapp
echo "⏳ Bridge'in başlaması bekleniyor (10s)..."
sleep 10

# ─── ADIM 9: Durum Kontrolü ────────────────────────────────────
echo -e "\n${BOLD}${BLUE}═══ ADIM 9: Durum Kontrolü ═══${NC}"

echo -e "${CYAN}📊 Container Durumları:${NC}"
docker compose ps

echo -e "\n${CYAN}📋 WhatsApp Bridge Son Loglar:${NC}"
docker logs prism-whatsapp --tail 30 2>&1

# ─── SONUÇ ──────────────────────────────────────────────────────
echo -e "\n${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅ KURULUM TAMAMLANDI!                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  📱 WhatsApp'ı bağlamak için:                            ║"
echo "║                                                          ║"
echo "║  1. PRISM uygulamasına giriş yapın                       ║"
echo "║     → matrix.fathertkt.uk                                ║"
echo "║                                                          ║"
echo "║  2. Yeni DM başlatın:                                    ║"
echo "║     → @whatsappbot:matrix.fathertkt.uk                   ║"
echo "║                                                          ║"
echo "║  3. Bota 'login' yazın                                   ║"
echo "║                                                          ║"
echo "║  4. QR kod gelecek → WhatsApp → Bağlı Cihazlar → Tara   ║"
echo "║                                                          ║"
echo "║  5. Mesajlar otomatik senkronize olacak! 🎉              ║"
echo "║                                                          ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  📊 Canlı log: docker logs -f prism-whatsapp            ║"
echo "║  🔄 Restart:   docker compose restart whatsapp           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
