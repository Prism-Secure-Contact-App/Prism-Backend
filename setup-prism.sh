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

# 2. PRISM Branding Uygulanıyor...
sed -i "s/Synapse/$SERVER_NAME/g" ./data/synapse/homeserver.yaml
python3 configure_synapse.py

# 3. WhatsApp Bridge Konfigürasyonu...
echo 1234 | sudo -S rm -f ./data/whatsapp/config.yaml
echo 1234 | sudo -S python3 configure_whatsapp.py

# 4. Instagram (Meta) Bridge Konfigürasyonu...
echo 1234 | sudo -S rm -f ./data/meta/config.yaml
echo 1234 | sudo -S python3 configure_meta.py

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
