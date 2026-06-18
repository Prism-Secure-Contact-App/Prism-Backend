# PRISM Deployment & Code Quality Update — 2026-06-18

## Server Deployment (Contabo VPS)

- All PRISM services are running on `5.189.159.214` under `/opt/prism`.
- Matrix homeserver is reachable via Cloudflare Tunnel at `matrix.fathertkt.uk`.
- Monero wallet RPC is working with a fresh empty wallet (`balance: 0 XMR`).
- WhatsApp bridge is connected to Synapse and waiting for user login.
- Website (`prismas.net`) is served on port 80; HTTPS is pending Contabo firewall changes.

## HP Elitebook Cleanup

- Stopped and removed all Prism containers from `100.77.114.31`.
- Removed local Prism Docker images.
- Deleted `/home/fatih/prism-backend` and `/home/fatih/prism-monero` (freed ~80 GB of disk space).
- Confirmed no Prism containers, images, or public ports remain on the host.

## Website Improvements (`Backend/prismas.net`)

- Added mobile navigation hamburger menu.
- Added accessibility enhancements: skip-link, aria labels, focus states.
- Added OpenGraph/Twitter Card meta tags and favicon.
- Made download link use `apkFilename` from `app-info.json`.
- Made copyright year dynamic.
- Added modern security headers in nginx: CSP, Permissions-Policy, HSTS placeholder.
- Enforced `application/vnd.android.package-archive` MIME type for APK downloads.

## Android App Fixes (`Frontend_Source`)

- Replaced crash-risk `TODO()` in `RoomMemberMapper` with a safe fallback.
- Disabled fake-success path in `LoginWithClassicPresenter`; now returns a clear failure until migration is implemented.
- Replaced sub-space creation `TODO()` with a safe private-space fallback.
- Migrated `VaultManager` from plain `DataStore` to `EncryptedSharedPreferences`.
- Exposed Monero mnemonic/view/spend keys in onboarding and wallet settings presenters.
- Centralized homeserver URL and bridge bot IDs in `AuthenticationConfig`.
- Moved hardcoded onboarding strings to string resources.
- Improved WhatsApp bridge prompt copy (consistent Turkish).

## Remaining Blockers

1. **HTTPS for `prismas.net`**: Requires opening 80/443 in the Contabo VPS firewall.
2. **Monero node sync**: The pruned node is still catching up (~39% at the time of writing). Transactions should wait until fully synced.
3. **PRISM Classic migration**: The feature flag path still needs a real session migration implementation.
4. **Duplicate `MoneroWalletDataStore`**: Still duplicated in `features/ftue/impl` and `features/preferences/impl`; should be moved to a shared library module.
