#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 WhatsApp Köprüsü Kurulumu Başlıyor...${NC}"

# 1. Database Oluşturma
echo -e "${YELLOW}🗄️  Adım 1: WhatsApp için Postgres Veritabanı Açılıyor...${NC}"
# Postgres konteynerında veritabanını oluşturan SQL
docker exec -i matrix-db psql -U synapse -d synapse -c 'CREATE DATABASE whatsapp;' 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ whatsapp veritabanı başarıyla oluşturuldu (veya zaten var).${NC}"
else
    echo -e "${YELLOW}ℹ️  Veritabanı kontrol edildi.${NC}"
fi

# 2. Klasör İzinleri
mkdir -p data/whatsapp

echo -e "${YELLOW}⚙️  Adım 2: WhatsApp Temel Konfigürasyon Üretiliyor...${NC}"
# WhatsApp imajını bir kerelik çalıştırıp config.yaml üretelim
docker compose run --rm whatsapp 

if [ $? -ne 0 ]; then
    echo -e "${RED}🛑 HATA: config.yaml üretilemedi!${NC}"
    exit 1
fi

echo -e "${YELLOW}⚙️  Adım 3: Konfigürasyonların Entegrasyonu Yapılıyor...${NC}"
# Python scripti ile bridge-synapse bağlantısı kurulur
python3 configure_whatsapp.py

if [ $? -ne 0 ]; then
    echo -e "${RED}🛑 HATA: Konfigürasyon dosyaları birbirini göremedi!${NC}"
    exit 1
fi

echo -e "${YELLOW}⚙️  Adım 4: Registration Dosyası Üretiliyor...${NC}"
# registration.yaml dosyası üretelim (Synapse'e tanıtmak için)
docker compose run --rm whatsapp -g

if [ $? -ne 0 ]; then
    echo -e "${RED}🛑 HATA: registration.yaml üretilemedi!${NC}"
    exit 1
fi

# Dosyayı Synapse klasörüne kopyalayalım ki Synapse ulaşabilsin
cp data/whatsapp/registration.yaml data/synapse/appservice-whatsapp.yaml

# Python scriptini tekrar çağırıp homeserver'a tam yolu ekleyelim
sed -i 's/- \/data\/registration.yaml/- \/data\/appservice-whatsapp.yaml/g' data/synapse/homeserver.yaml

echo -e "${GREEN}✅ Tüm Dosyalar Başarıyla Konfigüre Edildi!${NC}"
echo -e "\n--- ÇALIŞTIRMA VE QR KOD ---"
echo -e "1️⃣  Sistemi başlatmak için: ${YELLOW}docker compose restart synapse && docker compose up -d whatsapp${NC}"
echo -e "2️⃣  BAĞLANTI İÇİN TERMİNALDE QR KOD GÖRMEK İÇİN:"
echo -e "   Önce Element'te bir özel odaya girip kendinize bir odayı onaylattıktan sonra tünel odasında QR okutun."
echo -e "   Daha basitçe, telefonunuzu bağlamak için sadece şu komutu çalıştırıp QR kodu taratın:"
echo -e "   ${YELLOW}docker compose logs -f whatsapp${NC}"
echo -e "-------------------------"
