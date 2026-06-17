# PRISM Update Workflow

This document outlines the standard workflow for applying updates to the PRISM project.

## Backend Update Process (RPi 4)

To update the Matrix server, bridges, or database configuration:

1.  Modify files in the `Backend/` directory locally.
2.  Run the update tool:
    ```powershell
    python tools/update_server.py
    ```
    *Note: This script archives the Backend folder, uploads it via SSH, and runs `setup-prism.sh` and `docker compose` on the RPi 4. It also automatically configures E2EE support for bridges.*

## Monero Node Update Process (HP Laptop)

The Monero node is hosted on a separate HP Elitebook laptop to offload heavy processing.

1.  Access the HP Laptop via SSH (`100.77.114.31`).
2.  Navigate to `prism-monero/`.
3.  Modify `docker-compose.yml` if needed.
4.  Restart services:
    ```bash
    docker-compose up -d
    ```

## Mobile App Update Process

1.  Make source code changes in `Frontend/app/src/main/java/`.
2.  Update version info in `Frontend/app/build.gradle` (Current: 1.0.0).
3.  Generate the APK:
    ```powershell
    python tools/build_apk.py
    ```
4.  Test the APK from `outputs/APK/`.

## Post-Update Verification

Always run the multi-server health check after any change:
```powershell
python tools/check_server.py
```

### Expected Output
- [✓] RPi Containers (Synapse, DB, WhatsApp)
- [✓] Synapse API (HTTP 200)
- [✓] HP Containers (Monero Node)
- [✓] Monero RPC (Sync Height)
