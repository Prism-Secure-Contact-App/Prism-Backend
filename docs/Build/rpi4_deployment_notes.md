# RPi4 PRISM Backend Deployment Notes

> **Last updated:** 2026-05-05  
> **Target:** Raspberry Pi 4 (ARMv8 / `linux/arm/v8`)  
> **Host:** `100.125.63.77` (user: `fathertkt`)  
> **Domain:** `matrix.fathertkt.uk` (Cloudflare Tunnel)

---

## 1. Architecture Overview

```
┌─────────────┐     Cloudflare Tunnel      ┌──────────────┐
│   Client    │ ◄─────────────────────────►│  prism-tunnel│
│  (Element)  │                            │   (RPi4)     │
└─────────────┘                            └──────┬───────┘
                                                  │
                                           ┌──────┴───────┐
                                           │  prism-synapse│
                                           │   (Matrix HS) │
                                           └──────┬───────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    │             │             │
                              ┌─────┴────┐  ┌────┴────┐  ┌────┴────┐
                              │prism-db  │  │prism-   │  │prism-   │
                              │(Postgres)│  │whatsapp │  │meta     │
                              └──────────┘  └─────────┘  └─────────┘
```

**Data dirs:**
- `data/synapse/` — Synapse config, media, signing keys
- `data/postgres/` — PostgreSQL data
- `data/whatsapp/` — WhatsApp bridge config + registration
- `data/meta/` — Meta (Instagram) bridge config + registration

---

## 2. Critical ARMv8 Compatibility Issue

**Problem:** `mautrix/whatsapp:v0.12.0` and `mautrix/meta:v0.4.0` images have **no ARMv8 manifest**. Docker pulls fail with:
```
no matching manifest for linux/arm/v8 in the manifest list entries
```

**Fix:** Use `latest` tag for both bridges in `docker-compose.yml`:
```yaml
services:
  whatsapp:
    image: dock.mau.dev/mautrix/whatsapp:latest
  meta:
    image: dock.mau.dev/mautrix/meta:latest
```

> ⚠️ `latest` is a moving target. Pin to a specific digest (`@sha256:...`) for reproducible production builds once you verify a working version.

---

## 3. File Ownership Pitfall (uid 1337)

**Problem:** Bridge containers run as uid `1337`. Files they create (`config.yaml`, `registration.yaml`) are unreadable by host user `fathertkt`.

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: './data/whatsapp/config.yaml'
```

**Fix:** Before running any config-patcher script:
```bash
chmod -R 777 data/whatsapp data/meta
```

> 🛡️ In production, use `chown 1337:1337` instead of `777`.

---

## 4. Bridge Two-Step Bootstrap (Cannot pass `-g` directly)

The mautrix bridge containers use `/docker-run.sh` entrypoint with this logic:

1. **No `config.yaml`** → generates default config → **exits** (container stops)
2. **`config.yaml` exists, no `registration.yaml`** → generates registration → **exits**
3. **Both exist** → starts bridge normally

You **cannot** pass `-g` as a `docker compose` argument. You must run the container twice:

```bash
# Step 1: Generate config.yaml (container exits automatically)
docker compose run --rm whatsapp

# Step 2: Patch config.yaml (homeserver, DB, bot username, permissions)
python3 configure_whatsapp.py

# Step 3: Generate registration.yaml (container exits automatically)
docker compose run --rm whatsapp

# Step 4: Patch registration.yaml (sender_localpart, namespaces, token sync)
python3 configure_whatsapp.py   # idempotent; patches both config and reg

# Step 5: Restart Synapse to pick up appservice registration
docker compose restart synapse

