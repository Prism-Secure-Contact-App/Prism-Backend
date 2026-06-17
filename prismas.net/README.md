# prismas.net

PRISM uygulamasının resmi web sitesi.

## Özellikler

- PRISM Android APK indirme sayfası
- Duyuru ve basın bültenleri (JSON tabanlı)
- Matrix `.well-known` delegation
- Hafif nginx tabanlı Docker imajı

## Duyuru Ekleme

`public/content/announcements.json` dosyasını düzenleyin:

```json
{
  "announcements": [
    {
      "title": "Duyuru Başlığı",
      "summary": "Kısa açıklama",
      "date": "2025-06-17",
      "tag": "Kategori"
    }
  ]
}
```

## APK Yükleme

APK dosyasını `prism-backend/data/website/apk/prism-latest.apk` konumuna koyun. Bu dizin Docker volume ile website container'ına bağlanır.

## Yerel Test

```bash
docker build -t prism-website .
docker run -p 8080:80 -e DOMAIN=prismas.net -e MATRIX_DOMAIN=matrix.prismas.net prism-website
```

Tarayıcıda: http://localhost:8080
