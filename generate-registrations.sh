#!/bin/bash

# PRISM Registration Generator
# Bu script WhatsApp ve Instagram köprüleri için gerekli kayıt dosyalarını üretir.

PASS="1234"

# 1. WhatsApp Registration Üretiliyor...
if [ ! -f "./data/whatsapp/config.yaml" ]; then
    echo "⚠️  WhatsApp config.yaml bulunamadı! Atlanıyor..."
else
    echo $PASS | sudo -S docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
        -v $(pwd)/data/whatsapp:/data \
        --entrypoint /usr/bin/mautrix-whatsapp \
        dock.mau.dev/mautrix/whatsapp:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    
    if [ ! -s "./data/whatsapp/registration.yaml" ]; then
        echo "❌ WhatsApp registration.yaml üretilemedi. Docker çıktısını kontrol et." >&2
    else
        echo "⚙️  WhatsApp konfigüre ediliyor..."
        echo $PASS | sudo -S python3 configure_whatsapp.py
        echo $PASS | sudo -S cp ./data/whatsapp/registration.yaml ./data/synapse/appservice-whatsapp.yaml
        echo "✅ WhatsApp registration üretildi."
    fi
fi

# 2. Instagram (Meta) Registration Üretiliyor...
if [ ! -f "./data/meta/config.yaml" ]; then
    echo "⚠️  Meta config.yaml bulunamadı! Atlanıyor..."
else
    echo $PASS | sudo -S docker run --rm --security-opt seccomp=unconfined --platform linux/arm64 \
        -v $(pwd)/data/meta:/data \
        --entrypoint /usr/bin/mautrix-meta \
        dock.mau.dev/mautrix/meta:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    
    if [ ! -s "./data/meta/registration.yaml" ]; then
        echo "❌ Meta registration.yaml üretilemedi. Docker çıktısını kontrol et." >&2
    else
        echo "⚙️  Meta (Instagram) konfigüre ediliyor..."
        echo $PASS | sudo -S python3 configure_meta.py
        echo $PASS | sudo -S cp ./data/meta/registration.yaml ./data/synapse/appservice-instagram.yaml
        echo "✅ Instagram registration üretildi."
    fi
fi

echo "⚙️  Synapse konfigürasyonu temizleniyor..."
echo $PASS | sudo -S python3 cleanup_config.py

echo "Tüm registration dosyaları işlendi."
