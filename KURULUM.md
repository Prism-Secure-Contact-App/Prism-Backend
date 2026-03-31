# 🚀 Raspberry Pi 4 Matrix Synapse Kurulum Rehberi (Cloudflare Tunnel)

Bu rehber, üniversite ağı veya kısıtlı ağlar (NAT) arkasındaki Raspberry Pi 4'ünüzde Cloudflare Tunnel kullanarak **tamamen açık ve federasyonlu** bir Matrix Sunucusu kurmanızı sağlar.

---

## 🛠️ Ön Gereksinimler

1.  **Raspberry Pi 4** (Docker ve Docker Compose yüklü olmalı)
2.  **Bir Alan Adı (Domain)** (Cloudflare'e yönlendirilmiş olmalı)
3.  **Cloudflare Hesabı** (Zero Trust özelliği açık - Ücretsizdir)

---

## 📂 Adım 1: Dosyaları Hazırlama

İlk olarak `.env.template` dosyasını `.env` olarak kopyalayın ve içini düzenleyin:

```bash
cp .env.template .env
```
`.env` dosyasını açıp şu alanları doldurun:
- **`POSTGRES_PASSWORD`**: Çok güçlü bir şifre üretin.
- **`TUNNEL_TOKEN`**: Adım 2'de Cloudflare'den alıp buraya yapıştıracağız.
- **`SERVER_NAME`**: Matrix sunucu adınız (örn: `matrix.alanadiniz.com`).

---

## ☁️ Adım 2: Cloudflare Tunnel Ayarları

1.  [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) paneline gidin.
2.  Sol menüden **Networks** -> **Tunnels** yolunu izleyin.
3.  **Add a Tunnel** butonuna basın.
4.  Tip olarak **Cloudflared** seçin, tünele bir isim verin (örn: `matrix-pi`).
5.  **Install and update** sayfasında, tünel kodunun en sonunda yer alan **Token**'ı kopyalayın.
    *   *Kod şöyle görünür:* `cloudflared.exe service install eyJ......`
    *   Buradaki uzun `eyJ...` ile başlayan kısmı kopyalayın ve `.env` dosyasındaki `TUNNEL_TOKEN` kısmına yapıştırın.
6.  **Next** diyerek **Public Hostname** sekmesine geçin:
    *   **Subdomain:** `matrix` (veya ne isterseniz)
    *   **Domain:** Kendi alan adınızı seçin.
    *   **Service Type:** `HTTP`
    *   **URL:** `synapse:8008` (Docker ağındaki konteyner adı!)
7.  **Save Tunnel** diyerek kaydedin.

---

## ⚙️ Adım 3: İlk Synapse Konfigürasyonunu Üretme

Matrix Synapse ilk çalışmadan önce şifreleme anahtarlarını ve temel dosyaları üretmelidir. Pi terminalinde şu komutu çalıştırın:

```bash
# Değişkenleri yükleyip konfigürasyon üretelim
source .env
docker compose run --rm synapse generate-config -H $SERVER_NAME -e report_stats=$REPORT_STATS
```

Bu komut `./data/synapse/homeserver.yaml` dosyasını üretecektir.

---

## 🗄️ Adım 4: PostgreSQL Entegrasyonu (KRİTİK ADIM)

Pi 4'ün performansı için SQLite yerine PostgreSQL kullanmalıyız.
`./data/synapse/homeserver.yaml` dosyasını açın ve şu düzenlemeleri yapın:

1.  **`database:` kısmını bulun:**
    Varsayılan SQLite ayarını bulun ve **bağlantıyı tamamen silip** veya yorum satırı yapıp yerine şunları ekleyin:

```yaml
database:
  name: psycopg2
  args:
    user: synapse
    password: ".env dosyasına yazdığınız POSTGRES_PASSWORD"
    host: db
    database: synapse
    cp_min: 5
    cp_max: 10
```

2.  **Dinleyici Ayarları (Listeners):**
    `listeners:` altında port 8008'in `bind_addresses` kısmında `127.0.0.1` varsa, Cloudflare tünelinin bağlanabilmesi için bunu `['::', '0.0.0.0']` şeklinde değiştirin (Zaten varsayılan budur).

---

## 🚀 Adım 5: Sunucuyu Başlatma

Her şey hazır! Konteynerları arka planda başlatmak için:

```bash
docker compose up -d
```

Konteynerların sağlığını kontrol etmek için:
```bash
docker compose ps
```

---

## 🔑 Adım 6: Yönetici (Admin) Kullanıcı Oluşturma

Matrix sunucunuza bir kullanıcı açıp ona admin yetkisi vermek için sunucu çalışırken şu komutu çalıştırın:

```bash
docker exec -it matrix-synapse register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008
```
Sizden Kullanıcı Adı, Şifre ve admin yapılıp yapılmayacağını (`yes`) soracaktır.

---

## 🌐 Adım 7: Kullanım ve Federasyon

Kurulum bittikten sonra [Element Web](https://app.element.io/) veya telefon uygulaması üzerinden **Başka bir sunucu seç** (Change Server) diyerek kendi sunucunuzu (`https://matrix.alanadiniz.com`) yazıp giriş yapabilirsiniz.

### Federasyon Notu (Sunucular Arası Konuşma):
Cloudflare Tunnel + Subdomain kullandığınız için, diğer sunucular size `matrix.alanadiniz.com` üzerinden direkt erişecektir. Synapse bunu otomatik yönetir.
Eğer kullanıcı adınızın `@ahmet:alanadiniz.com` (Subdomain olmadan) olmasını isterseniz, ana sitenizin `.well-known` dosyalarını Matrix'e yönlendirmeniz gerekir. Bu rehber başlangıç için `matrix.alanadiniz.com` formatını eksiksiz kurar.
