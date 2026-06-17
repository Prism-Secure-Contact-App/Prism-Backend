# PRISM v1.0.0 Technical Plan

This document outlines the technical requirements and implementation strategy for the PRISM 1.0.0 release.

## 1. Authentication Flow Redesign

### Login
- **Target**: Single screen with Username and Password fields. The homeserver will be hardcoded to `matrix.fathertkt.uk` will not shown to user at anywhere in the app.
- **Implementation**: ✅ Completed — `LoginPasswordPresenter` calls `setHomeserver()` before login.

### Registration
- **Target**: Username, Password, and Password Confirmation.
- **Implementation**: ✅ Completed — `CreateAccountPresenter` + `SynapseRegisterClient` with direct Synapse POST.
- **Password Policy**: ✅ Client-side validation added — min 8 chars, upper/lower, digit, special char.

## 2. Post-Registration Onboarding (Wizard)

After successful registration and first login, the user will be presented with a setup wizard:

### Step 1: Session Verification
- ✅ Completed

### Step 2: Notifications Opt-in
- ✅ Completed

### Step 3: Lockscreen Setup
- ✅ Completed

### Step 4: WhatsApp Bridge
- **Action**: Ask the user if they want to integrate WhatsApp.
- **Explanation**: "WhatsApp Bridge allows you to send and receive WhatsApp messages directly within PRISM. Your chats will be synced securely. Also you can disable it anytime from settings."
- **Technical**: ✅ Completed — `BridgeSettingsPresenter` handles full connect/disconnect flow with bot DMs.

### Step 5: Monero (XMR) Wallet
- **Action**: Ask the user if they want a Monero wallet.
- **Explanation**: "Monero is a privacy-focused cryptocurrency. Having a wallet in PRISM allows you to make anonymous payments."
- **Technical**: ✅ UI skeleton completed — address, mnemonic, view/spend keys displayed. Real blockchain interaction deferred to v1.1 (requires native Monero library).

### Step 6: PrismAI Onboarding
- **Action**: Explain how to activate PrismAI via WhatsApp.
- **Explanation**: "Meta'ya WhatsApp'ından bir mesaj yaz, ardından o mesajı basılı tutup 'AI olarak işaretle' seçeneğine tıkla."
- **Technical**: ✅ Completed — FTUE popup added after Monero wallet step.

### Step 7: Analytics Opt-in
- ✅ Completed

## 3. Settings & Security

- ✅ **Developer Options**: Removed from v1.0.0 release build.
- ✅ **Cüzdan Güvenliği**: Monero wallet seed phrase backup in Settings.
- ✅ **LLM API**: API key generation, rotation, deletion in Settings.
- ✅ **Deep Work Modu**: Toggle in Settings with state persistence.
- ✅ **Session Rooms**: Auto-delete timer and screenshot protection in Create Room flow.
- ✅ **Password Policy**: Enforced during registration.

## 4. Admin & Backend

- ✅ **Admin Setup Script**: `Backend/setup_admin.py` creates admin from `.env` / `SYNAPSE_SHARED_SECRET`.

## 5. Removed Features

- ❌ **Instagram Bridge**: Completely removed from codebase.
- ❌ **Developer Options**: Hidden from end-user release.
- ❌ **TOTP/MFA**: Deferred per user request.
- ❌ **Local LLM**: Deferred per user request.

## 6. Build and Distribution

- **Output Path**: `outputs/APK/prism-v1.0.0.apk`
- **Method**: `./gradlew.bat :app:assembleFdroidDebug -x lint -x test`
- **Status**: ✅ Build successful, APK generated.

## 7. Technical Debt & Risks

| Item | Status | Note |
|------|--------|------|
| Monero Integration | ⚠️ UI ready, backend deferred | Needs native Monero library or RPC bridge |
| Session Rooms Zero Trace | ⚠️ Client ready, server deferred | Needs Synapse retention policy or custom bridge |
| Deep Work Theme | ⚠️ Toggle ready, theme deferred | Needs MainActivity + theme engine integration |
| LLM API Backend | ⚠️ Client ready, proxy deferred | Needs `llm_api_service.py` Docker integration |

---
*Updated by AI agent on 2026-05-21*
