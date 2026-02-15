# WAGMI CrewLog - Maritime Logbook & Bordkasse

### Overview
WAGMI CrewLog is a comprehensive maritime logbook and expense tracking application designed for sailing crew members. It integrates professional logbook entries with GPS and weather data, alongside expense management (Bordkasse) and automated settlement calculations. The application supports secure authentication, manages up to 12 crew members, tracks deposits and expenses with flexible splitting, and calculates optimized settlement transfers. Key features include compliance with maritime logbook standards, multi-currency support with automatic conversion, Progressive Web App (PWA) capabilities, and professional PDF export for trip documentation.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Dual-mode session-based auth — legacy (admin/trip_admin/crew roles) and SaaS (email/password via `new_users` table with account scoping). Uses `werkzeug.security` for password hashing.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX.
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
- **Logbook System**: Comprehensive logbook entry with over 20 fields (navigation, weather, engine, events), including append-only compliance. Supports quick entry system with maneuver types and hybrid dropdown/manual input fields.
- **GPS Integration**: Enhanced GPS auto-pull for latitude, longitude, Speed Over Ground (SOG), and Course Over Ground (COG), with continuous foreground GPS tracking.
- **Weather API Integration**: Open-Meteo API integration for automatic weather data retrieval (temperature, wind, pressure).
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime from on/off timestamps.
- **PDF Export**: ReportLab-based PDF generation for single entries and daily summaries, adhering to German/European official logbook standards.
- **Crew Departure Handling**: Settlement calculations correctly account for crew members departing mid-trip.
- **Timezone Handling**: All datetime fields are normalized to UTC, with client-side conversion for accurate display.
- **Solo-Sailing Workflow**: "Solo-Sailing" checkbox streamlines trip creation by automatically assigning the user as skipper and admin, utilizing `UserPreferences` for default information.
- **Stripe Subscription Billing**: `billing_stripe.py` provides helpers for Stripe customer/subscription management. `routes_billing.py` handles checkout (`POST /billing/checkout`), portal (`POST /billing/portal`), success/cancel pages, and webhook (`POST /stripe/webhook`) with signature verification. Webhook updates `subscriptions` table idempotently for plan gating. Only account owners can manage billing. DB unique constraint enforces one active subscription per account.
- **Billing UI**: `routes_billing_ui.py` provides in-product billing pages. `GET /billing` shows SaaS users their plan/status/renewal with upgrade (FREE) or manage (SKIPPER_PLUS) buttons. Owner-only `POST /billing/ui/checkout` and `POST /billing/ui/portal` create Stripe sessions with HTMX redirect support. `GET /admin/billing` provides admin-only overview of all accounts with subscription state, filters, and Stripe IDs. `GET /admin/billing/account/{id}` shows account detail with members and trip count.

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
- **Maritime UI Theme**: Nautical aesthetic with custom colors and components.
- **Professional PDF Export**: Themed PDF outputs.
- **Responsive Dashboard**: Streamlined mobile navigation with a focus on quick logbook entry.
- **Navigation Restructuring**: Prioritizes quick access to Logbook alongside Törns; streamlined dropdowns for other actions.

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

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.
- **Open-Meteo API**: For weather data retrieval.
- **Stripe API**: For subscription billing (checkout, webhooks, billing portal).