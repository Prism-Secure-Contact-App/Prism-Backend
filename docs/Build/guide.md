# PRISM Build & Infrastructure Guide

This guide explains how to build the PRISM mobile application and manage the backend infrastructure.

## 1. Multi-Server Infrastructure

PRISM uses a distributed backend architecture to optimize performance and resource usage.

### Server 1: Raspberry Pi 4 (Main Backend)
- **Role**: Core messaging services and bridges.
- **IP**: `100.125.63.77`
- **Services**:
  - **Matrix Synapse**: The primary communication server.
  - **PostgreSQL**: Database for messaging and user data.
  - **WhatsApp Bridge**: Integration with WhatsApp.
  - **Meta Bridge**: Integration with Instagram/Meta.
  - **Cloudflare Tunnel**: Secure remote access.

### Server 2: HP Elitebook G8 (Node Server)
- **Role**: Resource-intensive blockchain nodes.
- **IP**: `100.77.114.31`
- **Services**:
  - **Monero Node (monerod)**: Full blockchain node for private transactions.

## 2. Infrastructure Management Tools

Use the following Python tools in the `tools/` directory to manage the system:

| Tool | Description |
| :--- | :--- |
| `update_server.py` | Deploys backend updates to the RPi 4. |
| `check_server.py` | Health check for BOTH servers (RPi 4 and HP Laptop). |

## 3. Building the Mobile App (APK)

The mobile client is built directly from `Frontend_Source/` using Gradle. The previous workaround (`build_apk.py` re-signing a base APK) is **deprecated and removed** — it produced byte-identical APKs and made true releases impossible.

### Prerequisites

| Component | Path / Version |
| :--- | :--- |
| JDK 21 (Temurin) | `C:\AMDDesignTools\.xinstall\2025.2\tps\win64\jre21.0.5_11` |
| Android SDK | `tools/android/sdk` (referenced from `Frontend_Source/local.properties`) |
| Android Build-Tools | `34.0.0` |
| Compile/Target SDK | `36` |
| Gradle | `9.2.1` (auto-downloaded by wrapper) |

### Flavors and which one to ship

The Gradle project produces TWO product flavors per build type:

| Flavor | Push provider | Google libs | Size (universal) | Use case |
| :--- | :--- | :--- | :--- | :--- |
| `gplay` | Firebase Cloud Messaging | Required (`google-services.json`) | ~350 MB | Play Store distribution. Needs a real Firebase project to avoid `Unable to register pusher, Firebase token is not known.` |
| **`fdroid`** ✅ | UnifiedPush | None | ~150 MB | **Canonical PRISM v1.0.0 distribution.** No Google libs, no FCM dependency, smaller APK. |

PRISM ships the **fdroid** flavor by default because (a) we are not yet on Play Store, (b) we have no production Firebase project, (c) UnifiedPush is the privacy-respecting choice that aligns with the AGPL fork's spirit. Push notifications require the user to install a UnifiedPush distributor (e.g., NTFY) — without one, the app still works but does not receive background push.

### Build command (canonical)

```powershell
cd Frontend_Source
$env:JAVA_HOME="C:\AMDDesignTools\.xinstall\2025.2\tps\win64\jre21.0.5_11"
$env:PATH="$env:JAVA_HOME\bin;$env:PATH"
./gradlew.bat :app:assembleFdroidDebug -x lint -x test --no-daemon --parallel
```

Output: `Frontend_Source/app/build/outputs/apk/fdroid/debug/`. Five APKs are produced — one per ABI plus a `universal` build. Always ship the **`app-fdroid-universal-debug.apk`** for distribution.

```powershell
Copy-Item Frontend_Source/app/build/outputs/apk/fdroid/debug/app-fdroid-universal-debug.apk outputs/APK/prism-v1.0.0.apk
```

The `outputs/APK/` directory must hold **exactly one file**: `prism-v1.0.0.apk`. Do not keep flavor-suffixed copies (`-fdroid.apk`, `-gplay.apk`) — they cause confusion when handing the APK to testers.

### APK size — what's normal and what's not

The build emits five APKs per flavor, one per ABI plus a **universal** that bundles every native lib slice:

| File | Approx. size | Use |
| :--- | :--- | :--- |
| `app-fdroid-universal-debug.apk` | **~375 MB** | **Canonical distribution.** Works on every Android phone (arm64, armv7, x86, x86_64). |
| `app-fdroid-arm64-v8a-debug.apk` | ~150 MB | 64-bit ARM only. Almost every phone made after 2017. |
| `app-fdroid-arm64-v8a-debug.apk` | ~150 MB | 64-bit ARM only. Almost every phone made after 2017 — but installing this on an armv7 / x86 device fails. Do **not** treat as the canonical APK. |
| `app-fdroid-armeabi-v7a-debug.apk` | ~125 MB | 32-bit ARM only. |
| `app-fdroid-x86-debug.apk` | ~160 MB | x86 emulator slice. |
| `app-fdroid-x86_64-debug.apk` | ~158 MB | x86_64 emulator slice. |

The fdroid vs gplay difference is small (~1 MB) — gplay only adds Firebase + Google Play Services bindings. The big swing comes from `universal` (all ABIs) vs single-arch.

If you ever see a ~150 MB file in `outputs/APK/`, somebody accidentally copied the arm64 single-arch artifact. The canonical distribution APK is **always** the universal one (~375 MB).

### Memory Requirements

Element X is a 100+ module project. On 8 GB systems use the tuned settings already in `Frontend_Source/gradle.properties`:

```properties
org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8 -XX:+UseG1GC -XX:MaxMetaspaceSize=1g
kotlin.daemon.jvm.options=-Xmx2048m -XX:+UseG1GC
org.gradle.workers.max=1
```

A clean first build downloads several GB of dependencies and takes 30–60 min. Incremental rebuilds are 3–15 min.

### minSdk Note

`monero-wallet-sdk` requires **API 26+** (Android 8.0). PRISM's `minSdk` is therefore set to `26` for FOSS builds. This excludes Android 7.x devices (API 24–25), which represent < 3 % of the active Android install base as of 2026.

## 4. Monitoring Health

Run the health check regularly to ensure all services are operational:
```powershell
python tools/check_server.py
```

## 5. Maintenance for Future Agents

- **Monero Setup**: If the HP laptop's Monero node needs to be re-initialized, refer to `tools/setup_remote_monero.py`. See `docs/Tools/README.md` for the full tool catalogue.
- **IP Changes**: Update `tools/check_server.py` and `docs/Environment/credentials.md` if server IPs change in the Tailscale network.
- **Build Issues**: See `docs/Build/agent_notes.md` for the catalog of half-renamed references and other gotchas discovered during the v1.0.0 baseline restoration.
