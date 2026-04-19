# CrewLog iOS App — Capacitor Wrapper

## Overview

This folder contains a Capacitor-based iOS wrapper that loads the production CrewLog web application inside a native iOS WebView. It provides native access to GPS, camera, and photo library while ensuring Stripe checkout/billing flows open in an external browser (SFSafariViewController).

## Prerequisites

- **macOS** with **Xcode 15+** installed
- **Node.js 18+** and npm
- An Apple Developer account (Individual or Organization)
- CocoaPods (`sudo gem install cocoapods`)

---

## Quick Start

```bash
cd ios_app

# 1. Install npm dependencies
npm install

# 2. Add iOS platform (first time only)
npx cap add ios

# 3. Sync web assets + native config to Xcode project
npx cap sync ios

# 4. Open in Xcode
npx cap open ios
```

---

## Detailed TestFlight Build Steps

### Step 1: Install Dependencies

> Note: when biometric login support was added, two plugins were appended to `package.json` (`@aparajita/capacitor-biometric-auth`, `@aparajita/capacitor-secure-storage`). Run `npm install` (not `npm ci`) on the next pull so the lockfile picks them up, then commit the regenerated `package-lock.json`.

```bash
cd ios_app
npm install
```

### Step 2: Add iOS Platform (first time only)

```bash
npx cap add ios
```

This creates the `ios/` directory with the native Xcode project.

### Step 3: Sync Configuration

```bash
npx cap sync ios
```

This copies `capacitor.config.ts` settings and plugin configurations into the native project. Run this every time you update `capacitor.config.ts` or install new Capacitor plugins.

### Step 4: Open in Xcode

```bash
npx cap open ios
```

### Step 5: Configure Signing & Capabilities

In Xcode:
1. Select the **App** target in the left sidebar
2. Go to **Signing & Capabilities** tab
3. Set **Team** to your Apple Developer team
4. Check **Automatically manage signing**
5. Set **Bundle Identifier** to `app.crewlog.mobile` (or your registered bundle ID)

### Step 6: Set Version & Build Number

In Xcode:
1. Select the **App** target
2. Go to **General** tab
3. Under **Identity**:
   - **Version**: `1.0.0` (semantic: MAJOR.MINOR.PATCH)
   - **Build**: `1` (increment for each TestFlight upload)

### Step 7: Configure Info.plist

In `ios/App/App/Info.plist`, add the entries from `ios-plist-additions.xml`:
- `NSLocationWhenInUseUsageDescription` — GPS for logbook entries
- `NSCameraUsageDescription` — Receipt and logbook photos
- `NSPhotoLibraryUsageDescription` — Attach existing photos
- `NSPhotoLibraryAddUsageDescription` — Save exported documents
- `NSAppTransportSecurity` — Enforce HTTPS only
- `ITSAppUsesNonExemptEncryption` — Set to `false` (standard HTTPS only)

### Step 8: Configure Associated Domains (Universal Links)

In Xcode:
1. Select the **App** target
2. Go to **Signing & Capabilities** tab
3. Click **+ Capability**
4. Add **Associated Domains**
5. Add: `applinks:crewlog.app`

The web server serves `/.well-known/apple-app-site-association` automatically. After deployment, replace `TEAMID` in the AASA response with your actual Apple Team ID.

### Step 9: Archive & Upload to TestFlight

1. In Xcode, select **Product > Scheme > App**
2. Set build target to **Any iOS Device (arm64)**
3. Select **Product > Archive**
4. Once archived, the **Organizer** window opens
5. Click **Distribute App**
6. Choose **App Store Connect** > **Upload**
7. Follow prompts (bitcode, symbols, etc.)
8. Wait for processing in App Store Connect (~15-30 min)

### Step 10: TestFlight Distribution

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Select your app
3. Go to **TestFlight** tab
4. Add internal testers or create an external test group
5. Add build to the test group
6. Testers receive a notification to install via TestFlight app

---

## How It Works

### Remote Web App Loading
The app does NOT bundle web assets. It loads the live CrewLog site via `server.url` in `capacitor.config.ts`:
- Instant updates when the web app changes
- No build pipeline duplication
- Requires internet connectivity

### App Store Compliance (Guideline 3.1.3b)
The bridge script (`capacitor-bridge.js`) automatically:
- Sets `window.IS_NATIVE_IOS = true`
- Hides all upgrade/checkout/payment UI in the native app
- Shows a neutral "Subscriptions managed via website" note
- Opens legal pages (Privacy, Terms) in Safari

No Stripe branding or payment UI is visible in the iOS app.

### Stripe External Browser
Any Stripe URLs that might be reached are intercepted and opened in SFSafariViewController via the Browser plugin.