# Step 6: Start bridge
docker compose up -d whatsapp
```

---

## 5. Registration Token Sync Workflow

**The #1 source of `M_FORBIDDEN` errors** is token mismatch between:
- `data/whatsapp/registration.yaml` (bridge's copy)
- `data/synapse/appservice-whatsapp.yaml` (Synapse's copy)

When the bridge regenerates `registration.yaml`, it creates **new random tokens**. If Synapse still has the old file, every API call is rejected.

**Correct workflow:**
1. Let bridge generate `registration.yaml`
2. Patch it (fix `sender_localpart`, namespaces)
3. **Copy** (not rewrite) the patched file to `data/synapse/appservice-whatsapp.yaml`
4. Restart Synapse

```bash
# After configure_whatsapp.py runs, verify tokens match:
diff data/whatsapp/registration.yaml data/synapse/appservice-whatsapp.yaml
```

### 5.1 `sender_localpart` Must Match Bot Username

**Problem:** If `registration.yaml` has a random `sender_localpart` (e.g. `eSxXfzEkTtKGCPtNmZTc7R9n2NLTHSWH`) but `config.yaml` says `appservice.bot.username: pwb-bot`, Synapse rejects the bot:
```
M_FORBIDDEN (HTTP 403): Application service has not registered this user (@pwb-bot)
```

**Fix:** Ensure `sender_localpart` in both `registration.yaml` and `appservice-*.yaml` matches the bot username:
```yaml
# registration.yaml & appservice-whatsapp.yaml
sender_localpart: pwb-bot   # must match config.yaml appservice.bot.username
```

> 💡 `configure_whatsapp.py` already enforces this, but if you ever regenerate registration manually, you must re-run the patch script.

---

## 6. Synapse v1.151.0 Broke Appservice `/sync`

**Problem:** Synapse `latest` (v1.151.0, 2026-04-07) added this check:
```python
# synapse/handlers/sync.py line ~1715
app_service = self.store.get_app_service_by_user_id(user_id)
if app_service:
    raise NotImplementedError()
```

This **intentionally kills** appservice users doing `/sync`. mautrix bridges use `/sync` for end-to-bridge encryption (e2ee).

**Symptom:** Bridge logs show:
```
ERR Error /syncing, waiting 10 seconds error="M_UNKNOWN (HTTP 500): Internal server error" component=crypto
```

Synapse logs show:
```
ERROR - GET-xxx - Failed handle request via 'SyncRestServlet'
NotImplementedError
```

### Root Cause

Synapse v1.151.0 added an unconditional `raise NotImplementedError()` in `synapse/handlers/sync.py` line ~1715 for any user that belongs to an appservice. mautrix bridges rely on `/sync` to receive end-to-bridge encryption keys and to-device events.

### Permanent Fix (Chosen by PRISM)

Patch `sync.py` to replace `raise NotImplementedError()` with `pass`, then mount the patched file into the container via `docker-compose.yml`. This restores the pre-v1.151 behavior without downgrading.

```bash
# 1. Copy sync.py out of the running container
docker cp prism-synapse:/usr/local/lib/python3.13/site-packages/synapse/handlers/sync.py \
  ./data/synapse/synapse_handlers_sync.py

# 2. Patch it on the host
sed -i 's/            raise NotImplementedError()/            pass/' \
  ./data/synapse/synapse_handlers_sync.py

# 3. Mount it in docker-compose.yml (under synapse volumes)
#      - ./data/synapse/synapse_handlers_sync.py:/usr/local/lib/python3.13/site-packages/synapse/handlers/sync.py:ro

