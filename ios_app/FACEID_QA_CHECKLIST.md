# Face ID Sign-In — Manual QA Checklist

Biometric sign-in cannot be exercised in CI (Playwright/headless browsers cannot drive iOS LocalAuthentication). Use this list on a real iPhone with Face ID enrolled before each App Store submission, or after any change to `static/capacitor-bridge.js`, `templates/login.html`, or `routes_auth.py`.

**Test device prerequisites**
- Real iPhone with Face ID enrolled and working in Settings → Face ID & Passcode.
- CrewLog iOS build installed via TestFlight or Xcode (`npm run cap:open:ios`).
- A SaaS account (email + password) on the staging or production server.

## Checklist

1. **Cold launch, no saved credentials** — Open the app on the login screen. Confirm NO "Sign in with Face ID" button is visible (the legacy crew-login card is shown by default).
2. **Switch to email login** — Tap "Sign in with email & password". Enter valid SaaS credentials and submit.
3. **Enrollment prompt** — Immediately after login succeeds, a system confirm dialog appears asking "Securely save your sign-in on this device and use Face ID next time?". Tap **OK**.
4. **Successful redirect** — App navigates to `/trips/`. No errors shown.
5. **Force-quit the app** — Swipe it out of the app switcher.
6. **Re-launch on login screen** — The SaaS card is shown automatically (no manual switch needed) and a "Sign in with Face ID" button is visible above the email/password form. The button label says "Face ID" (not "biometrics" / "Touch ID").
7. **Tap the Face ID button** — A native Face ID prompt appears with the reason text "Authenticate to sign in to CrewLog." (or its German equivalent if app language is DE). Authenticate with your face.
8. **Successful biometric login** — App navigates to `/trips/` with no password ever re-entered.
9. **"Remove saved sign-in"** — On the login screen, tap "Remove saved sign-in" under the Face ID button, confirm. The Face ID block disappears. Force-quit and re-launch — Face ID button must NOT reappear.
10. **Stale-credentials wipe** — Re-enroll (steps 2–4). Then change the SaaS password from another browser. Force-quit, re-launch, tap Face ID, authenticate. The login should fail (server returns 401), the Face ID UI should disappear, and an error should appear in the email/password form. Re-launch once more — the Face ID button must NOT reappear (Keychain was cleared).
11. **Cancel biometric prompt** — Re-enroll. On next launch, tap Face ID, then dismiss the system prompt. The login screen should remain unchanged with no error toast — and the button must remain available for another attempt.
12. **Locale switch (DE ↔ EN)** — Re-enroll, switch the app language, and verify the Face ID button label and confirm-dialog copy are translated correctly.
