# WAGMI CrewLog - Maritime Logbook & Bordkasse

### Overview
WAGMI CrewLog is a comprehensive maritime logbook and expense tracking application designed for sailing crew members. It integrates professional logbook entries with GPS and weather data, alongside expense management (Bordkasse) and automated settlement calculations. The application supports secure authentication, manages up to 12 crew members, tracks deposits and expenses with flexible splitting, and calculates optimized settlement transfers. Key features include compliance with maritime logbook standards, multi-currency support with automatic conversion, Progressive Web App (PWA) capabilities, and professional PDF export for trip documentation.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Dual-mode session-based auth — legacy (admin/trip_admin/crew roles) and SaaS (email/password via `new_users` table with account scoping). Uses `werkzeug.security` for password hashing.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX. All router templates use shared `create_templates()` factory from `template_helpers.py` for consistent context processors.
**Internationalization (i18n)**: Session-based i18n with German (default) and English. `i18n.py` provides `get_lang()`, `set_lang()`, and `t()` helpers. Translations stored in `locales/de.json` and `locales/en.json` (flat key-value, 920 synchronized keys). Language detection: query param `?lang=` > session > Accept-Language header > default `de`. Fallback chain: selected language > German > raw key. `t()` function injected into all Jinja templates via context processor. Language switch UI in navbar (DE|EN links). Endpoint: `GET/POST /set-language` with HTMX support (HX-Redirect). **Full translation coverage**: All 25 templates migrated including help guide, logbook form (with JS i18n for GPS/weather alerts), billing, admin, crew, expenses, deposits, settlements, export, and navigation. Database-stored option values (sail plans, event categories, visibility) keep German `value` attributes for data integrity; display text is translated via conditional `t()` calls. JavaScript strings use a Jinja-populated `const i18n = {...}` object pattern for client-side translation.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Modular Router Structure**: Enhances maintainability and separation of concerns.
- **Role-Based Authentication**: Robust, role-based security with environment variable-based secrets and scoped permissions for Trip admins.
- **SaaS Multi-Tenancy**: Account-based tenant isolation via `account_id` on trips. `auth_saas.py` provides session guards (`get_current_saas_user`, `require_trip_access`, `require_trip_edit`), plan gating (`get_effective_plan`, `enforce_free_limits_*`), and account scoping (`get_active_account_id`). SaaS endpoints: `POST /login-saas`, `GET /api/whoami`, `POST /logout-saas`, `POST /admin/saas/backfill`. Legacy login remains intact; SaaS session takes precedence when present.
- **File Upload Security**: Enforces UUID-based filenames, type validation (PDF/JPG/PNG), and size limits (10MB).
- **Trip Management**: `Trip` model organizes all data, supporting active/archived/closed states, with all data scoped to a specific trip.
- **Multi-Currency Support**: Integrates with the ECB API for daily exchange rates, with caching.
- **Performance Optimization**: Addresses N+1 query problems through pre-aggregation, eager loading, and database indexes.
- **Settlement Groups**: Allows combining crew members for simplified settlement transfers.
- **Logbook System**: Comprehensive logbook entry with over 20 fields (navigation, weather, engine, events), including append-only compliance. Supports quick entry system with maneuver types and hybrid dropdown/manual input fields. **Language-neutral storage**: Wind strength (bft0-12), visibility (very_good/good/moderate/poor/very_poor), sail plan (motor_none/mainsail/genoa/main_genoa/no_sails), and event_category (maneuver/weather_change/sighting/repair/emergency/other) use canonical English keys in DB. `constants/logbook_enums.py` provides normalize_* functions (applied on save) for backward-compatible migration of legacy German values, and display_* functions (applied at render time) for i18n-translated display including `display_sea_state()` and `display_event_category()`. PDF export uses German locale via `_pdf_t()` helper.
- **Expense Category i18n**: Expense categories use language-neutral codes (provisions/beverages/mooring/diesel/water/electricity/gas/taxi_transfer/restaurant/admissions/other) stored in DB. `constants/expense_enums.py` provides `normalize_expense_category()` (accepts canonical codes, German legacy labels, English labels) and `display_expense_category()` for i18n display. Template helpers `display_expense_cat` and `norm_expense_cat` available in all Jinja templates. CSV/PDF exports render localized category labels. ExpenseTemplate category field also normalized.
- **GPS Integration**: Enhanced GPS auto-pull for latitude, longitude, Speed Over Ground (SOG), and Course Over Ground (COG), with continuous foreground GPS tracking.
- **Weather API Integration**: Open-Meteo API integration for automatic weather data retrieval (temperature, wind, pressure).
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime from on/off timestamps.
- **PDF Export**: ReportLab-based PDF generation for single entries and daily summaries, adhering to German/European official logbook standards.
- **Crew Departure Handling**: Settlement calculations correctly account for crew members departing mid-trip.
- **Timezone Handling**: All datetime fields are normalized to UTC, with client-side conversion for accurate display.
- **Solo-Sailing Workflow**: "Solo-Sailing" checkbox streamlines trip creation by automatically assigning the user as skipper and admin, utilizing `UserPreferences` for default information.
- **Stripe Subscription Billing**: `billing_stripe.py` provides helpers for Stripe customer/subscription management. `routes_billing.py` handles checkout (`POST /billing/checkout`), portal (`POST /billing/portal`), success/cancel pages, and webhook (`POST /stripe/webhook`) with signature verification. Webhook updates `subscriptions` table idempotently for plan gating. Only account owners can manage billing. DB unique constraint enforces one active subscription per account. Webhook handler uses deterministic upsert (lookup by `stripe_subscription_id` first, then `account_id`) and stores `webhook_received_at` timestamp on every event. `reconcile_subscription_from_stripe()` allows manual Stripe state sync.
- **Billing UI**: `routes_billing_ui.py` provides in-product billing pages. `GET /billing` shows SaaS users their plan/status/renewal with upgrade (FREE) or manage (SKIPPER_PLUS) buttons, plus over-limit banners when FREE plan exceeds limits. Owner-only `POST /billing/ui/checkout` and `POST /billing/ui/portal` create Stripe sessions with HTMX redirect support. `GET /admin/billing` provides admin-only overview with Stripe health widget (active/past_due/canceled/stale webhook counts), filters, and per-account reconcile action. `GET /admin/billing/account/{id}` shows account detail with members, trip count, and reconcile button. `POST /admin/billing/reconcile/{account_id}` fetches live Stripe state and syncs DB.
- **Downgrade Handling**: `check_over_limit_state()` in `billing_stripe.py` computes over-limit state for FREE accounts (active trips > 1 or crew > 4). Non-destructive: no data deleted, only blocks new actions exceeding limits and shows guidance banners.
- **DB Hardening**: `subscriptions` table has UNIQUE constraint on `account_id` (one row per account), partial UNIQUE index on `stripe_subscription_id` (non-null), column defaults for plan (FREE) and status (CANCELED), and `webhook_received_at` timestamp column.

