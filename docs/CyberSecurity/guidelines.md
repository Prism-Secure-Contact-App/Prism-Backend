# CyberSecurity Guidelines for AI Agents

## 1. Credential Management
- Never hardcode passwords, tokens, or API keys in scripts.
- Keep all secrets in `/opt/prism/.env` on the server.
- Ensure `.env` is listed in `.gitignore` and never pushed to GitHub.
- Rotate the PostgreSQL password and Synapse admin token after major incidents.

## 2. Server Access
- SSH password authentication is disabled on the VPS; only public-key auth is allowed.
- Keep the private key (`~/.ssh/prism_deploy`) secure and never share it.
- Expose only essential ports: 22 (SSH), 80 (HTTP), 443 (HTTPS).
- `ufw` and `fail2ban` are active on the server.
- Keep Docker images updated: `docker compose pull && docker compose up -d`.

## 3. Code Integrity
- Verify all third-party dependencies before installation.
- Do not push sensitive configuration files to public repositories.
- Review changes to `docker-compose.yml` and `.env.example` before deployment.

## 4. Matrix/Synapse Specifics
- Keep `registration_shared_secret`, `macaroon_secret_key`, and `form_secret` private.
- Store Synapse signing keys only on the server (`/opt/prism/data/synapse/`).
- Regularly monitor Synapse logs for unauthorized access attempts.
- Keep Synapse and bridges updated to the latest stable images.

## 5. Monero Security
- Monero wallets are stored in `/opt/prism/data/monero-wallets/`.
- Wallet RPC runs without login (`--disable-rpc-login`) inside the private Docker network only.
- Never expose Monero RPC ports (`18081`, `18083`) to the public internet.
