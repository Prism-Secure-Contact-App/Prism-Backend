#!/bin/bash

# PRISM Registration Generator
# Bu script WhatsApp ve Instagram köprüleri için gerekli kayıt dosyalarını üretir.

# 1. WhatsApp Registration Üretiliyor...
if [ ! -f "./data/whatsapp/config.yaml" ]; then
    echo "⚠️  WhatsApp config.yaml bulunamadı! Atlanıyor..."
else
    docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
        -v $(pwd)/data/whatsapp:/data \
        --entrypoint /usr/bin/mautrix-whatsapp \
        dock.mau.dev/mautrix/whatsapp:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    cp ./data/whatsapp/registration.yaml ./data/synapse/appservice-whatsapp.yaml
    echo "✅ WhatsApp registration üretildi."
fi

echo "2. Instagram (Meta) Registration Üretiliyor..."
if [ ! -f "./data/meta/config.yaml" ]; then
    echo "⚠️  Meta config.yaml bulunamadı! Atlanıyor..."
else
    docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
        -v $(pwd)/data/meta:/data \
        --entrypoint /usr/bin/mautrix-meta \
        dock.mau.dev/mautrix/meta:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    cp ./data/meta/registration.yaml ./data/synapse/appservice-instagram.yaml
    echo "✅ Instagram registration üretildi."
fi

echo ""
echo "Tüm registration dosyaları işlendi."