#### Data Model
**Core Entities**: CrewMember, Deposit, Expense, ExpenseParticipant, ExpenseTemplate, CrewGroup, CrewGroupMember, Receipt, Trip, AuditLog, LogbookEntry, LogbookPhoto, UserPreferences.

#### Settlement Algorithm
Uses a greedy matching algorithm to minimize transfers between debtors and creditors, including individual balance calculation, settlement group aggregation, and optimized transfer generation.

#### Security
- **CSRF Protection**: `FastAPI-CSRF-Jinja` middleware.
- **Rate Limiting**: `SlowAPI` for global and login-specific limits.
- **Session Security**: 24-hour timeout, SameSite=Lax, httponly flags.
- **Role-Based Authorization**: Server-side checks enforce permissions across all routes.
- **Audit Logging**: Tracks financial transactions.
- **Input Validation**: Pydantic schemas.
- **Environment Variables**: Secure storage for sensitive data.

#### Frontend Architecture
**Technology Stack**: Jinja2, Tailwind CSS (CDN), HTMX.
**Design Principles**:
- **Mobile-First Design**: Optimized for touch and responsiveness.
- **UI v1.2 Design System**: Calm, Apple-inspired marine design with `static/ui_v1.css` providing CSS custom properties for colors (--bg, --surface, --surface-2, --border, --text, --text-secondary, --muted, --accent, --accent-2, --accent-light, --warning, --success, --warn, --danger), typography (--font-sans system stack, --text-xs..--text-3xl scale, --lh-tight/normal/relaxed), spacing (--space-1..--space-10 on 4px grid), radius (--r-sm/md/lg/xl), and shadows (--shadow-sm/md/lg). Reusable component classes (.btn, .btn-primary/secondary/danger, .card, .kpi-card, .tag, .dash-tile, .dash-hero, .topbar, .nav-item, .footer-bar). Opt-in UI utility classes: .ui-container (responsive max-width + padding), .ui-section (vertical spacing), .ui-card, .ui-title, .ui-subtitle, .ui-muted, .ui-stack/.ui-stack-sm/.ui-stack-lg, .ui-row, .ui-divider. Dashboard cards use neutral white backgrounds with minimal accent (thin top border on KPI cards, no side borders). Icons muted (lower opacity, smaller size). Accent color from branding overrides --accent/--accent-2 only (not --navy-deep).
- **Desktop UI Refinement (Calm Maritime v3)**: Desktop-only (>=1024px) design system in `static/ui_desktop_skin.css`. Color variables: `--navy-shell` (#1E2F45), `--canvas-grey` (#F3F4F6), `--card-white`, `--text-primary` (#1F2937)/`--text-secondary` (#64748B)/`--text-on-navy` (#F8FAFC), `--accent-blue` (#2C6BED), semantic `--success-bg/text`, `--warning-bg/text`, `--danger-bg/text` using rgba tints. 68px topbar with premium navy feel and subtle 1px separator shadow, bottom-border active nav indicator (accent-blue 2px), unified card system (white/16px radius/0 6px 24px shadow), 44px form inputs with 10px radius and blue focus ring (#CBD5E1 border), clean table headers (no uppercase, soft grey bg), 12px radius buttons (primary=accent-blue, secondary=white+border, danger=#991B1B). `ui_navy_contrast_fix.css` guardrail with `.navy-shell` class ensures white text on navy header/footer with dropdown exclusions. All scoped inside desktop media query — mobile untouched. Service worker cache at v12.
- **Navigation**: Dual-mode responsive navigation. Desktop (>=1024px): horizontal nav in topbar with hover/click dropdowns, active route bottom-border highlight. Mobile (<1024px): hamburger opens off-canvas drawer sidebar (dark navy, 280px width, translateX animation) with collapsible sections, close-on-link, ESC key, focus trapping, scroll lock. `static/ui_nav.js` handles all drawer behavior and active route highlighting (both desktop .nav-active and mobile .drawer-link-active via JS pathname matching). All nav labels use i18n `t()` function.
- **Professional PDF Export**: Themed PDF outputs.
- **Responsive Dashboard**: Streamlined mobile navigation with a focus on quick logbook entry.

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

#### Frontend Libraries (CDN)
- **Tailwind CSS**: CSS framework.
- **HTMX**: Dynamic HTML.

#### Database
- **PostgreSQL**: Replit-managed (Neon-backed).

#### File Storage
- **Local filesystem**: For receipt uploads in `/uploads`.

#### iOS Native Wrapper
- **Capacitor**: `/ios_app` contains a Capacitor-based iOS wrapper that loads the production CrewLog web URL in a native WKWebView.
- **Plugins**: @capacitor/browser (Stripe external open), @capacitor/geolocation (GPS), @capacitor/camera (photo capture), @capacitor/app (lifecycle).
- **Stripe external browser**: `capacitor-bridge.js` intercepts Stripe checkout/portal URLs and opens them in SFSafariViewController via Browser plugin. Templates use `data-stripe-external="1"` attribute as hook.
- **iOS build**: Requires macOS + Xcode. Run `npx cap sync ios && npx cap open ios` from `/ios_app`. See `ios_app/README_IOS.md`.

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.
- **Open-Meteo API**: For weather data retrieval.
- **Stripe API**: For subscription billing (checkout, webhooks, billing portal).