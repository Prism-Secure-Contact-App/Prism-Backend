#!/bin/bash
# PRISM Server Branding Tool
# Bu script sunucu tarafındaki tüm Matrix/Synapse ibarelerini PRISM ile değiştirir.

echo "--- PRISM Sunucu Kimliği Güncelleniyor ---"

# 1. Homeserver.yaml içindeki görünen isimleri değiştir
if [ -f "./data/synapse/homeserver.yaml" ]; then
    sed -i "s/Synapse/PRISM Server/g" ./data/synapse/homeserver.yaml
    sed -i "s/Matrix/PRISM/g" ./data/synapse/homeserver.yaml
    echo "[Tamam] homeserver.yaml güncellendi."
fi

# 2. Hoşgeldin mesajlarını ve HTML şablonlarını temizle
# Synapse default templates dizinini bulmaya çalış
TEMPLATES_DIR="./data/synapse/templates"
if [ -d "$TEMPLATES_DIR" ]; then
    find "$TEMPLATES_DIR" -type f -name "*.html" -exec sed -i "s/Matrix/PRISM/g" {} +
    find "$TEMPLATES_DIR" -type f -name "*.html" -exec sed -i "s/Element/PRISM Messenger/g" {} +
    echo "[Tamam] HTML şablonları güncellendi."
fi

echo "--- İslem Tamam! Sunucuyu 'docker compose restart synapse' ile yeniden başlatın. ---"
