#!/bin/bash
set -euo pipefail

# =============================================================================
# PRISM Admin Kullanıcı Oluşturma Scripti
# =============================================================================
# Synapse çalışırken admin kullanıcısı oluşturur.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
    echo "❌ HATA: .env dosyası bulunamadı!"
    exit 1
fi

export $(grep -v '^#' .env | xargs -d '\n')

echo "🔑 PRISM admin kullanıcısı oluşturuluyor..."
echo "   Sunucu: ${SERVER_NAME:-localhost}"
echo ""

docker compose exec synapse register_new_matrix_user \
    -c /data/homeserver.yaml \
    -a \
    http://localhost:8008
