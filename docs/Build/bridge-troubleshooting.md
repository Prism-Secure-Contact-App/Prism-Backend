# Bridge Troubleshooting Guide (WhatsApp & Meta)

## Issue Summary
WhatsApp ve Meta bridges mesajlara cevap vermiyorlar. Bridgeler Synapse tarafından tanınmıyor veya mesaj routing başarısız oluyor.

## Root Causes Identified

### 1. ❌ appservice-whatsapp.yaml - Sender Mismatch
**Location**: `Backend/data/synapse/appservice-whatsapp.yaml`

**Problem**: 
```yaml
sender_localpart: whatsapp-as  # ← WRONG
```

**Should be**:
```yaml
sender_localpart: pwb-bot  # ← per configure_whatsapp.py line 106
```

**Impact**: Synapse doesn't recognize the bridge's messages; they get dropped or rejected with auth errors.

---

### 2. ❌ appservice-meta.yaml - Not Configured
**Location**: `Backend/data/synapse/appservice-meta.yaml`

**Problem**: File is empty or doesn't exist.

**Should contain**:
```yaml
id: meta
url: http://prism-meta:29319
as_token: <generated_in_config.yaml>
hs_token: <generated_in_config.yaml>
sender_localpart: pmb-bot
rate_limited: false
namespaces:
    users:
        - regex: ^@pmb-bot:matrix.fathertkt.uk$
          exclusive: true
        - regex: ^@meta_.*:matrix.fathertkt.uk$
          exclusive: true
de.sorunome.msc2409.push_ephemeral: true
receive_ephemeral: true
encryption: true
```

**Impact**: Meta bridge is not registered with Synapse at all.

---

### 3. ❌ Meta Bridge Mode Not Set to Instagram
**Location**: `Backend/data/meta/config.yaml`

**Current**:
```yaml
network:
  mode: facebook  # ← WRONG for PRISM v1.0.0
```

**Should be**:
```yaml
network:
  mode: instagram  # ← Per PRISM v1.0.0 plan
  receive_instagram_typing_indicators: true
```

**Impact**: Bridge connects to Facebook Messenger instead of Instagram.

---

### 4. ⚠️ homeserver.yaml AppService Registration
**Location**: `Backend/data/synapse/homeserver.yaml`

**Check**: Verify that both files are listed:
```yaml
app_service_config_files:
  - /data/appservice-whatsapp.yaml
  - /data/appservice-meta.yaml
```

**If missing**: Add them manually or re-run configuration scripts.

---

### 5. ⚠️ Bot User Accounts Not Created
**Problem**: `pwb-bot` and `pmb-bot` don't exist on Synapse.

**Solution**: Use Synapse admin API or SQL to create:
```bash
# Create WhatsApp bot (as admin)
curl -X POST /_synapse/admin/v1/register \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"user_id": "pwb-bot", "password": "botpass123", "displayname": "WhatsApp bridge bot"}'

# Create Meta bot
curl -X POST /_synapse/admin/v1/register \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"user_id": "pmb-bot", "password": "botpass123", "displayname": "Meta bridge bot"}'
```

---

### 6. ⚠️ Bridge Container Ports/Addresses
**Verify**:
- WhatsApp: listening on `0.0.0.0:29318`
- Meta: listening on `0.0.0.0:29319`
- Synapse can reach them via `http://prism-whatsapp:29318` and `http://prism-meta:29319`

**Check on RPi**:
```bash
docker logs prism-whatsapp 2>&1 | grep -i "listening\|error"
docker logs prism-meta 2>&1 | grep -i "listening\|error"
```

---

## Fix Sequence

### Step 1: Fix appservice-whatsapp.yaml
```bash
cd Backend/data/synapse
sed -i 's/sender_localpart: whatsapp-as/sender_localpart: pwb-bot/' appservice-whatsapp.yaml
```

### Step 2: Generate & Copy appservice-meta.yaml
```bash
cd Backend
python3 configure_meta.py
```

### Step 3: Update Meta Config to Instagram Mode
```bash
cd Backend/data/meta
# Edit config.yaml and set: network.mode = instagram
python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    cfg = yaml.safe_load(f) or {}
cfg['network']['mode'] = 'instagram'
cfg['network']['receive_instagram_typing_indicators'] = True
with open('config.yaml', 'w') as f:
    yaml.safe_dump(cfg, f)
print('✅ Meta mode set to instagram')
"
```

### Step 4: Verify homeserver.yaml
```bash
grep "app_service_config_files" Backend/data/synapse/homeserver.yaml
# Should show both files
```

### Step 5: Restart Bridges & Synapse
```bash
cd Backend
docker compose restart whatsapp meta synapse
```

### Step 6: Check Bridge Connectivity
```bash
docker logs prism-synapse 2>&1 | grep -i "appservice"
docker logs prism-whatsapp 2>&1 | head -50
docker logs prism-meta 2>&1 | head -50
```

---

## Automated Fix & Check Scripts

PRISM projesi çevrimiçi olarak bridge sorunlarını çözmek için iki ana script sağlar:

### 1. `setup_bridges.py` - Otomatik Kurulum & Tamir
```bash
cd Backend
python3 setup_bridges.py
```

**Ne yapar:**
- AppService registration dosyalarını düzelt (sender_localpart mismatch)
- Meta mode'unu facebook → instagram'a çevir
- homeserver.yaml'a appservice'leri ekle
- Bot user'ları doğrula
- Servisleri restart et
- Log'ları kontrol et

### 2. `check_bridges.py` - Sağlık Kontrolü & Debugging
```bash
cd Backend
python3 check_bridges.py
```

**Ne kontrol eder:**
- Container status'u
- AppService registration dosyaları
- homeserver.yaml konfigürasyonu
- Bridge port'ları & connectivity
- Synapse appservice event'leri
- Bot user'ları DB'de
- Tavsiye edilen fix'leri sunar

---

## Quick Start

**Bridge'leri kontrol etmek:**
```bash
cd Backend && python3 check_bridges.py
```

**Sorunları otomatik tamir etmek:**
```bash
cd Backend && python3 setup_bridges.py
```

---


