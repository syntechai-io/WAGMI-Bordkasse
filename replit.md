# Crew Wallet - Bordkasse

### Overview
Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members. It provides secure user authentication, manages up to 12 crew members, tracks deposits into a shared wallet, records expenses with flexible splitting, and automatically calculates optimized settlement transfers. The application supports multi-currency transactions with automatic conversion, offers PWA capabilities, and includes professional PDF export functionality for trip documentation. Its business vision is to simplify shared expense management for sailing trips, targeting a market with significant potential for subscription-based revenue.

### Recent Changes (November 9, 2025)
- **Hybrid Dropdown/Manual Entry Fields**: Converted wind direction, wind strength, visibility, and sail plan to hybrid select/manual pattern. Default mode shows mobile-friendly `<select>` dropdowns (no keyboard popup). Toggle button "✏️ Eigenen Wert eingeben" switches to manual text entry mode for custom values. Auto-detects legacy values on page load and enables manual mode when needed. Name attribute swapping ensures only active control submits. Preserves all existing legacy values while providing fast dropdown UX on mobile.
- **Compact Date/Time Fields**: Redesigned date and time inputs to use flex layout with proper spacing instead of full-width grid. Date field (min-width: 160px) and time field (min-width: 140px) now sit side-by-side with gap, preventing unnecessary expansion while maintaining responsive behavior.
- **Weather API Integration**: Added Open-Meteo API integration (free, no API key required) to auto-pull temperature, wind direction, wind speed (converted to Beaufort), and pressure from GPS coordinates. New "Wetterdaten automatisch abrufen" button fetches live weather data using coordinates from GPS button. Updated to work with hybrid dropdown/manual system via `getHybridFieldControl()` helper. Auto-sets weather source to "Open-Meteo API".
- **Comprehensive Testing**: Created test_weather_service.py (10 unit tests passing) for API parsing, Beaufort conversion, compass direction conversion, and error handling. Updated test_regression_logbook.py (17 tests passing) to verify hybrid select/manual fields, weather API integration, GPS auto-pull, motor hours, PDF export, in-mast furling, watch leader, offline storage, and all Phase A fields.

### Previous Changes (November 8, 2025)
- **Logbook Phase A Complete**: Enhanced LogbookEntry with 20+ fields including navigation (COG, SOG, log speed, distance), advanced weather (pressure, trend, source), engine tracking (on/off times, total hours, fuel), in-mast furling (0-100% slider, NO reef options), events (category, details), and append-only compliance (parent_id, is_superseded, change_note). All fields are nullable and optional.
- **PDF Export System**: Added ReportLab-based PDF generation for German/European official logbook standards with two endpoints: single entry export (GET /logbook/export/pdf/entry/{id}) and daily export (GET /logbook/export/pdf/daily?export_date=YYYY-MM-DD). Maritime-themed with bilingual labels and signature fields.
- **Watch Leader System**: Added watch_leader_id field to LogbookEntry with crew selection dropdown for designating Wachführer on each entry.
- **Vessel-Specific Sail Config**: Simplified headsail configuration to dropdown with only "Genua gesetzt/teilweise/geborgen" options, reflecting vessel inventory (mainsail with in-mast furling + genua only).
- **Photo Upload**: Confirmed existing POST /{entry_id}/photos/upload endpoint for logbook photo uploads with LogbookPhoto model.
- **GPS Auto-Pull Features**: Enhanced GPS button to extract SOG (speed in knots, converted from m/s via 1.94384 multiplier) and COG (heading 0-359°) in addition to lat/lon. Handles null speed/heading gracefully.
- **Continuous GPS Tracking**: Implemented `static/js/logbook-gps.js` module with LogbookGPSTracker class for foreground-only tracking (iOS restriction). Provides start/stop controls, active banner with live updates (position, accuracy, last update time), 5-second update frequency, position history buffer (last 10), and event-driven architecture.
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime duration from on/off timestamps, adds to existing eng_hours_total if present. Quick action buttons (Motor AN/AUS) auto-set current time and trigger calculation. Manual override always available.
- **GPS Debug Logging**: Comprehensive console logging for GPS button showing protocol (HTTP/HTTPS), iframe status, permission state, position data, and detailed error diagnostics. Helps diagnose GPS issues in development vs production environments.
- **PDF Navigation Footer**: PDF exports now include footer with generation timestamp, trip name, and clickable links back to logbook entry detail view or dashboard. Uses REPLIT_DOMAINS environment variable for correct URL generation.
- **Default Start Port**: New logbook entries auto-fill departure field with "Fredericia DK" (user-configurable default).
- **Comprehensive Testing**: Created test_logbook_autopull.py (17 tests passing) for GPS conversion formulas, motor hours logic, and offline storage validation. Created TESTING_AUTOPULL.md manual testing guide with 5 test suites covering GPS single/continuous, motor hours, offline, and end-to-end scenarios. Test entry script (create_test_logbook_entry.py) for realistic PDF export testing.

### Previous Changes (November 5, 2025)
- **Expense Timestamp Precision**: Added `occurred_at` DateTime field to Expense model for accurate crew departure filtering.
- **Trip Switching System**: Fixed redirect loop when admin logs in with no active trip.
- **CSRF Token Fix**: Fixed trip selector dropdown forms to use proper `{{ csrf_input | safe }}` pattern.
- **Database Session Management**: Fixed potential session leak in `trip_context_processor`.
- **Session-Based Trip Selection**: `TripService.get_selected_trip()` no longer falls back to active trip.

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

**Timezone Handling**: All datetime fields (expense `occurred_at`, crew `departed_at`) are normalized to **UTC** for consistency across different user timezones. The crew deactivation form captures the browser's timezone offset via JavaScript and converts the local datetime to UTC before storing. Expense creation uses `datetime.utcnow()` for real-time expenses. This ensures accurate timestamp comparisons when filtering crew participation based on departure times, regardless of the user's timezone (e.g., CET users at UTC+1 are handled correctly).

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