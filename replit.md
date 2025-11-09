# WAGMI CrewLog - Maritime Logbook & Bordkasse

### Overview
WAGMI CrewLog is a comprehensive maritime logbook and expense tracking application for sailing crew members. It combines professional logbook entries with GPS and weather data integration alongside expense tracking (Bordkasse) and settlement calculations. The application offers secure authentication, manages up to 12 crew members, tracks deposits and expenses with flexible splitting, and automatically calculates optimized settlement transfers. Key features include maritime logbook compliance, multi-currency support with automatic conversion, PWA capabilities, and professional PDF export for trip documentation and official logbook records.

### Recent Changes (November 9, 2025)
- **Vessel Information Auto-Population (LATEST)**: Enhanced Trip model with complete vessel metadata (home_port, call_sign, imo_mmsi) for maritime logbook compliance. Quick Start and Solo-Sailing trip creation now auto-populate skipper name/code and home port from UserPreferences. For Sven's WAGMI trips, this ensures PDFs automatically show "Sven" as skipper and "Fredericia" as home port without manual entry. Call sign and MMSI remain trip-specific fields for manual entry when needed. Created database migration (1350e71f86fe) to add vessel columns.
- **PDF Export Bugfix**: Fixed AttributeError in logbook PDF exports caused by missing skipper_name and skipper_code fields on Trip model. Added both fields to Trip model as nullable strings, created database migration (cd1095e65126) to add columns, and implemented getattr() fallbacks in PDF export code for backward compatibility with older trips. Both single-entry and daily PDF exports now work correctly with proper skipper information display.
- **Solo-Sailing Trip Creation**: Added "Solo-Sailing" checkbox to trip creation form that automatically adds the user as both skipper and crew with trip admin privileges. Uses UserPreferences for skipper name/code or falls back to "Skipper"/"SK" defaults when preferences don't exist. Single database query optimization ensures preferences are fetched once and reused for both trip and crew creation. Streamlines solo-sailing workflow by eliminating manual crew management step.
- **Logbook PDF Crew Roster**: Enhanced logbook PDF exports (both single entry and daily) to include skipper and crew roster information in the header section. PDFs now display skipper name/code and full crew list (excluding departed members) to comply with official maritime logbook standards. Crew data is automatically queried from the database and formatted with professional maritime typography.
- **Weather API Bugfix**: Fixed Quick Fill weather data fetch - moved endpoint from `/logbook/weather` to `/api/weather` to bypass authentication middleware. Created new `routers/api.py` for unauthenticated public endpoints. Weather data (temperature, wind, pressure) now loads correctly via Open-Meteo API integration without 303 redirect errors.
- **Navigation Restructuring**: Reorganized top navigation bar for improved accessibility:
  - **Logbook Promotion**: Moved Logbuch from Verwaltung dropdown to top-level navigation next to Törns for quick access
  - **Compact Layout**: Reduced spacing (space-x-3) and font size (text-sm) to fit all items in one row on desktop
  - **Streamlined Verwaltung**: Simplified dropdown to Crew, Groups, Passwords (admin), and Export only
  - **Smaller Icons**: Reduced dropdown arrow icons to w-3 h-3 for more compact appearance
  - **Goal**: Prioritize quick access to Logbook alongside Törns for sailors' primary workflows
- **Mobile Dashboard UX Optimization**: Completely redesigned mobile dashboard prioritizing quick logbook entry:
  - **Primary CTA**: Prominent "Schnell-Logbuch" button at top with 96px min-height and 24px padding for easy tapping while sailing
  - **Accessibility**: All touch targets meet ≥72px minimum (48dp accessibility guideline)
  - **Visual Hierarchy**: Info cards (e.g., total expenses) visually distinct with border styling vs. action cards
  - **Layout**: Compact 2-column grids for secondary actions reducing scrolling
  - **Admin Controls**: Quick Start button hidden on mobile to prioritize core logbook workflow
  - **Goal**: Reduce time-to-log-entry to ≤4 taps from dashboard
