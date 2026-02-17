# CrewLog iOS App — Capacitor Wrapper

## Overview

This folder contains a Capacitor-based iOS wrapper that loads the production CrewLog web application inside a native iOS WebView. It provides native access to GPS, camera, and photo library while ensuring Stripe checkout/billing flows open in an external browser (SFSafariViewController).

## Prerequisites

- **macOS** with **Xcode 15+** installed
- **Node.js 18+** and npm
- An Apple Developer account for App Store submission
- The production CrewLog URL set as an environment variable

## Required Environment Variable

Set `CREWLOG_WEB_URL` to your production CrewLog URL before syncing:

```bash
export CREWLOG_WEB_URL="https://crewlog.app"
```

If not set, the app falls back to `APP_BASE_URL` or `https://crewlog.app`.

## Setup & Build

```bash
# 1. Install dependencies
cd ios_app
npm install

# 2. Initialize Capacitor (first time only)
npx cap init CrewLog app.crewlog.mobile --web-dir public

# 3. Add iOS platform (first time only)
npx cap add ios

# 4. Sync configuration to iOS project
npx cap sync ios

# 5. Open in Xcode
npx cap open ios
```

## How It Works

### Remote Web App Loading
The app does NOT bundle web assets. Instead, it loads the live CrewLog site via `server.url` in `capacitor.config.ts`. This means:
- Instant updates when the web app changes
- No build pipeline duplication
- Requires internet connectivity

### Stripe External Browser
Stripe checkout and billing portal URLs are intercepted and opened in SFSafariViewController (via the Capacitor Browser plugin) instead of the internal WebView. This is required by Stripe's terms and ensures proper payment security.

The interception is handled by `capacitor-bridge.js`, which:
1. Intercepts `window.location.href` assignments to Stripe domains
2. Listens for HTMX `HX-Redirect` headers pointing to Stripe
3. Catches fetch responses containing `checkout_url` or `portal_url`
4. Opens matching URLs via `Browser.open()` in SFSafariViewController

To inject this script into the WebView, add it to the iOS project:
1. Copy `capacitor-bridge.js` to `ios/App/App/public/`
2. In `ios/App/App/capacitor.config.json`, the script is loaded via the web URL

Alternatively, configure the WKWebView to inject the script using a `WKUserScript` in `ios/App/App/AppDelegate.swift` or create a custom Capacitor plugin.

### Native Capabilities
- **GPS/Geolocation**: Used by logbook Quick Fill for position recording
- **Camera**: Attach photos to logbook entries and expense receipts
- **Photo Library**: Select existing photos for attachments

## iOS Permissions (Info.plist)

The following permission strings must be present in `ios/App/App/Info.plist`:

| Key | Description |
|-----|-------------|
| `NSLocationWhenInUseUsageDescription` | CrewLog uses your location to record GPS position for logbook entries. |
| `NSCameraUsageDescription` | CrewLog uses the camera to attach receipts and logbook photos. |
| `NSPhotoLibraryUsageDescription` | CrewLog accesses your photo library to attach images to entries and expenses. |
| `NSPhotoLibraryAddUsageDescription` | CrewLog saves photos to your library. |

See `ios-plist-additions.xml` for copy-paste ready entries.

## App Store Submission Notes

### Bundle ID
- Current placeholder: `app.crewlog.mobile`
- Change in `capacitor.config.ts` and Xcode project settings before submission

### Versioning
- Set version in Xcode: General > Version and Build
- Follow semantic versioning (1.0.0, 1.0.1, etc.)

### Signing
1. In Xcode, select your Team under Signing & Capabilities
2. Enable "Automatically manage signing"
3. Ensure your provisioning profile includes the correct bundle ID

### App Icons
- Source icons from `static/logo-crewlog-192.png` and `static/logo-crewlog-512.png`
- Generate the full iOS icon set using:
  ```bash
  npx @capacitor/assets generate --iconBackgroundColor '#1E2F45' --splashBackgroundColor '#1E2F45'
  ```
- Or manually create icons at all required sizes and place in `ios/App/App/Assets.xcassets/AppIcon.appiconset/`

### Privacy Manifest
Apple requires a privacy manifest for apps using certain APIs. Capacitor plugins handle their own manifests, but verify compliance before submission.

### App Review Notes
- The app loads a remote web URL — Apple allows this for "web-wrapper" apps IF the content provides sufficient native functionality (GPS, camera, etc.)
- Ensure the login flow works smoothly in the review environment
- Provide demo credentials in the App Review notes

## Session Cookie Compatibility

CrewLog uses session cookies with `SameSite=Lax` and `httponly` flags. Since the iOS WebView loads the same HTTPS domain, cookies are handled natively by WKWebView without any special configuration.

If cookie issues arise:
- Verify the app's URL scheme matches the production domain
- Check that cookies are not being blocked by iOS privacy settings
- `SameSite=Lax` should work correctly since the WebView and server share the same origin

## Troubleshooting

| Issue | Solution |
|-------|----------|
| White screen on launch | Check `CREWLOG_WEB_URL` is set correctly and the server is reachable |
| GPS not working | Verify location permission was granted in iOS Settings |
| Camera not available | Check camera permission in iOS Settings |
| Stripe checkout fails | Ensure `allowNavigation` includes all Stripe subdomains |
| Login session lost | Check cookie settings; ensure HTTPS is used |
