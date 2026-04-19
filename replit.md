# WAGMI CrewLog - Maritime Logbook & Bordkasse

### Overview
WAGMI CrewLog is a comprehensive maritime logbook and expense tracking application for sailing crew members. It integrates professional logbook entries with GPS and weather data, expense management (Bordkasse), and automated settlement calculations. Key capabilities include secure authentication, multi-crew management, flexible expense splitting, optimized settlement transfers, compliance with maritime logbook standards, multi-currency support, Progressive Web App (PWA) features, and professional PDF export for trip documentation. The project aims to provide an essential tool for sailing crews, simplifying administrative tasks and enhancing trip management.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Dual-mode session-based authentication supporting legacy role-based access and SaaS email/password accounts with account scoping.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX.
**Internationalization (i18n)**: Session-based i18n with German (default) and English, using `locales/de.json` and `locales/en.json`. Language-neutral storage for database option values (e.g., wind strength, visibility, expense categories) with i18n applied at render time.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Modular Router Structure**: For maintainability and separation of concerns.
- **Role-Based and SaaS Multi-Tenancy**: Robust security with scoped permissions and account-based tenant isolation via `account_id` on trips.
- **File Upload Security**: Enforces UUID-based filenames, type validation, and size limits.
- **Trip Management**: Data organized by `Trip` model, supporting active/archived/closed states.
- **Multi-Currency Support**: Integration with ECB API for daily exchange rates with caching.
- **Performance Optimization**: Addresses N+1 query problems through pre-aggregation and eager loading.
- **Settlement Groups**: Allows combining crew members for simplified transfers.
- **Logbook System**: Comprehensive, append-only logbook entries with quick entry features and language-neutral storage for key data.
- **Expense Category i18n**: Uses language-neutral codes in the database, with localized display for users.
- **GPS Integration**: Enhanced auto-pull for navigation data and continuous foreground tracking.
- **Weather API Integration**: Automatic weather data retrieval via Open-Meteo API.
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime.
- **PDF Export**: ReportLab-based generation of PDF reports adhering to maritime standards.
- **Crew Departure Handling**: Correct settlement calculations for mid-trip departures.
- **Timezone Handling**: All datetime fields normalized to UTC with client-side conversion.
- **Solo-Sailing Workflow**: Streamlined trip creation for solo users.
- **Quick Start Trip (swap semantics)**: `POST /trips/quick-start` archives the currently active trip and creates a fresh one in a single transaction. The auto-archive runs *before* the free-plan limit check so a free-plan user (1 active trip max) can always swap. Archive + create share one DB transaction; on any failure the archive rolls back so the user is never left with zero active trips.
- **Stripe Subscription Billing**: Integration for customer/subscription management, checkout, billing portal, and webhook processing for plan gating and state synchronization. Non-destructive downgrade handling.
- **DB Hardening**: Unique constraints and robust defaults for critical tables.
- **Receipt OCR Pre-fill**: Anthropic Claude vision (`claude-sonnet-4-20250514`) reads uploaded receipt images/PDFs and pre-fills empty expense form fields (amount, currency, date, vendor, category, description). Endpoint `POST /expenses/ocr-suggest` is auth-gated, scoped to active trip, rate-limited (20/min/IP), 8 MB cap. Failures degrade silently and are audit-logged (`OCR_FAILED`). Suggestions are visually marked with a "Suggested" pill that clears on user edit; existing values are never overwritten.
- **Day Logbook (Batch Entry)**: `GET/POST /logbook/day-new` lets the skipper record many entries for one day in a single transactional submission. Frontend (`static/js/logbook-day-entry.js`) supports add/remove rows, monotonic time validation, and Quick Fill seeding for the first row; values carry forward to later rows when blank. Backend rolls back the whole batch on any per-row failure and additionally carries forward GPS lat/lon server-side for resilience.
- **Multi-Photo Upload**: `POST /logbook/{entry_id}/photos/upload` accepts `List[UploadFile]` so multiple photos can be added in one action. Hard cap of 10 files per upload (`MAX_PHOTOS_PER_UPLOAD`) plus per-file 10 MB / type checks; partial successes are surfaced via flash messages. After file selection, the UI renders thumbnail previews (`URL.createObjectURL`) plus a green "N selected" confirmation on both the Day Logbook form (`#dayPhotosPreview`) and the single-entry detail page (`#photoPreview`) so the user can verify what's about to be uploaded.
- **Day Logbook UI (mobile/tablet)**: Each row uses `items-end` grid alignment with a `min-height` on labels and inputs so wrapping labels (e.g. "Manöver-Typ (Quick Entry)") no longer stagger the field row. Move-up/down arrows are 40×40px iPhone-friendly touch targets and auto-disable on the first/last row via `renumber()` in `static/js/logbook-day-entry.js`. Drag handle removed in favor of the simpler arrow controls.
- **Trip Finalize**: `GET /trips/{trip_id}/finalize` shows a summary card (entries, distance, sail hours) with a confirmation checkbox. `POST /trips/{trip_id}/close` requires `confirm=yes`, admin/owner role, account scoping, and CSRF. After finalize, the trip shows a CLOSED badge and crew lose write access.
- **iOS Home/Lock Screen Widget**: WidgetKit extension shows the active trip at a glance. Backend exposes `POST /api/widget/token` (session+CSRF, issues new bearer + revokes prior), `DELETE /api/widget/token` (revoke all), `GET /api/widget/status` (enabled/issued/last-used), and `GET /api/widget/snapshot` (Bearer auth, returns `{v, state, trip:{id,name,day}, totals:{distance_nm,motor_hours}, last_entry:{at,position}}`). Tokens are 32-byte URL-safe random, stored as SHA-256 hashes in `widget_tokens`. The web `/about` page (SaaS sessions only) shows status, **Enable widget**, and **Revoke widget access** controls. The Capacitor bridge persists the plain token to the iOS Keychain (App Group `group.app.crewlog.mobile`) under `crewlog.widget.token` + `crewlog.widget.baseUrl`. Swift WidgetKit sources live in `ios_app/WidgetExtension/` (small + medium families, deep link `crewlog://logbook/today`); Xcode setup steps documented in `ios_app/README_IOS.md`.
- **Night Mode**: Red-on-black theme for night sailing, preserving dark adaptation. CSS-only overlay activated by `html[data-theme="night"]` (`static/ui_night_mode.css`). Toggle pill auto-injected into the desktop topbar and mobile drawer by `static/js/night-mode.js`. State persisted in `localStorage["crewlog-theme"]`. Inline early script in `templates/layout.html` and `templates/login.html` `<head>` applies the attribute before paint to prevent white flash. User-uploaded photos/receipts (`/uploads/`, `.photo-thumb img`, `.receipt-thumb img`) get a dim red filter; icons and SVGs inherit color. Service worker cache bumped to `crewlog-v20` and precaches the new CSS/JS.