- **Desktop Dashboard Redesign**: Two-column layout focusing on core workflows:
  - Left column: Logbook section with entry action + crew management
  - Right column: Bordkasse section with total expenses + expense entry + settlement
  - Removed detailed stats (deposits breakdown, top categories) to reduce clutter
  - Added timezone capture using device's Intl.DateTimeFormat API, stored in sessionStorage for consistent local time handling
- **Quick Start Törn**: Implemented one-click trip creation for single-handed sailing workflow. Features:
  - New `UserPreferences` model storing default skipper, boat, home port, coordinates, and currency
  - Seeded with Sven's defaults: WAGMI boat, Fredericia Denmark (55.553611°N, 9.730556°E), DKK currency
  - `TripQuickStartService` creates trip with auto-generated name (WAGMI - DD.MM.YYYY), adds skipper as crew+admin, and generates first logbook departure entry with motor running from home port
  - Prominent "⚡ Quick Start WAGMI" buttons on dashboard and trips page for instant trip creation
  - POST /trips/quick-start endpoint with admin-only security, auto-archives previous active trip, and redirects to dashboard
  - Optimized for solo sailor who primarily uses WAGMI from Fredericia
- **Settlement Export Enhancement**: Added settlement transfer calculations to both PDF and CSV exports showing optimized payment transfers (who owes whom). Changed from StreamingResponse to Response for better navigation after download.
- **Quick Entry System (Phase B)**: Added maneuver type field to LogbookEntry model with 7 types: departure, sail_change, motor, anchor, weather, arrival, and full entry. Implemented button-based maneuver selector in logbook form with icons (🚢⛵🔧⚓🌤️🏁📝) and visual feedback. JavaScript manages button selection and stores selected type. Enables fast logging of specific maneuver types during sailing. All fields remain visible for all maneuver types (user can categorize entries).
- **Daily Logbook View**: Created /logbook/daily route displaying all entries for a selected date in chronological timeline format. Features date navigation (prev/next buttons + date picker), summary statistics (entry count, total distance, engine hours delta, route: departure → destination), maneuver type icons for each entry, and link to daily PDF export. German date formatting with proper weekday/month names. Engine hours calculated as delta (max - min) only when 2+ readings exist.
- **Enhanced Daily Navigation**: Main logbook list now groups entries by date with clickable date headers linking to daily view. Each date shows "📖 Tagesansicht →" badge for easy access to full day timeline. Individual entries indented under date headers with time-only display and maneuver type icons.
- **Quick Fill Feature**: Added prominent "⚡ Quick Fill" button to logbook form that auto-populates all data in one tap: current date/time, GPS position (lat/lon/SOG/COG), and weather data (temperature, wind, pressure). Features loading spinner, success/error notifications, and seamless integration with hybrid dropdown/manual fields. Optimized for mobile use with large touch target and visual feedback.
- **PDF Export Redesign**: Completely redesigned PDF exports to match traditional maritime logbook format with grid-based table layout. Changed from portrait to landscape orientation. All entries now displayed in a single table with 11 columns (Zeit, Position, Kurs, Fahrt, Log, Wind, Wetter, Motor, Segel, Wache, Bemerkungen). Features black grid lines, alternating row backgrounds, compact 7pt font, and professional appearance matching official maritime documentation. Fixed coordinate bug (0° equator/meridian now render correctly). Multiple entries fit on one page in scannable grid format.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Session-based with Global Admin, Trip Admin, and Crew roles, using `werkzeug.security` for password hashing.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Modular Router Structure**: Enhances maintainability and separation of concerns.
- **Authentication Model**: Robust, role-based security with environment variable-based secrets. Trip admins have scoped permissions.
- **File Upload Security**: Enforces UUID-based filenames, type validation (PDF/JPG/PNG), and size limits (10MB).
- **Trip Management**: `Trip` model organizes all data, supports active/archived/closed states, with all data scoped to a specific trip.
- **Trip Admin System**: Allows up to two trip admins per trip with specific management capabilities.
- **Multi-Currency Support**: Integrates with the ECB API for daily exchange rates, with caching.
- **Performance Optimization**: Addresses N+1 query problems through pre-aggregation, eager loading, and database indexes.
- **Expense Templates**: Global templates streamline data entry for common expenses.
- **Settlement Groups**: Allows combining crew members for simplified settlement transfers while maintaining individual expense tracking.
- **Logbook System**: Comprehensive logbook entry with over 20 fields (navigation, weather, engine, events), including append-only compliance. Supports quick entry system with maneuver types and hybrid dropdown/manual input fields.
- **GPS Integration**: Enhanced GPS auto-pull for latitude, longitude, Speed Over Ground (SOG), and Course Over Ground (COG). Continuous foreground GPS tracking with position history.
- **Weather API Integration**: Open-Meteo API integration for automatic weather data retrieval (temperature, wind, pressure).
- **Motor Hours Auto-Calculation**: JavaScript logic calculates engine runtime from on/off timestamps.
- **PDF Export**: ReportLab-based PDF generation for single entries and daily summaries, adhering to German/European official logbook standards.
- **Crew Departure Handling**: Settlement calculations correctly account for crew members departing mid-trip by considering their active presence for expense splitting.
- **Timezone Handling**: All datetime fields are normalized to UTC for consistency, with client-side conversion for accurate storage.

