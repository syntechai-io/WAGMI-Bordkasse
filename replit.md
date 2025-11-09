# Crew Wallet - Bordkasse

### Overview
Crew Wallet is a minimalist expense tracking and settlement application for sailing crew members. It offers secure authentication, manages up to 12 crew members, tracks deposits and expenses with flexible splitting, and automatically calculates optimized settlement transfers. Key features include multi-currency support with automatic conversion, PWA capabilities, and professional PDF export for trip documentation. The project aims to simplify shared expense management for sailing trips, targeting a subscription-based revenue model.

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