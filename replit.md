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
- **Stripe Subscription Billing**: Integration for customer/subscription management, checkout, billing portal, and webhook processing for plan gating and state synchronization. Non-destructive downgrade handling.
- **DB Hardening**: Unique constraints and robust defaults for critical tables.

#### Data Model
**Core Entities**: CrewMember, Deposit, Expense, ExpenseParticipant, ExpenseTemplate, CrewGroup, CrewGroupMember, Receipt, Trip, AuditLog, LogbookEntry, LogbookPhoto, UserPreferences, Subscriptions.

#### Settlement Algorithm
A greedy matching algorithm minimizes transfers between debtors and creditors, supporting individual and group settlements.

#### Security
- **CSRF Protection**: `FastAPI-CSRF-Jinja` middleware.
- **Rate Limiting**: `SlowAPI` for global and login-specific limits.
- **Session Security**: Secure session configurations (timeout, SameSite, httponly).
- **Role-Based Authorization**: Server-side checks enforce permissions.
- **Audit Logging**: Tracks financial transactions.
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
- **Offline Handling**: Bridge shows full-screen offline overlay with retry button when device loses connectivity (iOS only).
- **Documentation**: `ios_app/README_IOS.md` (TestFlight build steps), `ios_app/APP_STORE_CHECKLIST.md` (Apple review compliance), `ios_app/APP_STORE_ASSETS.md` (screenshots, metadata, descriptions).

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.
- **Open-Meteo API**: For weather data retrieval.
- **Stripe API**: For subscription billing (checkout, webhooks, billing portal).