# PRISM Build & Infrastructure Guide

This guide explains how to build the PRISM mobile application and manage the single-server backend infrastructure.

## 1. Single-Server Infrastructure

PRISM now runs on a single Contabo VPS to simplify operations and reduce maintenance overhead.

### Server: Contabo Cloud VPS 20 SSD
- **IP Address**: `5.189.159.214`
- **Hostname**: `vmi3380172`
- **OS**: Ubuntu 24.04 LTS
- **Specs**: 4 vCPU, 11 GB RAM, 200 GB SSD
- **SSH Access**: Public key only (`~/.ssh/prism_deploy`)
- **Deployment Directory**: `/opt/prism`

### Services
| Service | Container Name | Description |
| :------ | :------------- | :---------- |
| PostgreSQL | `prism-db` | Synapse and bridge database |
| Matrix Synapse | `prism-synapse` | Core messaging server |
| WhatsApp Bridge | `prism-whatsapp` | Mautrix WhatsApp bridge |
| Monero Node | `monero-node` | Pruned Monero full node |
| Monero Wallet RPC | `monero-wallet-rpc` | Wallet RPC interface |
| PRISM Monero API | `prism-monero-api` | Internal Monero API |
| PRISM LLM API | `prism-llm-api` | AI assistant API |
| PRISM Retention | `prism-retention` | Message retention worker |
| Cloudflare Tunnel | `prism-tunnel` | Secure public access for `matrix.fathertkt.uk` |
| PRISM Website | `prism-website` | `prismas.net` download page |

## 2. Domains & DNS

| Domain | Use | Configuration |
| :----- | :-- | :------------ |
| `prismas.net` | Public website + APK download | A record → `5.189.159.214` |
| `www.prismas.net` | Website alias | A record → `5.189.159.214` |
| `matrix.fathertkt.uk` | Matrix homeserver | Cloudflare Tunnel |

## 3. Infrastructure Management Tools

Tools are located in `Backend/tools/`.

| Tool | Description |
| :--- | :---------- |
| `tools/check_server.py` | Health check for the single VPS |
| `tools/update_server.py` | Deploy Backend updates to the VPS |
| `tools/setup_prism_server.py` | Full server setup (hardening, Docker, clone, start) |

## 4. Building the Mobile App (APK)

The mobile client is built from `Frontend_Source/` using Gradle.

### Prerequisites

| Component | Path / Version |
| :--- | :--- |
| JDK 21 (Temurin) | `C:\AMDDesignTools\.xinstall\2025.2\tps\win64\jre21.0.5_11` |
| Android SDK | `tools/android/sdk` |
| Android Build-Tools | `34.0.0` |
| Compile/Target SDK | `36` |
| Gradle | `9.2.1` (wrapper) |

### Canonical Build

```powershell
cd Frontend_Source
$env:JAVA_HOME="C:\AMDDesignTools\.xinstall\2025.2\tps\win64\jre21.0.5_11"
$env:PATH="$env:JAVA_HOME\bin;$env:PATH"
./gradlew.bat :app:assembleFdroidDebug -x lint -x test --no-daemon --parallel
```

Output: `Frontend_Source/app/build/outputs/apk/fdroid/debug/`. Always ship the **`app-fdroid-universal-debug.apk`**.

```powershell
Copy-Item Frontend_Source/app/build/outputs/apk/fdroid/debug/app-fdroid-universal-debug.apk outputs/APK/prism-latest.apk
```

The website expects the APK at `/opt/prism/data/website/apk/prism-latest.apk`.

## 5. Deploying the Backend

### Quick Deploy

```bash
python tools/update_server.py
```

### Manual Deploy

```bash
# 1. Push changes to GitHub
git push origin master

# 2. SSH into the server
ssh -i ~/.ssh/prism_deploy root@5.189.159.214

# 3. Pull and restart
cd /opt/prism
git pull origin master
docker compose pull
docker compose up -d --remove-orphans
```

## 6. Monitoring Health

```powershell
python Backend/tools/check_server.py
```

## 7. Security Notes

- SSH password authentication is disabled on the VPS.
- Only the `prism-deploy-local` SSH key can log in as root.
- `ufw` allows only 22, 80, and 443.
- `fail2ban` protects SSH.
- All secrets live in `/opt/prism/.env`, which is never committed to Git.
