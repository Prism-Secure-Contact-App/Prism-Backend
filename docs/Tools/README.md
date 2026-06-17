# PRISM Tools — Reference

All Python helpers and SDK assets used during PRISM setup, deployment, and
recovery live under `tools/`. There is no other "scripts" location in the
repository — `scratch/` was retired on 2026-05-02 and its contents either
promoted here or removed.

## Layout

```
tools/
├── android/                       Android SDK + bundled Gradle (do not commit binaries to git).
│   ├── sdk/                       compileSdk 34 / 36 + build-tools 34/35.
│   └── gradle_dist/               Offline fallback for Gradle 8.5 (wrapper still uses 9.2.1).
├── check_server.py                Multi-server health check — RPi 4 + HP Elitebook.
├── update_server.py               Pack and deploy `Backend/` to the RPi 4.
├── setup_remote_monero.py         One-shot bootstrap for monerod on the HP Elitebook.
└── sync_synapse_db_password.py    Recovery: realign Synapse <-> PostgreSQL credentials.
```

## Tool catalogue

### `check_server.py`

| | |
| :--- | :--- |
| When to run | Before & after every backend change; whenever the app reports `[502]` errors. |
| What it checks | SSH reachability of both hosts, Docker container status (`prism-db`, `prism-synapse`, `prism-whatsapp` on RPi; `prism-monero` on HP), Synapse `/_matrix/client/versions`, Monero RPC `get_info`. |
| Exit code | `0` only when **all** checks pass. |
| Notes | Prints ✓ / ✗ glyphs; the script forces UTF-8 stdout so it renders on Windows cp1254/cp857. |

```powershell
python tools/check_server.py
```

### `update_server.py`

| | |
| :--- | :--- |
| When to run | After editing anything under local `Backend/`. |
| What it does | tars the `Backend/` directory (excluding `data/`), uploads via SFTP to `prism-backend/` on the RPi, runs `setup-prism.sh`, then `docker compose up -d`. |
| Pre-condition | `Backend/docker-compose.yml` must reference `${POSTGRES_PASSWORD}` and friends from the RPi-side `.env` (do not bake secrets into the tar). |

```powershell
python tools/update_server.py
```

### `setup_remote_monero.py`

| | |
| :--- | :--- |
| When to run | First-time bootstrap of the HP Elitebook node, or after a reinstall. |
| What it does | SSH-installs Docker (if missing), clones a minimal `prism-monero/` working tree, writes the agreed `docker-compose.yml`, starts `monerod`, and prints sync status. |
| Idempotent | Yes — re-running on a healthy node just verifies and pulls latest. |

```powershell
python tools/setup_remote_monero.py
```

### `sync_synapse_db_password.py`

| | |
| :--- | :--- |
| When to run | Synapse boot loops with `psycopg2.OperationalError: ... password authentication failed for user "synapse"`, **or** the app shows `[502] non-json bytes` because the Cloudflare tunnel cannot reach a healthy Synapse. |
| What it does | (1) backs up & patches `homeserver.yaml` `database.args.password` to the canonical value, (2) issues `ALTER USER synapse WITH PASSWORD '<canonical>'` inside `prism-db`, (3) restarts `prism-synapse`, (4) verifies `/versions` returns 200. |
| Canonical value | Defined at the top of the script as `CANONICAL_PASSWORD`. Update there if the team rotates the secret. |
| Idempotent | Yes — safe to re-run on an already-correct system (results in just a restart + verify). |

```powershell
python tools/sync_synapse_db_password.py
```

## Conventions for new tools

When you add another helper:

1. Drop the file directly under `tools/` (not in nested subdirs unless the file
   has supporting assets — Android SDK is the lone exception).
2. Add a section in this file with the same four-row table format
   (when, what, idempotency, command) so future agents and humans can find it
   without grepping.
3. Never log secrets. SSH passwords are fine to read from the constants block,
   but never `print(PASS)`.
4. Stamp any RPi mutation with a `.bak.<epoch>` so a human can revert.

## What was removed on 2026-05-02

- `scratch/` directory entirely (5 files): `setup_remote_monero.py` was promoted
  to `tools/`; `fix_config.py` + `fix_db.py` were merged into the new
  `tools/sync_synapse_db_password.py`; `debug_monero.py` and `debug_monero2.py`
  were deleted as the RPi no longer hosts Monero (it lives on the HP Elitebook).
- `Backend_Backup/` directory entirely. The active backend is `Backend/`
  (tracked at `github.com/Prism-Secure-Contact-App/Prism-Backend`, deployed by
  `tools/update_server.py`). The Synapse signing key inside the backup was
  redundant — the authoritative copy lives on the RPi at
  `/home/fathertkt/prism-backend/data/synapse/matrix.fathertkt.uk.signing.key`.
