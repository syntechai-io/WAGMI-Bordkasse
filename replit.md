# WAGMI CrewLog - Maritime Logbook & Bordkasse

### Overview
WAGMI CrewLog is a comprehensive maritime logbook and expense tracking application designed for sailing crews. It integrates professional logbook entries with GPS and weather data, robust expense management (Bordkasse), and automated settlement calculations. The project's core purpose is to simplify administrative tasks for sailing crews, offering features like secure authentication, multi-crew management, flexible expense splitting, multi-currency support, PWA capabilities, and professional PDF export for trip documentation. It aims to be an essential tool for enhancing trip management and ensuring compliance with maritime logbook standards.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with a modular router structure for maintainability.
**Authentication**: Dual-mode session-based authentication supporting legacy role-based access and SaaS email/password accounts with account scoping.
**Template Engine**: Jinja2 for server-side rendering, enhanced with HTMX for dynamic interactions.
**Internationalization (i18n)**: Session-based i18n with German (default) and English. Database values for options (e.g., wind strength) are language-neutral, with i18n applied at render time.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Role-Based and SaaS Multi-Tenancy**: Robust security with scoped permissions and account-based tenant isolation.
- **File Upload Security**: Enforces UUID-based filenames, type validation, and size limits.
- **Trip Management**: Data organized by `Trip` model, supporting active, archived, and closed states.
- **Multi-Currency Support**: Integration with ECB API for daily exchange rates with caching.
- **Performance Optimization**: Addresses N+1 query problems through pre-aggregation and eager loading.
- **Settlement Groups**: Allows combining crew members for simplified transfers.
- **Logbook System**: Comprehensive, append-only entries with quick entry features.
- **GPS & Weather Integration**: Auto-pull for navigation data and continuous foreground tracking, and automatic weather data retrieval via Open-Meteo API.
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime.
- **PDF Export**: ReportLab-based generation of PDF reports adhering to maritime standards.
- **Crew Departure Handling**: Correct settlement calculations for mid-trip departures.
- **Timezone Handling**: All datetime fields normalized to UTC with client-side conversion.
- **Solo-Sailing Workflow**: Streamlined trip creation for solo users.
- **Quick Start Trip**: Archives the currently active trip and creates a fresh one in a single transaction, ensuring free-plan users can always swap.
- **Stripe Subscription Billing**: Integration for customer/subscription management, checkout, billing portal, and webhook processing for plan gating and state synchronization, including non-destructive downgrade handling.
- **DB Hardening**: Unique constraints and robust defaults for critical tables.
- **Receipt OCR Pre-fill**: Anthropic Claude vision reads uploaded receipt images/PDFs to pre-fill empty expense form fields, with suggestions visually marked.
- **Day Logbook (Batch Entry)**: Allows recording multiple entries for one day in a single transactional submission, with frontend support for row management and Quick Fill.
- **Multi-Photo Upload**: Supports uploading multiple photos simultaneously for logbook entries.
- **Day Logbook UI (mobile/tablet)**: Optimized UI for mobile and tablet with improved touch targets and layout.
- **Trip Finalize**: Provides a summary and confirmation process to close a trip, restricting write access for crew members.
- **iOS Home/Lock Screen Widget**: WidgetKit extension displays active trip information, with a backend API for secure token management and data snapshots.
- **Night Mode (Auto / Day / Night)**: A pure red-on-black theme for night sailing, activated by `html[data-theme="night"]` and controlled by a UI switch, with state persisting locally and optionally server-side. Critical Night CSS is inlined in the `<head>` of `layout.html` and `login.html` so the dark palette renders on first paint even before external stylesheets load. CSS link tags use `?v=28` cache-busters; `sw.js` uses a network-first strategy for `/static/*.css` so theme updates propagate on a single reload. A no-auth, no-cache `/diagnostics/theme?theme=night|light` page renders one of every UI primitive for instant visual smoke-testing.

#### Data Model
**Core Entities**: CrewMember, Deposit, Expense, ExpenseParticipant, ExpenseTemplate, CrewGroup, CrewGroupMember, Receipt, Trip, AuditLog, LogbookEntry, LogbookPhoto, UserPreferences, Subscriptions, PasswordResetToken.

#### Settlement Algorithm
A greedy matching algorithm minimizes transfers between debtors and creditors, supporting individual and group settlements.

#### Security
- **CSRF Protection**: `FastAPI-CSRF-Jinja` middleware.
- **Rate Limiting**: `SlowAPI` for global and login-specific limits.
- **Session Security**: Secure session configurations (timeout, SameSite, httponly).
- **Role-Based Authorization**: Server-side checks enforce permissions.
- **Password Reset**: Secure forgot/reset password flow for SaaS users via Resend email, with single-use, time-limited, hashed tokens and rate limiting.
- **Audit Logging**: Tracks financial transactions and security events.
- **Input Validation**: Pydantic schemas.
- **Environment Variables**: Secure storage for sensitive data.

#### Frontend Architecture
**Technology Stack**: Jinja2, Tailwind CSS (CDN), HTMX.
**Design Principles**:
- **Mobile-First Design**: Optimized for touch and responsiveness.
- **UI Design System**: Calm, Apple-inspired marine design with custom CSS properties for consistent styling and reusable component classes.
- **Desktop UI Refinement**: Dedicated desktop-only design system with a premium navy aesthetic, unified card system, and refined form inputs.
- **Navigation**: Dual-mode responsive navigation with horizontal desktop nav and an off-canvas mobile drawer.
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
- **Capacitor**: Used for a Capacitor-based iOS wrapper loading the web app in a native WKWebView, including plugins for browser, geolocation, camera, and app lifecycle management. Handles Stripe external browser interactions and ensures App Store compliance.
- **Universal Links**: `/ios/return` route for return-to-app flow.
- **Biometric Login (Face ID / Touch ID)**: SaaS users on iOS can opt in to biometric sign-in via Keychain integration.
- **Offline Handling**: Bridge shows full-screen offline overlay with retry button when device loses connectivity (iOS only).

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.
- **Open-Meteo API**: For weather data retrieval.
- **Stripe API**: For subscription billing (checkout, webhooks, billing portal).
- **Anthropic Claude**: For receipt OCR pre-fill (`claude-sonnet-4-20250514`).