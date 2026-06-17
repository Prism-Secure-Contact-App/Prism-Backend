# PRISM Project: AI Agent Instructions

## Project Overview
PRISM is a secure chatting application based on a rebrand of the **Matrix Element** ecosystem. 
- **Frontend**: Android (Kotlin/Java) decompiled from a debug build.
- **Backend**: Matrix Synapse server with WhatsApp and Meta (Instagram) bridges.

## Folder Structure
- `Backend/`: Server-side configuration, Synapse data, and deployment scripts.
- `Frontend/`: Decompiled source code and resources of the mobile app.
- `docs/`: Documentation, environment secrets, and security guidelines.
- `tools/`: Utility scripts (e.g., server update tool).

## Procedures for AI Agents
1.  **Backend Changes**: Always test changes locally or verify scripts before running `tools/update_server.py`.
2.  **Frontend Changes**: Mobile code is decompiled. When modifying, focus on `sources/im/vector/app` for logic and `resources/res/values` for branding.
3.  **Security**: Adhere to `docs/CyberSecurity/guidelines.md`. Never expose credentials.
4.  **Common Errors**: 
    - Don't touch the "Stocktrack" (Borsa) files if they appear; they belong to a separate project.
    - Ensure Docker is running on the remote server before deployment.

## Technical Debt / Progress
- [x] Code recovery from server and phone.
- [x] Environment and Documentation structure.
- [ ] Admin Panel (Yet to be developed).
- [ ] Working Gradle build for the decompiled Frontend.
