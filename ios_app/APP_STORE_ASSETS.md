# CrewLog iOS — App Store Assets & Metadata

## Required Screenshots

### iPhone Sizes (mandatory)
| Device | Resolution | Required |
|--------|-----------|----------|
| iPhone 6.9" (iPhone 16 Pro Max) | 1320 x 2868 | Yes |
| iPhone 6.7" (iPhone 15 Plus / 14 Pro Max) | 1290 x 2796 | Yes |
| iPhone 6.5" (iPhone 11 Pro Max / XS Max) | 1242 x 2688 | Yes |
| iPhone 5.5" (iPhone 8 Plus) | 1242 x 2208 | Yes |

### iPad Sizes (if supporting iPad)
| Device | Resolution | Required |
|--------|-----------|----------|
| iPad Pro 12.9" (6th gen) | 2048 x 2732 | Optional |
| iPad Pro 11" | 1668 x 2388 | Optional |

### Recommended Screenshots (5-10 per size)
1. **Login screen** — Clean, branded login
2. **Dashboard / Trip list** — Overview of trips
3. **Logbook entry** — GPS position + weather data
4. **Expense list** — Expense tracking overview
5. **Settlement / Balances** — Settlement calculations
6. **Crew management** — Crew member list
7. **PDF Export** — Professional report preview
8. **About screen** — App version info

---

## App Icon

| Size | Usage |
|------|-------|
| 1024 x 1024 | App Store listing (required) |
| 180 x 180 | iPhone (Retina) |
| 167 x 167 | iPad Pro |
| 152 x 152 | iPad |
| 120 x 120 | iPhone |
| 87 x 87 | Spotlight (iPhone Retina) |
| 80 x 80 | Spotlight (iPad) |
| 76 x 76 | iPad (non-Retina) |
| 60 x 60 | iPhone |
| 58 x 58 | Settings (iPhone Retina) |
| 40 x 40 | Spotlight |
| 29 x 29 | Settings |
| 20 x 20 | Notification |

Generate all sizes from the 1024x1024 source using:
```bash
npx @capacitor/assets generate --iconBackgroundColor '#1E2F45' --splashBackgroundColor '#1E2F45'
```

---

## App Store Description

### Short Description (EN)
Maritime logbook & crew expense tracker for sailing trips.

### Short Description (DE)
Digitales Bordbuch & Bordkasse für Segeltörns.

### Long Description (EN)
CrewLog is the essential companion for sailing crews. Manage your maritime logbook with GPS tracking and weather data, track shared expenses with automatic settlement calculations, and keep your crew organized — all in one app.

Features:
- Professional maritime logbook with GPS auto-fill
- Automatic weather data from your position
- Shared expense tracking (Bordkasse) with multi-currency support
- Smart settlement calculations to minimize transfers
- Crew management with role-based permissions
- PDF export for maritime documentation
- Multi-language support (English & German)
- Camera integration for receipts and logbook photos

CrewLog is a multi-platform service. Manage your subscription at crewlog.app.

### Long Description (DE)
CrewLog ist der unverzichtbare Begleiter für Segelcrews. Führen Sie Ihr digitales Bordbuch mit GPS-Tracking und Wetterdaten, verwalten Sie die Bordkasse mit automatischer Abrechnung und organisieren Sie Ihre Crew — alles in einer App.

Funktionen:
- Professionelles Bordbuch mit GPS-Autofill
- Automatische Wetterdaten von Ihrer Position
- Bordkasse mit Mehrwährungs-Unterstützung
- Intelligente Abrechnungsberechnung für minimale Überweisungen
- Crew-Verwaltung mit rollenbasierter Berechtigung
- PDF-Export für maritime Dokumentation
- Mehrsprachig (Deutsch & Englisch)
- Kamera-Integration für Belege und Bordbuch-Fotos

CrewLog ist ein Multi-Plattform-Service. Verwalten Sie Ihr Abonnement auf crewlog.app.

---

## Keywords

### English
sailing, logbook, maritime, crew, expenses, bordkasse, settlement, GPS, navigation, boat

### German
segeln, bordbuch, bordkasse, crew, ausgaben, abrechnung, GPS, navigation, boot, törn

---

## Privacy Questionnaire Notes

| Question | Answer |
|----------|--------|
| Do you collect data used to track users? | No |
| Do you collect data linked to the user's identity? | Yes — email (account), name (crew member) |
| Data types collected | Contact Info (email), Location (GPS when in use), Photos (user-initiated) |
| Is location used for tracking? | No — GPS only for maritime logbook position recording |
| Third-party analytics/tracking SDKs? | None |
| Advertising? | None |
| Is data shared with third parties? | No |

### Data Use Declarations
- **Location**: Used to record GPS coordinates in logbook entries. Only collected when user actively creates an entry and grants permission. Not used for tracking.
- **Camera/Photos**: Used to attach receipt photos and logbook documentation. User-initiated only.
- **Contact Info (Email)**: Used for account authentication only.

---

## App Review Notes Template

```
CrewLog is a multi-platform SaaS maritime logbook application available at https://crewlog.app.

This iOS app is a native companion that provides enhanced access with GPS and camera integration.

SUBSCRIPTIONS:
- Subscriptions are purchased and managed exclusively via our website (crewlog.app)
- No in-app purchase mechanism exists
- The app qualifies under Guideline 3.1.3(b) as a multi-platform SaaS service
- Free tier is fully functional (1 active trip, up to 4 crew)

TEST ACCOUNT:
- Email: [REVIEWER_EMAIL]
- Password: [REVIEWER_PASSWORD]
- Subscription: Skipper Plus (active)

TESTING STEPS:
1. Open app — login screen appears
2. Enter test credentials
3. After login, tap any trip to view logbook, expenses, crew
4. Create a logbook entry — GPS permission prompt appears
5. Add an expense — camera option available
6. Navigate to Billing — shows current plan status only (no purchase options)
7. Navigate to About — shows app version and diagnostics

PERMISSIONS USED:
- Location (When In Use): Maritime logbook GPS entries
- Camera: Receipt and logbook photos
- Photo Library: Attach existing photos

The app does NOT contain any payment UI, checkout buttons, or links to purchase subscriptions.
```

---

## Age Rating
- **4+** — No objectionable content
- No gambling, mature themes, or restricted content

## Category
- Primary: **Navigation**
- Secondary: **Productivity**

## Content Rights
- All content is original
- No third-party content requiring rights clearance
