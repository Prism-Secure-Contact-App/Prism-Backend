#!/bin/bash

# PRISM Registration Generator
# Bu script WhatsApp ve Instagram köprüleri için gerekli kayıt dosyalarını üretir.

# 1. WhatsApp Registration Üretiliyor...
if [ ! -f "./data/whatsapp/config.yaml" ]; then
    echo "⚠️  WhatsApp config.yaml bulunamadı! Atlanıyor..."
else
    docker run --rm --security-opt seccomp=unconfined \
        -v $(pwd)/data/whatsapp:/data \
        --entrypoint /usr/bin/mautrix-whatsapp \
        dock.mau.dev/mautrix/whatsapp:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    if [ ! -s "./data/whatsapp/registration.yaml" ]; then
        echo "❌ WhatsApp registration.yaml üretilemedi (boş veya yok). Docker çıktısını kontrol et." >&2
        exit 1
    fi

    echo "⚙️  WhatsApp konfigüre ediliyor..."
    python3 configure_whatsapp.py
    cp ./data/whatsapp/registration.yaml ./data/synapse/appservice-whatsapp.yaml
    echo "✅ WhatsApp registration üretildi."
fi

echo "2. Instagram (Meta) Registration Üretiliyor..."
if [ ! -f "./data/meta/config.yaml" ]; then
    echo "⚠️  Meta config.yaml bulunamadı! Atlanıyor..."
else
    docker run --rm --security-opt seccomp=unconfined \
        -v $(pwd)/data/meta:/data \
        --entrypoint /usr/bin/mautrix-meta \
        dock.mau.dev/mautrix/meta:latest \
        -c /data/config.yaml -r /data/registration.yaml -g
    if [ ! -s "./data/meta/registration.yaml" ]; then
        echo "❌ Meta registration.yaml üretilemedi (boş veya yok). Docker çıktısını kontrol et." >&2
        exit 1
    fi

    echo "⚙️  Meta (Instagram) konfigüre ediliyor..."
    python3 configure_meta.py
    cp ./data/meta/registration.yaml ./data/synapse/appservice-instagram.yaml
    echo "✅ Instagram registration üretildi."
fi

echo ""
echo ""
echo "⚙️  Synapse konfigürasyonu temizleniyor..."
python3 cleanup_config.py

echo "Tüm registration dosyaları işlendi."
