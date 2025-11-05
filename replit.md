# Crew Wallet - Bordkasse

### Overview
Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members. It provides secure user authentication, manages up to 12 crew members, tracks deposits into a shared wallet, records expenses with flexible splitting, and automatically calculates optimized settlement transfers. The application supports multi-currency transactions with automatic conversion, offers PWA capabilities, and includes professional PDF export functionality for trip documentation. Its business vision is to simplify shared expense management for sailing trips, targeting a market with significant potential for subscription-based revenue.

### Recent Changes (November 5, 2025)
- **Expense Timestamp Precision**: Added `occurred_at` DateTime field to Expense model for accurate crew departure filtering. Real-time expenses (today) use current timestamp to exclude departed crew immediately. Backdated expenses (past dates) use start-of-day to include crew active that day. This fixes the issue where crew members departed at 10:00 AM were incorrectly included in expenses created at 10:02 AM.
- **Trip Switching System**: Fixed redirect loop when admin logs in with no active trip. Admin login now redirects to trips page if no active trip exists, otherwise auto-selects active trip.
- **CSRF Token Fix**: Fixed trip selector dropdown forms (desktop and mobile) to use proper `{{ csrf_input | safe }}` pattern instead of manually accessing session token.
- **Database Session Management**: Fixed potential session leak in `trip_context_processor` by properly closing database sessions in finally block.
- **Session-Based Trip Selection**: `TripService.get_selected_trip()` no longer falls back to active trip - requires explicit selection via session.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Session-based with three role levels (Global Admin, Trip Admin, Crew), using `werkzeug.security` for password hashing and environment variables for secrets.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Modular Router Structure**: For maintainability and separation of concerns.
- **Authentication Model**: Session-based with three role levels and environment variable-based security. Trip admins have scoped permissions for their assigned trip only.
- **File Upload Security**: UUID-based filenames, type validation (PDF/JPG/PNG), and size limits (10MB).
- **Trip Management**: `Trip` model organizes all data, supports active/archived/closed trips, with all data scoped to a specific trip. Trip selection system allows switching between trips. Closed trips are read-only for crew, while admin and trip admins retain full edit access for their respective trips.
- **Trip Admin System**: Up to 2 trip admins per trip, designated via checkbox in crew management. Trip admins can manage their assigned trip (even when closed), but cannot access password management or designate other trip admins. Session-based tracking via `trip_admin_trip_id`.
- **Multi-Currency Support**: Integrates ECB API for daily exchange rates, with cached rates.
- **Performance Optimization**: Eliminated N+1 query problems through pre-aggregation, eager loading, and database indexes. Balance calculation optimized.
- **Expense Templates**: Global templates accelerate data entry for common expenses, pre-filling category, amount, currency, payment source, and split mode. Admin-only management available.
- **Settlement Groups**: Comprehensive system to combine crew members for simplified settlement transfers while maintaining individual expense tracking. Supports use cases like couples or families settling together.

#### Data Model
**Core Entities**:
- **CrewMember**: Crew details. Includes `is_trip_admin` flag, `trip_admin_password_hash` for trip admin authentication, and `departed_at` timestamp for mid-trip departures.
- **Deposit**: Shared wallet contributions.
- **Expense**: Spending records, supporting `paid_from`, `split_mode`, and nullable `payer_id` for external charges.
- **ExpenseParticipant**: Links expenses to crew for custom splits.
- **ExpenseTemplate**: Global templates for quick expense entry.
- **CrewGroup**: Settlement groups that combine crew members for simplified settlement. Each group has a name (unique per trip) and representative member.
- **CrewGroupMember**: Junction table linking crew members to groups. One member can only be in one group.
- **Receipt**: Uploaded receipt files.
- **Trip**: Organizes all related data, with an `is_closed` field.
- **AuditLog**: Records financial transactions with user attribution.

#### Settlement Algorithm
Uses a greedy matching algorithm to calculate net balances and minimize transfers by matching largest debtor with largest creditor. The calculation has been verified with real trip data (Kykladen 2025) and works correctly with only minor rounding differences (< 0.05 EUR tolerance). The Ausgleich page includes a comprehensive German explanation of the 3-step calculation process: (1) individual balance calculation, (2) settlement group aggregation, and (3) transfer optimization using the greedy algorithm.

**Crew Departure Handling**: The settlement calculation includes ALL crew members (even departed ones) to account for all financial activity during the trip. For equal-split expenses, crew members are considered active from the trip start until their departure date. Equal-split expenses divide by the count of crew who were active on each expense's date, excluding crew who had already departed. This allows crew to be added to the system retroactively while maintaining correct expense splits based on actual presence during the trip.

**Timezone Handling**: All datetime fields (expense `occurred_at`, crew `departed_at`) use naive local datetime (not UTC) for consistency. This ensures accurate comparisons when filtering crew participation based on departure times.

#### Security
- **CSRF Protection**: FastAPI-CSRF-Jinja middleware protects all POST/PUT/DELETE requests with cookie-based token validation.
- **Rate Limiting**: SlowAPI enforces global and login-specific limits.
- **Session Security**: 24-hour timeout, SameSite=Lax, httponly flags.
- **Trip Permissions**: `TripService.is_trip_editable()` enforces closed trip protection. `TripService.is_admin_or_trip_admin()` enforces admin/trip-admin authorization for crew management.
- **Role-Based Authorization**: Three role levels (Global Admin, Trip Admin, Crew) with server-side authorization checks on all GET and POST routes to prevent privilege escalation.
- **Audit Logging**: Tracks all financial transactions.
- **File Upload Validation**: UUID-based filenames, type validation, size limits.
- **Input Validation**: Pydantic schemas.
- **Environment Variables**: Sensitive data stored securely.

#### Frontend Architecture
**Technology Stack**: Jinja2, Tailwind CSS (CDN), HTMX.
**Design Principles**:
- **Mobile-First Design**: Touch-optimized and responsive.
- **Maritime UI Theme**: Nautical aesthetic with custom color palette, porthole-style cards, and ship wheel branding.
- **Professional PDF Export**: ReportLab for maritime-themed PDF exports.
- **Mobile Camera/File Upload**: Dual-button interface for photo/receipt uploads, with dynamic `capture` attribute for mobile compatibility.
- **Responsive Dashboard**: Mobile-friendly landing page with simplified navigation.
- **Grouped Navigation**: Desktop navigation reduced from 11 to 5 items using dropdown menus for better organization and accessibility.

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

#### Frontend Libraries (CDN)
- **Tailwind CSS**: CSS framework.
- **HTMX**: Dynamic HTML.

#### Database
- **PostgreSQL**: Replit-managed (Neon-backed).

#### File Storage
- **Local filesystem**: For receipt uploads in `/uploads`.

#### External Services
- **ECB (European Central Bank) API**: For daily exchange rates.