#### Data Model
**Core Entities**: CrewMember, Deposit, Expense, ExpenseParticipant, ExpenseTemplate, CrewGroup, CrewGroupMember, Receipt, Trip, AuditLog, LogbookEntry, LogbookPhoto, UserPreferences, Subscriptions, PasswordResetToken.

#### Settlement Algorithm
A greedy matching algorithm minimizes transfers between debtors and creditors, supporting individual and group settlements.

#### Security
- **CSRF Protection**: `FastAPI-CSRF-Jinja` middleware.
- **Rate Limiting**: `SlowAPI` for global and login-specific limits.
- **Session Security**: Secure session configurations (timeout, SameSite, httponly).
- **Role-Based Authorization**: Server-side checks enforce permissions.
- **Password Reset**: Secure forgot/reset password flow for SaaS users via Resend email. Tokens are single-use, time-limited (60min), stored hashed (SHA-256). Rate-limited per IP. No user enumeration. Audit logged.
- **Audit Logging**: Tracks financial transactions and security events (PASSWORD_RESET_REQUEST, PASSWORD_RESET_SUCCESS).
- **Input Validation**: Pydantic schemas.
- **Environment Variables**: Secure storage for sensitive data.

#### Frontend Architecture
**Technology Stack**: Jinja2, Tailwind CSS (CDN), HTMX.
**Design Principles**:
- **Mobile-First Design**: Optimized for touch and responsiveness.
- **UI Design System**: Calm, Apple-inspired marine design with custom CSS properties for consistent styling (colors, typography, spacing, radius, shadows) and reusable component classes.
- **Desktop UI Refinement**: Dedicated desktop-only (`>=1024px`) design system with a premium navy aesthetic, unified card system, and refined form inputs.
- **Navigation**: Dual-mode responsive navigation with horizontal desktop nav and an off-canvas mobile drawer with i18n support.
- **Professional PDF Export**: Themed PDF outputs for reports.
- **Responsive Dashboard**: Streamlined mobile navigation for quick logbook entry.

