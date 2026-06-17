#!/bin/sh
set -e

# Domain değişkenleri varsayılan değerlerle
DOMAIN="${DOMAIN:-prismas.net}"
MATRIX_DOMAIN="${MATRIX_DOMAIN:-matrix.${DOMAIN}}"

# Matrix .well-known delegation dosyalarını dinamik olarak oluştur
mkdir -p /usr/share/nginx/html/.well-known/matrix

cat > /usr/share/nginx/html/.well-known/matrix/server <<EOF
{"m.server": "${MATRIX_DOMAIN}:443"}
EOF

cat > /usr/share/nginx/html/.well-known/matrix/client <<EOF
{"m.homeserver": {"base_url": "https://${MATRIX_DOMAIN}"}}
EOF

# Nginx'i başlat
exec nginx -g "daemon off;"
