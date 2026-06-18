# Project Environment Credentials

> [!IMPORTANT]
> This file contains **non-sensitive** connection metadata for AI agents. All actual secrets (passwords, tokens, API keys) live in `/opt/prism/.env` on the server and are **never** committed to Git.

## PRISM Single Server (Contabo VPS)

- **IP Address**: `5.189.159.214`
- **Hostname**: `vmi3380172`
- **Username**: `root`
- **Authentication**: SSH public key only (key: `~/.ssh/prism_deploy`)
- **SSH Port**: `22`
- **Deployment Directory**: `/opt/prism`
- **Services**: Matrix Synapse, PostgreSQL, WhatsApp Bridge, Monero Node + Wallet RPC, LLM API, Retention, Website, Cloudflare Tunnel

## Domains

| Domain | Purpose | Routing |
| :----- | :------ | :------ |
| `prismas.net` | Official website + APK download | A record → `5.189.159.214` (SSL pending) |
| `www.prismas.net` | Website alias | A record → `5.189.159.214` (SSL pending) |
| `matrix.fathertkt.uk` | Matrix homeserver | Cloudflare Tunnel |

> **Note:** `prismas.net` HTTPS is blocked by the Contabo VPS firewall (80/443 not open from the internet). Open the ports in the Contabo panel, then run certbot to activate HTTPS.

## Where Secrets Live

| Secret | Location |
| :----- | :------- |
| PostgreSQL password | `/opt/prism/.env` |
| Cloudflare Tunnel token | `/opt/prism/.env` |
| Synapse admin token | `/opt/prism/.env` |
| Monero wallet password | `/opt/prism/.env` |
| Matrix signing keys | `/opt/prism/data/synapse/` |
| Monero wallets | `/opt/prism/data/monero-wallets/` |

## Decommissioned Hosts

- **HP Elitebook (`100.77.114.31`)**: All Prism containers, images, and directories (`/home/fatih/prism-backend`, `/home/fatih/prism-monero`) have been removed. Only an unrelated `lieu-cloudflared` container remains.
- **Raspberry Pi 4 (`100.125.63.77`)**: Offline for an extended period; assumed decommissioned.

## SSH Access

```bash
ssh -i ~/.ssh/prism_deploy root@5.189.159.214
```

## Maintenance Commands

```bash
cd /opt/prism
docker compose ps
docker compose logs -f <service>
docker compose up -d --pull always
```

## Enabling HTTPS for prismas.net

Once the Contabo firewall allows 80/443:

```bash
cd /opt/prism
docker run --rm \
  -v /opt/prism/data/certbot/conf:/etc/letsencrypt \
  -v /opt/prism/data/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot --webroot-path=/var/www/certbot \
  --email talhakagantosun9@gmail.com --agree-tos --no-eff-email \
  -d prismas.net -d www.prismas.net
```

Then uncomment the HTTPS server block in `prismas.net/nginx.conf` and rebuild the website container.