#### Data Model
**Core Entities**:
- **CrewMember**: Includes `is_trip_admin` and `departed_at`.
- **Deposit**: Tracks contributions to the shared wallet.
- **Expense**: Records spending with `paid_from`, `split_mode`, and nullable `payer_id`.
- **ExpenseParticipant**: Manages custom expense splits.
- **ExpenseTemplate**: Reusable templates for expenses.
- **CrewGroup**, **CrewGroupMember**: Manages settlement groups.
- **Receipt**: Stores uploaded receipt files.
- **Trip**: Main organizing entity with an `is_closed` field.
- **AuditLog**: Records financial transactions.
- **LogbookEntry**: Detailed records of trip events, including navigation, weather, engine, and events.
- **LogbookPhoto**: Photos associated with logbook entries.
- **UserPreferences**: Stores per-user defaults for quick trip creation (skipper, boat, home port, coordinates, currency).

#### Settlement Algorithm
Uses a greedy matching algorithm to minimize transfers between debtors and creditors, verified for accuracy. The calculation process includes individual balance calculation, settlement group aggregation, and optimized transfer generation.

#### Security
- **CSRF Protection**: `FastAPI-CSRF-Jinja` middleware.
- **Rate Limiting**: `SlowAPI` for global and login-specific limits.
- **Session Security**: 24-hour timeout, SameSite=Lax, httponly flags.
- **Role-Based Authorization**: Server-side checks enforce permissions across all routes.
- **Audit Logging**: Tracks financial transactions for accountability.
- **Input Validation**: Pydantic schemas.
- **Environment Variables**: Secure storage for sensitive data.

#### Frontend Architecture
**Technology Stack**: Jinja2, Tailwind CSS (CDN), HTMX.
**Design Principles**:
- **Mobile-First Design**: Optimized for touch and responsiveness.
- **Maritime UI Theme**: Nautical aesthetic with custom colors and components.
- **Professional PDF Export**: Themed PDF outputs.
- **Mobile Camera/File Upload**: Dual-button interface for photo uploads.
- **Responsive Dashboard**: Streamlined mobile navigation.
- **Grouped Navigation**: Desktop navigation uses dropdowns for better organization.
- **Compact Date/Time Fields**: Efficient layout for date and time inputs.

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
- **Open-Meteo API**: For weather data retrieval.