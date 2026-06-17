# PRISM Backend

PRISM uygulamasının arka ucu: Matrix Synapse mesajlaşma sunucusu, WhatsApp/Meta bridge'leri, Monero node ve Cloudflare Tunnel — tamamı Docker ile tek sunucuda çalışır.

## İçindekiler

- [Özellikler](#özellikler)
- [Mimari](#mimari)
- [Gereksinimler](#gereksinimler)
- [Hızlı Kurulum](#hızlı-kurulum)
- [Sunucu Önerisi](#sunucu-önerisi)
- [Cloudflare Tunnel Ayarları](#cloudflare-tunnel-ayarları)
- [Sık Kullanılan Komutlar](#sık-kullanılan-komutlar)
- [Sorun Giderme](#sorun-giderme)

## Özellikler

- **Matrix Synapse** ile kendi mesajlaşma sunucunuz
- **Çoklu WhatsApp Bridge desteği** — varsayılan birincil bridge + isteğe bağlı ikincil bridge
- **Mautrix Meta Bridge** ile Instagram/Facebook entegrasyonu (opsiyonel, kapalı)
- **Anonim / Session odaları** — varsayılan uçtan uca şifreli oda ayarları ve oda listesi gizliliği
- **Monero Node** (`monerod`) pruned modda
- **PRISM Payments Service** — kullanıcı bakiyesi sorgulama ve ödeme talepleri API'si
- **PRISM AI Relay** — WhatsApp/Meta AI entegrasyonu için altyapı (placeholder)
- **PostgreSQL** veritabanı
- **Cloudflare Tunnel** ile güvenli dış erişim
- **prismas.net websitesi** aynı sunucuda (APK indirme + duyurular)

## Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                        PRISM Sunucu                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Synapse    │  │  WhatsApp    │  │    Meta      │      │
│  │   (Matrix)   │──│   Bridge     │  │   Bridge     │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                   │
│  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │   monerod    │  │   Website    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Cloudflare Tunnel (cloudflared)          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Gereksinimler

- Docker + Docker Compose
- Bir alan adı (domain)
- Cloudflare hesabı (Zero Trust → Tunnels)

### Minimum sunucu kaynakları

| Kaynak | Minimum | Önerilen |
|---|---|---|
| RAM | 6 GB | **8 GB** |
| CPU | 2 vCPU | **4 vCPU** |
| Disk | 120 GB SSD | **200 GB+ SSD/NVMe** |

> Monero blockchain 2025 itibarıyla **pruned ~95–120 GB** yer kaplar. Full node için en az 400 GB disk gerekir.

## Hızlı Kurulum

### 1. Repoyu sunucuya kopyala

```bash
git clone https://github.com/Prism-Secure-Contact-App/Prism-Backend.git
cd Prism-Backend/prism-backend
```

### 2. `.env` dosyasını oluştur

```bash
cp .env.example .env
nano .env
```

Aşağıdaki alanları kendine göre doldur:

```env
DOMAIN=prismas.net
MATRIX_DOMAIN=matrix.prismas.net
SERVER_NAME=matrix.prismas.net
POSTGRES_PASSWORD=CokGucluBirSifre123!
TUNNEL_TOKEN=cloudflare_token_buraya
ENABLE_REGISTRATION=no
```

### 3. APK dosyasını yerleştir

Android uygulamasının APK dosyasını şu konuma koy:

```bash
mkdir -p data/website/apk
cp /path/to/prism.apk data/website/apk/prism-latest.apk
```

### 4. Konfigürasyon dosyalarını üret

```bash
./scripts/setup.sh
```

Bu script:
- Veri dizinlerini oluşturur
- Synapse config üretir
- PostgreSQL ayarlarını uygular
- WhatsApp/Meta bridge config'lerini hazırlar
- AppService kayıtlarını Synapse'e ekler

### 5. Cloudflare Tunnel'ı yapılandır

Cloudflare Zero Trust panelinden:

1. **Networks → Tunnels → Create a tunnel**
2. Tip olarak **Cloudflared** seç
3. Token'ı kopyala, `.env` dosyasındaki `TUNNEL_TOKEN` alanına yapıştır
4. **Public Hostname** ekle:

| Subdomain | Domain | Service Type | URL |
|---|---|---|---|
| `matrix` | `prismas.net` | HTTP | `synapse:8008` |
| `@` (veya `www`) | `prismas.net` | HTTP | `website:80` |

### 6. Servisleri başlat

```bash
docker compose up -d
```

### 7. Admin kullanıcı oluştur

```bash
./scripts/create-admin.sh
```

### 8. WhatsApp Bridge bağlantısı

Uygulamada (veya Element Web üzerinden) `@whatsappbot:matrix.prismas.net` ile konuşma başlat:

```
login
```

Gelen QR kodu telefonundaki WhatsApp → Bağlı Cihazlar → QR Tara ile okut.

## Sunucu Önerisi

Bütçe dostu ve ilk etap için yeterli:

| Sağlayıcı | Plan | RAM | CPU | Disk | Fiyat |
|---|---|---|---|---|---|
| **Contabo** | VPS 2 | 8 GB | 6 vCPU | 200 GB SSD | **~11 €/ay** |
| Hetzner | CPX31 | 8 GB | 4 vCPU | 160 GB NVMe | ~15 €/ay |
| Hetzner | CPX31 + 100 GB Volume | 8 GB | 4 vCPU | 260 GB NVMe | ~20 €/ay |

> **Önerim:** Contabo VPS 2. Fiyat/performans olarak en dengeli ve 200 GB disk Monero pruned node + Synapse için ilk etapta yeterli.

## Cloudflare Tunnel Ayarları

Tunnel public hostname'lerinde **Service Type: HTTP** seçin (Cloudflare zaten HTTPS terminasyonunu kendisi yapar).

### .well-known delegation

Website container'ı `/.well-known/matrix/server` ve `/.well-known/matrix/client` yollarını otomatik sunar. Böylece kullanıcı adlarınız `@user:prismas.net` şeklinde olabilir.

## Sık Kullanılan Komutlar

```bash
# Tüm temel servisleri başlat
docker compose up -d

# Durum kontrolü
docker compose ps

# Logları izle
docker compose logs -f

# Sadece Synapse logları
docker compose logs -f synapse

# WhatsApp bridge logları
docker compose logs -f whatsapp

# İkinci WhatsApp bridge'i başlat
docker compose --profile extra-whatsapp up -d

# Meta bridge'i başlat
docker compose --profile meta up -d

# AI relay'i başlat
docker compose --profile ai-relay up -d

# Monero node durumu
docker exec prism-monerod monerod status

# Bakiye API'sini kontrol et
curl http://localhost:8000/health

# Servisleri durdur
docker compose down
```

## Sorun Giderme

### WhatsApp bridge başlamıyor

```bash
docker compose logs whatsapp --tail 100
```

Config dosyasını yeniden üretmek için:

```bash
rm data/whatsapp/config.yaml data/whatsapp/registration.yaml
./scripts/setup.sh
docker compose up -d
```

### Payments servisi DB hatası veriyor

`payments` veritabanı PostgreSQL ilk başlatmada otomatik oluşturulur. Eğer oluşmamışsa:

```bash
docker compose exec db psql -U synapse -c "CREATE DATABASE payments;"
docker compose restart payments
```

### AI Relay henüz çalışmıyor

`prism-ai-relay` servisi şu anda altyapı/placeholder durumundadır. Tam Meta AI entegrasyonu için ileride geliştirilecektir. Başlatmak için:

```bash
docker compose --profile ai-relay up -d
```

### Monero senkronizasyonu çok yavaş

Pruned node kullanın (`--prune-blockchain` zaten varsayılan). Disk NVMe değilse sync oldukça yavaş olur.

### Disk doluyor

```bash
du -sh data/*
```

Monero log dosyalarını temizleyin:

```bash
docker exec prism-monerod sh -c "rm -f /monero/*.log*"
```

Synapse eski event'leri temizlemek için:

```bash
docker compose exec synapse synapse_auto_compressor
```

## Lisans

Bu proje [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) lisansı altında dağıtılmaktadır.
