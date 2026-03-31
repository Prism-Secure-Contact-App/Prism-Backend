#!/bin/bash

# PRISM Server Setup Script
# Bu script Synapse ve Köprülerin konfigürasyonunu otomatikleştirir.

DOMAIN="matrix.fathertkt.uk"
SERVER_NAME="PRISM Messenger"

mkdir -p ./data/synapse ./data/whatsapp ./data/meta ./data/postgres

echo "1. Synapse Konfigürasyonu Üretiliyor..."
docker run --rm \
    -v $(pwd)/data/synapse:/data \
    -e SYNAPSE_SERVER_NAME=$DOMAIN \
    -e SYNAPSE_REPORT_STATS=no \
    matrixdotorg/synapse:latest generate

echo "2. PRISM Branding Uygulanıyor..."
# Homeserver.yaml guncelleme (Örn: isim değiştirme)
sed -i "s/Synapse/$SERVER_NAME/g" ./data/synapse/homeserver.yaml

# 3. WhatsApp Bridge Konfigürasyonu...
docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
    -v $(pwd)/data/whatsapp:/data \
    dock.mau.dev/mautrix/whatsapp:latest \
    -c /data/config.yaml # Sadece config uretimi icin

# Bridge konfigürasyonlarını otomatikleştir
sed -i "s/address: http:\/\/localhost:8008/address: http:\/\/synapse:8008/g" ./data/whatsapp/config.yaml
sed -i "s/domain: localhost/domain: $DOMAIN/g" ./data/whatsapp/config.yaml

echo "4. Instagram (Meta) Bridge Konfigürasyonu..."
docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
    -v $(pwd)/data/meta:/data \
    dock.mau.dev/mautrix/meta:latest \
    -c /data/config.yaml # Sadece config uretimi icin

echo "5. Registration Dosyaları Üretiliyor..."
chmod +x ./generate-registrations.sh
./generate-registrations.sh

echo ""
echo "PRISM Sunucusu Başarıyla Yapılandırıldı!"
echo "--------------------------------------"
echo "1. data/synapse/homeserver.yaml dosyasını açın."
echo "2. 'app_service_config_files' kısmına şunları ekleyin:"
echo "   - /data/appservice-whatsapp.yaml"
echo "   - /data/appservice-instagram.yaml"
echo "3. 'docker compose up -d' komutu ile sistemi başlatın."