### Session Stability
On app resume (foreground), the bridge calls `/api/whoami` to check session validity. If the session has expired, the user is redirected to the login screen.

### Offline Handling
If the device loses connectivity, a full-screen offline overlay appears with a retry button. The overlay automatically dismisses when connectivity returns.

### Universal Links (Return-to-App)
After completing an external browser action (e.g., Stripe payment on the website), the `/ios/return` page provides a "Return to CrewLog" button that opens the app via its URL scheme (`crewlog://return`).

### Native Capabilities
- **GPS/Geolocation**: Logbook Quick Fill for position recording
- **Camera**: Attach photos to logbook entries and expense receipts
- **Photo Library**: Select existing photos for attachments
- **App Plugin**: Version info, app state change detection
- **Face ID / Touch ID**: Biometric login for SaaS accounts. After a successful email/password login the user is offered to save the credentials to the iOS Keychain (via `@aparajita/capacitor-secure-storage`). On subsequent visits to `/login`, the bridge probes `@aparajita/capacitor-biometric-auth`; if a biometric is enrolled and credentials are stored, a "Sign in with Face ID" button appears, prompts the user via `LocalAuthentication`, retrieves the credentials from the Keychain, and submits them to `/login-saas`. Credentials are cleared automatically if the saved password no longer works, and the user can clear them manually from the login screen.

---

## iOS Permissions (Info.plist)

| Key | Description |
|-----|-------------|
| `NSLocationWhenInUseUsageDescription` | Records GPS position for maritime logbook entries |
| `NSCameraUsageDescription` | Photographs receipts and logbook documentation |
| `NSPhotoLibraryUsageDescription` | Attaches images to logbook entries and expenses |
| `NSPhotoLibraryAddUsageDescription` | Saves exported documents to photo library |
| `NSFaceIDUsageDescription` | Enables Face ID / Touch ID for biometric sign-in |

No background location, Bluetooth, or tracking permissions are requested.

---

## Universal Links Setup

### Server-side (already configured)
The web app serves `/.well-known/apple-app-site-association` at the correct path. After deployment:
1. Edit the AASA route in `main.py` to replace `TEAMID` with your actual Apple Team ID
2. Verify: `curl https://crewlog.app/.well-known/apple-app-site-association`

### Xcode-side
1. Add **Associated Domains** capability
2. Add domain: `applinks:crewlog.app`

### Testing Universal Links
1. Build and install the app on a device (not simulator)
2. Open Safari and navigate to `https://crewlog.app/ios/return`
3. The page should offer to open in CrewLog app
4. Long-press the link to see "Open in CrewLog" option

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CREWLOG_WEB_URL` | `https://crewlog.app` | Production URL loaded by the app |
| `APP_BASE_URL` | `https://crewlog.app` | Fallback URL |

---

## Versioning Strategy

- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - MAJOR: Breaking changes or major feature releases
  - MINOR: New features, enhancements
  - PATCH: Bug fixes, small improvements
- **Build Number**: Incrementing integer per TestFlight upload
- **Initial Release**: Version 1.0.0, Build 1
- Set in Xcode under General > Identity

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| White screen on launch | Check internet connectivity; verify server URL is reachable |
| GPS not working | Verify location permission granted in iOS Settings |
| Camera not available | Check camera permission in iOS Settings |
| Session lost after background | Expected if >24h elapsed; app auto-redirects to login |
| Offline overlay stuck | Check if server is accessible; try force-quitting app |
| Universal Links not working | Ensure Associated Domains configured; test on device (not simulator) |
| Archive fails | Ensure signing is configured; check Xcode build logs |
| TestFlight upload fails | Increment build number; check for missing icons or provisioning issues |

---

## File Structure

```
ios_app/
├── package.json              # npm deps (Capacitor core + plugins)
├── capacitor.config.ts       # Capacitor configuration
├── capacitor-bridge.js       # iOS-specific JS bridge (payment hiding, session, offline)
├── tsconfig.json             # TypeScript config
├── public/
│   └── index.html            # Minimal stub (required by Capacitor webDir)
├── ios-plist-additions.xml   # Info.plist entries to add
├── APP_STORE_CHECKLIST.md    # Apple review compliance guide
├── APP_STORE_ASSETS.md       # Screenshots, metadata, descriptions
├── README_IOS.md             # This file
└── ios/                      # Generated by `npx cap add ios` (gitignored)
```

---

## Related Documentation

- [APP_STORE_CHECKLIST.md](./APP_STORE_CHECKLIST.md) — Apple review compliance & Stripe policy
- [APP_STORE_ASSETS.md](./APP_STORE_ASSETS.md) — Screenshots, descriptions, metadata
- [Capacitor Documentation](https://capacitorjs.com/docs)
- [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