### External Dependencies

#### Python Packages
- **FastAPI**: Web framework.
- **SQLAlchemy**: ORM.
- **psycopg2-binary**: PostgreSQL adapter.
- **Jinja2**: Template engine.
- **python-multipart**: File uploads.
- **python-dotenv**: Environment variables.
- **ReportLab**: PDF generation.
- **Alembic**: Database migrations.
- **fastapi-csrf-jinja**: CSRF protection.
- **slowapi**: Rate limiting.
- **werkzeug**: Password hashing.
- **stripe**: Stripe billing SDK.
- **resend**: Email delivery for password reset.

#### Frontend Libraries (CDN)
- **Tailwind CSS**: CSS framework.
- **HTMX**: Dynamic HTML.

#### Database
- **PostgreSQL**: Replit-managed (Neon-backed).

#### File Storage
- **Local filesystem**: For receipt uploads in `/uploads`.

#### iOS Native Wrapper
- **Capacitor**: Used for a Capacitor-based iOS wrapper loading the web app in a native WKWebView. Includes plugins for browser, geolocation, camera, and app lifecycle management. Handles Stripe external browser interactions and ensures App Store compliance by hiding billing UI on iOS.
- **Universal Links**: `/ios/return` route provides return-to-app flow after external browser actions. AASA served at `/.well-known/apple-app-site-association`. URL scheme: `crewlog://`.
- **About/Diagnostics**: `/about` page shows app version, session mode, account ID, language. In iOS, native version/build info from Capacitor App plugin. Accessible from Help in navigation.
- **Session Stability**: Bridge calls `/api/whoami` on app resume (foreground) to check session validity. Auto-redirects to login if session expired.
- **Biometric Login (Face ID / Touch ID)**: SaaS users on iOS can opt in to biometric sign-in. After a successful email/password login they are prompted to save credentials to the iOS Keychain via `@aparajita/capacitor-secure-storage`; on later visits to `/login`, `@aparajita/capacitor-biometric-auth` (LocalAuthentication) gates retrieval of those credentials and submits them to `/login-saas`. Stale credentials are cleared automatically and can be cleared manually from the login screen. Requires `NSFaceIDUsageDescription` in Info.plist.
- **Offline Handling**: Bridge shows full-screen offline overlay with retry button when device loses connectivity (iOS only).
- **Documentation**: `ios_app/README_IOS.md` (TestFlight build steps), `ios_app/APP_STORE_CHECKLIST.md` (Apple review compliance), `ios_app/APP_STORE_ASSETS.md` (screenshots, metadata, descriptions).

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.
- **Open-Meteo API**: For weather data retrieval.
- **Stripe API**: For subscription billing (checkout, webhooks, billing portal).