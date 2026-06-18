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
- **Services**: Matrix Synapse, PostgreSQL, WhatsApp Bridge, Monero Node, LLM API, Retention, Website, Cloudflare Tunnel

## Domains

| Domain | Purpose | Routing |
| :----- | :------ | :------ |
| `prismas.net` | Official website + APK download | A record → `5.189.159.214` |
| `www.prismas.net` | Website alias | A record → `5.189.159.214` |
| `matrix.fathertkt.uk` | Matrix homeserver | Cloudflare Tunnel |

## Where Secrets Live

| Secret | Location |
| :----- | :------- |
| PostgreSQL password | `/opt/prism/.env` |
| Cloudflare Tunnel token | `/opt/prism/.env` |
| Synapse admin token | `/opt/prism/.env` |
| Matrix signing keys | `/opt/prism/data/synapse/` |
| Monero wallets | `/opt/prism/data/monero-wallets/` |

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
