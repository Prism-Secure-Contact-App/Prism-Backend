# CyberSecurity Guidelines for AI Agents

## 1. Credential Management
- Never hardcode passwords in scripts. Use `.env` files or the `docs/Environment/credentials.md` mapping.
- Ensure `.env` files are in `.gitignore`.

## 2. Server Access
- Use SSH keys instead of passwords where possible.
- Avoid exposing non-essential ports (Synapse uses 8008, 8448).
- Keep Docker images updated to avoid vulnerabilities.

## 3. Code Integrity
- Verify all third-party dependencies before installation.
- Do not push sensitive configuration files to public repositories.

## 4. Matrix/Synapse Specifics
- Ensure `registration_shared_secret` is kept private.
- Regularly monitor Synapse logs for unauthorized access attempts.