# 4. Recreate Synapse with the mount
docker compose up -d --force-recreate synapse
```

> ⚠️ The exact container path (`/usr/local/lib/python3.13/...`) may change if Synapse updates its base image Python version. After any Synapse image update, verify the path still matches.

**Current PRISM choice:** Keep e2ee **enabled** in both bridges and use the patched `sync.py` above.

---

## 7. PostgreSQL Cleanup for Bridge Reset

If you need to fully reset a bridge (stale crypto, corrupt state, or just want a clean start), **deleting the bot user from Synapse's `users` table is not enough**.

Related tables that can cause `UniqueViolation` on re-registration:
- `profiles`
- `user_external_ids`
- `account_data`
- `devices`
- `access_tokens`

**Nuclear option:** Drop and recreate the bridge's dedicated database:
```bash
docker exec prism-db psql -U synapse -d postgres -c "DROP DATABASE IF EXISTS mautrix_whatsapp;"
docker exec prism-db psql -U synapse -d postgres -c "CREATE DATABASE mautrix_whatsapp OWNER synapse;"
```

> ⚠️ This destroys all bridge state (logins, portal mappings, history). Only use when no users are logged in.

---

## 8. Meta (Instagram) Bridge Specifics

- **Network mode must be `instagram`** — default is Facebook Messenger. `configure_meta.py` forces this.
- **Crypto DB is SQLite** (`data/meta/*.db*`), not PostgreSQL. If you see:
  ```
  FTL Failed to start bridge error="failed to start Matrix connector: the supplied account key is invalid"
  ```
  Delete the crypto DB files:
  ```bash
  rm -f data/meta/*.db*
  ```

---

## 9. Cloudflare Tunnel & Media

- Cloudflare Tunnel (`cloudflared`) handles all external traffic. No reverse proxy needed on the Pi.
- **Remote media avatars** (e.g. `mxc://maunium.net/...`) will fail with HTTP 502 if the homeserver cannot reach the remote server. This is harmless — the bridge falls back to no avatar.

---

## 10. Complete Reset Checklist

Use this when everything is broken and you want to start fresh:

```bash
# 1. Stop bridges
docker compose stop whatsapp meta

# 2. Drop bridge databases
docker exec prism-db psql -U synapse -d postgres -c "DROP DATABASE IF EXISTS mautrix_whatsapp;"
docker exec prism-db psql -U synapse -d postgres -c "DROP DATABASE IF EXISTS mautrix_meta;"
docker exec prism-db psql -U synapse -d postgres -c "CREATE DATABASE mautrix_whatsapp OWNER synapse;"
docker exec prism-db psql -U synapse -d postgres -c "CREATE DATABASE mautrix_meta OWNER synapse;"

# 3. Remove bridge configs
rm -rf data/whatsapp/* data/meta/*

# 4. Re-bootstrap (repeat for each bridge)
docker compose run --rm whatsapp          # generate config
chmod -R 777 data/whatsapp
python3 configure_whatsapp.py             # patch config + registration
docker compose run --rm whatsapp          # generate registration
python3 configure_whatsapp.py             # patch registration, copy to synapse

# 5. Restart Synapse
docker compose restart synapse

# 6. Start bridges
docker compose up -d whatsapp meta
```

---

## 11. Health Checks

Use `tools/check_server.py` for automated health checks:
- RPi4 SSH + Docker container status
- HP laptop Monero RPC height check

For quick manual checks:
```bash
# All PRISM containers
docker compose ps

# Bridge status (look for "Bridge started")
docker logs prism-whatsapp --tail 5
docker logs prism-meta --tail 5

# Synapse API
curl -s http://localhost:8008/_matrix/client/versions | head -c 200
```

---

## 12. Lessons Learned (Summary for Future Agents)

1. **Always use `latest` for mautrix bridges on ARMv8** — pinned version tags often lack ARM manifests.
2. **Always `chmod 777` bridge data dirs before patching** — containers run as uid 1337.
3. **Never rewrite `registration.yaml` tokens manually** — always copy the bridge-generated file to Synapse's dir.
4. **`sender_localpart` MUST match `appservice.bot.username`** — otherwise you get `M_FORBIDDEN` forever.
5. **Synapse `latest` can break appservices** — v1.151.0 killed `/sync` for AS users. Patch `sync.py` to restore support (see Section 6) rather than disabling encryption.
6. **Bridge bootstrap is two-step** — container auto-exits after generating config, then again after generating registration.
7. **Dropping the bridge DB is safer than cleaning Synapse users** — orphaned `devices`/`profiles` rows cause re-registration failures.
