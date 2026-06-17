#!/bin/bash
set -euo pipefail

# =============================================================================
# PRISM Backend Kurulum Scripti
# =============================================================================
# Bu script Synapse, PostgreSQL, bridge'ler, Monero node ve ek PRISM
# servisleri için gerekli konfigürasyon dosyalarını üretir.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# .env kontrolü
if [ ! -f .env ]; then
    log_error ".env dosyası bulunamadı! Lütfen .env.example dosyasını kopyalayıp doldurun:"
    echo "   cp .env.example .env"
    exit 1
fi

# .env'den değişkenleri yükle
export $(grep -v '^#' .env | xargs -d '\n')

REQUIRED_VARS=("SERVER_NAME" "POSTGRES_PASSWORD" "TUNNEL_TOKEN")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        log_error "$var değişkeni .env dosyasında boş veya tanımlı değil."
        exit 1
    fi
done

log_info "PRISM backend kurulumu başlatılıyor..."
log_info "Sunucu: $SERVER_NAME"

# ---------------------------------------------------------------------------
# 1. Veri dizinlerini oluştur
# ---------------------------------------------------------------------------
log_info "Veri dizinleri oluşturuluyor..."
mkdir -p data/{postgres,synapse,whatsapp,whatsapp-2,meta,monero,website/apk}

# Synapse log konfigürasyonunu kopyala
if [ -f config/matrix.log.config ]; then
    cp config/matrix.log.config data/synapse/matrix.log.config
    log_success "Dizinler ve log konfigürasyonu hazır."
else
    log_success "Dizinler hazır."
fi

# ---------------------------------------------------------------------------
# 2. Synapse konfigürasyonunu üret
# ---------------------------------------------------------------------------
if [ ! -f data/synapse/homeserver.yaml ]; then
    log_info "Synapse konfigürasyonu üretiliyor..."
    docker run --rm \
        -v "$(pwd)/data/synapse:/data" \
        -e SYNAPSE_SERVER_NAME="$SERVER_NAME" \
        -e SYNAPSE_REPORT_STATS="${REPORT_STATS:-no}" \
        matrixdotorg/synapse:latest generate
    log_success "Synapse konfigürasyonu oluşturuldu."
else
    log_warn "data/synapse/homeserver.yaml zaten mevcut, yeniden oluşturulmadı."
fi

# ---------------------------------------------------------------------------
# 3. PostgreSQL entegrasyonu
# ---------------------------------------------------------------------------
log_info "PostgreSQL entegrasyonu uygulanıyor..."
python3 "$SCRIPT_DIR/configure-synapse.py"

# ---------------------------------------------------------------------------
# 4. WhatsApp Bridge konfigürasyonları (çoklu destek)
# ---------------------------------------------------------------------------
configure_whatsapp_instance() {
    local instance="$1"
    local data_dir="data/$instance"
    local db_name="${instance//-/_}"

    if [ ! -f "$data_dir/config.yaml" ]; then
        log_info "$instance konfigürasyonu üretiliyor..."
        docker run --rm \
            -v "$(pwd)/$data_dir:/data" \
            dock.mau.dev/mautrix/whatsapp:latest \
            > /dev/null 2>&1 || true
        log_success "$instance konfigürasyonu oluşturuldu."
    else
        log_warn "$data_dir/config.yaml zaten mevcut, yeniden oluşturulmadı."
    fi

    log_info "$instance ayarları uygulanıyor..."
    python3 "$SCRIPT_DIR/configure-whatsapp.py" "$instance"

    # Registration dosyasını üret
    if [ ! -f "$data_dir/registration.yaml" ]; then
        log_info "$instance registration dosyası üretiliyor..."
        docker run --rm \
            -v "$(pwd)/$data_dir:/data" \
            dock.mau.dev/mautrix/whatsapp:latest \
            -g -c /data/config.yaml -r /data/registration.yaml \
            > /dev/null 2>&1 || true
        log_success "$instance registration dosyası oluşturuldu."
    else
        log_warn "$data_dir/registration.yaml zaten mevcut."
    fi

    # Synapse dizinine kopyala
    local app_name="appservice-${instance}.yaml"
    if [ -f "$data_dir/registration.yaml" ]; then
        cp "$data_dir/registration.yaml" "data/synapse/$app_name"
        log_success "$app_name Synapse dizinine kopyalandı."
    else
        log_warn "$data_dir/registration.yaml oluşturulamadı, $app_name atlanıyor."
    fi
}

