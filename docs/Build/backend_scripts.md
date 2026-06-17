# Backend Scripts Reference

## `Backend/setup_admin.py`

Idempotent admin account creation for PRISM Synapse.

| | |
| :--- | :--- |
| When to run | During first-time setup, or after a fresh Synapse install. |
| What it does | Reads `PRISM_ADMIN_USERNAME`, `PRISM_ADMIN_PASSWORD` from env/`.env`, validates password policy (min 8, upper/lower/digit/special), then calls Synapse's shared-secret registration endpoint. |
| Idempotent | Yes — if the user already exists, it logs a warning and exits 0. |
| Pre-condition | `SYNAPSE_SHARED_SECRET` must be set (from `homeserver.yaml`). |

```bash
cd /home/fnech/prism-backend
export SYNAPSE_SHARED_SECRET="..."
export PRISM_ADMIN_USERNAME="admin"
export PRISM_ADMIN_PASSWORD="..."
python3 setup_admin.py
```

---

## `Backend/llm_api_service.py`

Lightweight FastAPI gateway for PRISM LLM API keys and Meta AI proxy.

| | |
| :--- | :--- |
| When to run | Auto-started by Docker Compose (`prism-llm-api` service). |
| What it does | Generates/rotates/deletes per-user API keys (`prism_sk_...`). Proxies `/v1/llm/chat/completions` to Meta AI. |
| Idempotent | Yes — re-creating a key overwrites the old one. |
| Pre-condition | `META_AI_ENDPOINT` and `META_AI_API_KEY` must be configured in `.env`. |

```bash
# Manual run (dev only)
pip install fastapi uvicorn httpx
export META_AI_ENDPOINT="https://meta-ai.example.com/v1"
export META_AI_API_KEY="..."
python3 llm_api_service.py
```

**Docker Compose integration** (already in `docker-compose.yml`):
```yaml
  prism-llm-api:
    build:
      context: .
      dockerfile: Dockerfile.llm-api
    container_name: prism-llm-api
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - PRISM_LLM_API_PORT=8080
      - META_AI_ENDPOINT=${META_AI_ENDPOINT:-}
      - META_AI_API_KEY=${META_AI_API_KEY:-}
      - SYNAPSE_URL=http://synapse:8008
      - SYNAPSE_ADMIN_TOKEN=${SYNAPSE_ADMIN_TOKEN:-}
    depends_on:
      - synapse
```

---

## `Backend/prism_retention_bridge.py`

Session Room retention enforcer. Scans rooms for `m.room.retention` state events and purges expired messages.

| | |
| :--- | :--- |
| When to run | Auto-started by Docker Compose (`prism-retention` service). Runs periodically every `SCAN_INTERVAL_MIN` minutes. |
| What it does | Lists all rooms via Synapse Admin API, checks for `m.room.retention` state event, calculates `before_ts = now - max_lifetime`, then calls `POST /_synapse/admin/v1/purge_history/{room_id}` to delete old messages. |
| Idempotent | Yes — purging the same history range twice is a no-op. |
| Pre-condition | `SYNAPSE_ADMIN_TOKEN` must be set in `.env`. |

```bash
# Manual run (dev only)
export SYNAPSE_URL=http://localhost:8008
export SYNAPSE_ADMIN_TOKEN="..."
export SCAN_INTERVAL_MIN=60
python3 prism_retention_bridge.py
```

**Docker Compose integration** (already in `docker-compose.yml`):
```yaml
  prism-retention:
    build:
      context: .
      dockerfile: Dockerfile.retention
    container_name: prism-retention
    restart: unless-stopped
    environment:
      - SYNAPSE_URL=http://synapse:8008
      - SYNAPSE_ADMIN_TOKEN=${SYNAPSE_ADMIN_TOKEN:-}
      - SCAN_INTERVAL_MIN=${SCAN_INTERVAL_MIN:-60}
    depends_on:
      - synapse
```

---

## `Backend/Dockerfile.llm-api`

Multi-stage build for the LLM API service.

- Base: `python:3.11-slim`
- Dependencies: `fastapi`, `uvicorn[standard]`, `httpx`
- Port: `8080`
- Healthcheck: `GET /health` every 30s

## `Backend/Dockerfile.retention`

Minimal build for the retention bridge.

- Base: `python:3.11-slim`
- Dependencies: `requests`
- Entrypoint: `python prism_retention_bridge.py`

---

## Environment Variables

Add these to `Backend/.env`:

```bash
# LLM API
META_AI_ENDPOINT=
META_AI_API_KEY=

# Retention Bridge
SYNAPSE_ADMIN_TOKEN=
SCAN_INTERVAL_MIN=60
```
