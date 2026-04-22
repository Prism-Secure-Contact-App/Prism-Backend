#!/bin/bash
# PRISM Backend MVP Entegrasyon Test Betiği
# Bu script, Prism-Synapse ile Mautrix (WhatsApp ve Meta/Instagram) köprülerinin
# birleşik MVP testi için gerekli ortamı hazırlar ve çalıştırır.

echo "=========================================="
echo "PRISM Backend MVP & Bridge Setup Başlıyor..."
echo "=========================================="

echo "[1/4] Docker ortamı denetleniyor..."
docker-compose down

echo "[2/4] Veritabanı ve Synapse başlatılıyor..."
docker-compose up -d db synapse
sleep 10 # Wait for db & synapse

echo "[3/4] Bridge (WhatsApp ve Instagram) Servisleri başlatılıyor..."
docker-compose up -d whatsapp meta

echo "[4/4] Bridge Kayıtları Synapse'e İşleniyor..."
# Burada Mautrix-WhatsApp ve Mautrix-Meta'nın appservice YAML konfigürasyonlarını 
# hedef köprü container'larından kopyalayıp synapse data dizinine linklediğimizi varsayıyoruz:
# (Bu mimaride WhatsApp scriptleri `setup_whatsapp.sh` içerisinde halihazırda var)
bash ./setup_whatsapp_local.sh

echo "=========================================="
echo "MVP Backend ayağa kalktı. Logları kontrol etmek için:"
echo "docker-compose logs -f whatsapp meta"
echo "Mobil uygulamada 'Instagram'ı Bağla' akışından alınan çerezler API test aracılığıyla Mautrix-Meta'ya beslenecek."
echo "=========================================="