configure_whatsapp_instance "whatsapp"
configure_whatsapp_instance "whatsapp-2"

# ---------------------------------------------------------------------------
# 5. Meta Bridge konfigürasyonu (opsiyonel, kapalı durumda)
# ---------------------------------------------------------------------------
if [ ! -f data/meta/config.yaml ]; then
    log_info "Meta bridge konfigürasyonu üretiliyor (varsayılan kapalı)..."
    docker run --rm \
        -v "$(pwd)/data/meta:/data" \
        dock.mau.dev/mautrix/meta:latest \
        > /dev/null 2>&1 || true
    log_success "Meta bridge konfigürasyonu oluşturuldu."
else
    log_warn "data/meta/config.yaml zaten mevcut, yeniden oluşturulmadı."
fi

log_info "Meta bridge ayarları uygulanıyor..."
python3 "$SCRIPT_DIR/configure-meta.py" || log_warn "Meta bridge ayarlanamadı (opsiyonel)."

if [ ! -f data/meta/registration.yaml ]; then
    log_info "Meta registration dosyası üretiliyor..."
    docker run --rm \
        -v "$(pwd)/data/meta:/data" \
        dock.mau.dev/mautrix/meta:latest \
        -g -c /data/config.yaml -r /data/registration.yaml \
        > /dev/null 2>&1 || true
    log_success "Meta registration dosyası oluşturuldu."
else
    log_warn "data/meta/registration.yaml zaten mevcut."
fi

if [ -f data/meta/registration.yaml ]; then
    cp data/meta/registration.yaml data/synapse/appservice-meta.yaml
    log_success "appservice-meta.yaml Synapse dizinine kopyalandı."
else
    log_warn "data/meta/registration.yaml oluşturulamadı, Meta bridge atlanıyor."
fi

# ---------------------------------------------------------------------------
# 6. Synapse homeserver.yaml'a AppService kayıtlarını ekle
# ---------------------------------------------------------------------------
log_info "Synapse AppService kayıtları kontrol ediliyor..."
python3 "$SCRIPT_DIR/add-appservices.py"

# ---------------------------------------------------------------------------
# 7. İzinleri düzenle
# ---------------------------------------------------------------------------
log_info "Dosya izinleri düzenleniyor..."
find data -type d -exec chmod 755 {} \;
find data -type f -exec chmod 644 {} \;
log_success "İzinler düzenlendi."

# ---------------------------------------------------------------------------
# 8. Monero dizini hazır
# ---------------------------------------------------------------------------
log_info "Monero veri dizini hazır: data/monero"

# ---------------------------------------------------------------------------
# 9. APK klasörü için placeholder
# ---------------------------------------------------------------------------
if [ ! -f data/website/apk/prism-latest.apk ]; then
    log_warn "data/website/apk/prism-latest.apk bulunamadı."
    log_info "Lütfen Android APK dosyasını şu dizine yükleyin:"
    echo "   $(pwd)/data/website/apk/prism-latest.apk"
fi

# ---------------------------------------------------------------------------
# 10. Tamamlandı
# ---------------------------------------------------------------------------
echo ""
log_success "PRISM backend kurulumu tamamlandı!"
echo ""
echo "Sıradaki adımlar:"
echo "   1. .env dosyasını kontrol edin."
echo "   2. Cloudflare Tunnel'da public hostname'leri ayarlayın:"
echo "      - $SERVER_NAME  -> http://synapse:8008"
echo "      - $DOMAIN       -> http://website:80"
echo "   3. Servisleri başlat:"
echo "      docker compose up -d"
echo "   4. İkinci WhatsApp bridge için (opsiyonel):"
echo "      docker compose --profile extra-whatsapp up -d"
echo "   5. Admin kullanıcı oluşturmak için:"
echo "      ./scripts/create-admin.sh"
echo ""
