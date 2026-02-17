# CrewLog iOS — App Store Submission Checklist

## Apple Review Compliance (Guideline 3.1.3(b))

### Why CrewLog qualifies as a multi-platform SaaS app

CrewLog is a **multi-platform SaaS application** that meets Apple's Guideline 3.1.3(b) criteria:

1. **Available on multiple platforms**: CrewLog is primarily a web application accessible at https://crewlog.app via any modern browser. The iOS app is a native wrapper providing enhanced mobile access to the same service.

2. **Subscriptions purchased outside the app**: All subscription management (upgrade, downgrade, cancellation) occurs exclusively through the CrewLog website. No in-app purchase mechanism exists within the iOS app.

3. **No purchase prompts in iOS app**: The iOS app does not display upgrade buttons, checkout flows, or any payment-related UI. Users who wish to upgrade must do so via the website.

4. **Full functionality for subscribers**: Users who have already subscribed via the website can log in to the iOS app and access all premium features immediately.

5. **Free tier available**: The app provides a functional free tier (1 active trip, up to 4 crew members) without requiring any purchase.

### What the iOS app does NOT contain

- No "Upgrade" or "Subscribe" buttons
- No checkout forms or payment flows
- No Stripe branding or payment references
- No external links directing users to purchase pages
- No price information or plan comparison

### What the iOS app DOES contain

- Login/logout functionality
- Full logbook entry creation with GPS integration
- Expense tracking and settlement calculations
- Crew management
- Trip management (within plan limits)
- PDF export
- Camera integration for receipts/photos
- A neutral note: "Subscriptions are managed via our website" (no link)

---

## Test Credentials for Apple Review

Provide these to Apple during submission:

| Field | Value |
|-------|-------|
| **Login URL** | (app opens to login screen) |
| **Email** | _(create a dedicated test account)_ |
| **Password** | _(set a review password)_ |
| **Subscription Status** | SKIPPER_PLUS (active) |

### Steps for Apple Reviewer

1. Open the app — login screen appears
2. Enter the provided test credentials
3. After login, the dashboard shows active trips
4. Navigate to any trip to see logbook, expenses, crew, settlements
5. Create a new logbook entry — GPS prompt appears (grant permission)
6. Add an expense — camera prompt appears for receipt (grant permission)
7. Navigate to Billing page — only shows current plan status and a note that subscriptions are managed via the website
8. No payment buttons or upgrade prompts are visible

---

## App Information

| Field | Value |
|-------|-------|
| **Bundle ID** | `app.crewlog.mobile` |
| **App Name** | CrewLog |
| **Version** | 1.0.0 |
| **Build** | 1 |
| **Category** | Navigation / Productivity |
| **Age Rating** | 4+ |
| **Content Rights** | No third-party content |

---

## Versioning Strategy

- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - MAJOR: Breaking changes or major feature releases
  - MINOR: New features, enhancements
  - PATCH: Bug fixes, small improvements
- **Build Number**: Incrementing integer, reset not required between versions
- **Initial Release**: Version 1.0.0, Build 1

---

## Required Permissions

| Permission | Usage Description | Required |
|------------|-------------------|----------|
| Location (When In Use) | Records GPS position for maritime logbook entries | Yes |
| Camera | Photographs receipts and logbook documentation | Yes |
| Photo Library | Attaches images to logbook entries and expenses | Yes |
| Background Location | Not used | No |
| Bluetooth | Not used | No |
| Tracking (ATT) | Not used — no user tracking | No |

---

## App Transport Security

- All connections use HTTPS exclusively
- `NSAllowsArbitraryLoads` is set to `false`
- Server URL: `https://crewlog.app` (HTTPS only)
- No cleartext HTTP traffic permitted

---

## Privacy & Legal

- Privacy Policy page: `/privacy` (accessible in-app and via footer link)
- Terms of Service page: `/terms` (accessible in-app and via footer link)
- Both pages open in Safari (SFSafariViewController) when tapped in the iOS app
- No user data is sold or shared with third parties
- `ITSAppUsesNonExemptEncryption`: `false` (standard HTTPS only)

---

## Pre-Submission Checklist

- [ ] Create dedicated Apple review test account with SKIPPER_PLUS subscription
- [ ] Verify all upgrade/checkout UI is hidden in iOS app
- [ ] Verify "Subscriptions managed via website" note displays on billing page
- [ ] Verify Privacy Policy and Terms links open in Safari
- [ ] Verify no Stripe branding visible anywhere in iOS app
- [ ] Verify GPS permission prompt has clear maritime logbook explanation
- [ ] Verify camera permission prompt has clear receipt/documentation explanation
- [ ] Test login/logout flow
- [ ] Test logbook entry creation with GPS
- [ ] Test expense creation with receipt photo
- [ ] Verify ATS — no HTTP connections
- [ ] Set correct Bundle ID in Xcode
- [ ] Set version 1.0.0 and build 1 in Xcode
- [ ] Add app icon assets (1024x1024 for App Store, plus all required sizes)
- [ ] Write App Store description emphasizing multi-platform SaaS nature
- [ ] Prepare screenshots for required device sizes
- [ ] Submit for review with demo account credentials
