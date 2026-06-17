# PRISM Project Status — 2026-05-27 (v1.0.0 Release Candidate)

## Current State

### Infrastructure
- **RPi4 (100.125.63.77)**: All containers healthy — Synapse, PostgreSQL, WhatsApp bridge, Cloudflare tunnel
- **HP Elitebook (100.77.114.31)**: Monero node running
- **Synapse API**: Responding normally (`/_matrix/client/versions` returns 200)
- **Domain**: `matrix.fathertkt.uk` accessible via Cloudflare Tunnel

### Completed Features (v1.0.0)

#### Authentication
- ✅ **Login**: Username + Password, hardcoded homeserver `matrix.fathertkt.uk`
- ✅ **Registration**: Direct Synapse `/_matrix/client/v3/register` with `m.login.dummy`
- ✅ **Password Policy**: Client-side validation — min 8 chars, upper/lower, digit, special char

#### Bridges
- ✅ **WhatsApp Bridge**: Full flow working — phone input, pairing code, connect/disconnect with `list-logins` + `logout <id>`
- ✅ **Instagram Bridge**: Completely removed from app (UI, Presenter, FlowNode, FTUE)
- ✅ **Bridge Room Filtering**: Bot/bridge rooms hidden from main room list

#### Monero Wallet (Native SDK)
- ✅ **`im.molly:monero-wallet-sdk:1.0.0`** integrated via Gradle
- ✅ **Wallet Creation**: FTUE onboarding uses real `InProcessWalletService.connect()` + `WalletProvider.createNewWallet()`
- ✅ **Wallet Open**: Settings uses `SandboxedWalletService.connect()` + `WalletProvider.openWallet()`
- ✅ **Wallet Storage**: `MoneroWalletDataStore` persists to `filesDir/prism_wallet/monero_wallet.bin`
- ✅ **Address Display**: Settings screen shows real `wallet.publicAddress.address`
- ✅ **Security Note**: SDK does **not** expose seed phrase / view key / spend key (sandboxed C++ design). UI shows "SDK tarafından gizli tutulmaktadır" for these fields.

#### Settings
- ✅ **Developer Options**: Completely removed from release build
- ✅ **Cüzdan Güvenliği (Monero Wallet)**: Real SDK-backed settings screen
- ✅ **LLM API**: Settings screen for API key generation, rotation, and deletion
- ✅ **Deep Work Mode**: Toggle in Settings, `forceDarkTheme = true` when enabled, WA bridge notifications suppressed
- ✅ **Köprüler (Bridge Settings)**: WhatsApp-only, with phone number display and disconnect

#### Session Rooms (Gizli Sohbet)
- ✅ **Create Room UI**: Session Room switch, auto-delete timer (1h / 12h / 24h / after-read), screenshot protection toggle
- ✅ **Client-side Retention Event**: `ConfigureRoomPresenter` sends `PUT /_matrix/client/v3/rooms/{roomId}/state/m.room.retention` with `max_lifetime` immediately after room creation
- ✅ **Backend Retention Bridge**: `prism_retention_bridge.py` + Docker Compose service purges expired messages via Synapse Admin API

#### PrismAI
- ✅ **Onboarding Popup**: FTUE flow includes PrismAI promotion step after Monero wallet setup
- ✅ **LLM API Key Management**: Client-side generation, rotate, delete
- ✅ **LLM API Backend**: `Dockerfile.llm-api` + `docker-compose.yml` `prism-llm-api` service

#### Onboarding (FTUE)
- ✅ **Step 1**: Session Verification
- ✅ **Step 2**: Notifications Opt-in
- ✅ **Step 3**: Lockscreen Setup
- ✅ **Step 4**: WhatsApp Bridge Setup
- ✅ **Step 5**: Monero Wallet Setup (real SDK)
- ✅ **Step 6**: PrismAI Onboarding
- ✅ **Step 7**: Analytics Opt-in

#### Admin & Backend
- ✅ **Admin Setup Script**: `Backend/setup_admin.py` — idempotent admin creation from `.env` / `SYNAPSE_SHARED_SECRET`
- ✅ **LLM API Service**: `Backend/llm_api_service.py` + `Dockerfile.llm-api` + `docker-compose.yml`
- ✅ **Retention Bridge**: `Backend/prism_retention_bridge.py` + `Dockerfile.retention` + `docker-compose.yml`

### Removed Features
- ❌ **Instagram Bridge**: All code removed (Presenter, View, State, Events, FlowNode, FTUE step)
- ❌ **Developer Options**: Hidden/removed from Preferences root
- ❌ **Meta Bridge FTUE Step**: Removed from `DefaultFtueService`

### Known Limitations
- **Monero Seed/Keys**: `monero-wallet-sdk` (Molly) sandboxes C++ wallet2 and intentionally does **not** expose mnemonic, view key, or spend key to the JVM layer. Wallet backup is done via `WalletDataStore` (encrypted file), not via seed phrase display.
- **Session Rooms Enforcement**: Client sends `m.room.retention` event on creation. Backend `prism-retention` service purges expired messages. True "zero server trace" also requires client-side redaction of already-delivered messages on all peers.
- **Deep Work Zen Theme**: Currently forces `darkTheme = true` via `PRISMThemeApp`. A custom "zen" color palette would require `SemanticColors` customization.
- **Monero Node URL**: Hardcoded to `https://node.community.rino.io:18081` in `MoneroWalletPresenter` / `MoneroWalletSettingsPresenter`. Update this to your real Monero node before production.

### Build Status
- **Build Command**: `./gradlew :app:assembleFdroidDebug -x lint -x test --no-daemon`
- **Build Result**: `BUILD SUCCESSFUL` (12m 20s, 3839 tasks)
- **minSdk**: 26 (required by `monero-wallet-sdk`)
- **APK Output**: `outputs/APK/PRISM-v1.0.0-rc-fdroid-debug.apk` (universal, ~373 MB)
- **License Note**: `monero-wallet-sdk` is GPL-3.0. `app/build.gradle.kts` `licensee` block includes `allow("GPL-3.0")` and `allowUrl("https://www.gnu.org/licenses/gpl-3.0.txt")`.

---
*Updated by AI agent on 2026-05-27*
