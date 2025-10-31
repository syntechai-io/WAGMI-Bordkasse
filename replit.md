# Crew Wallet - Bordkasse

### Overview
Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members. It provides secure user authentication, manages up to 12 crew members, tracks deposits into a shared wallet, records expenses with flexible splitting, and automatically calculates optimized settlement transfers. The application supports multi-currency transactions with automatic conversion, offers PWA capabilities, and includes professional PDF export functionality for trip documentation. Its business vision is to simplify shared expense management for sailing trips, targeting a market with significant potential for subscription-based revenue.

### User Preferences
Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture
**Framework**: FastAPI (Python) with modular routers.
**Authentication**: Session-based with Admin and Crew roles, using `werkzeug.security` for password hashing and environment variables for secrets.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX.
**Data Storage**: PostgreSQL with SQLAlchemy ORM.
**Key Architectural Decisions**:
- **Modular Router Structure**: For maintainability and separation of concerns.
- **Authentication Model**: Session-based with two roles and environment variable-based security.
- **File Upload Security**: UUID-based filenames, type validation (PDF/JPG/PNG), and size limits (10MB).
- **Trip Management**: `Trip` model organizes all data, supports active/archived/closed trips, with all data scoped to a specific trip. Trip selection system allows switching between trips. Closed trips are read-only for crew, while admin retains full edit access.
- **Multi-Currency Support**: Integrates ECB API for daily exchange rates, with cached rates.
- **Performance Optimization**: Eliminated N+1 query problems through pre-aggregation, eager loading, and database indexes. Balance calculation optimized.
- **Expense Templates**: Global templates accelerate data entry for common expenses, pre-filling category, amount, currency, payment source, and split mode. Admin-only management available.
- **Settlement Groups**: Comprehensive system to combine crew members for simplified settlement transfers while maintaining individual expense tracking. Supports use cases like couples or families settling together.

#### Data Model
**Core Entities**:
- **CrewMember**: Crew details.
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

#### Security
- **CSRF Protection**: FastAPI-CSRF-Jinja middleware protects all POST/PUT/DELETE requests with cookie-based token validation.
- **Rate Limiting**: SlowAPI enforces global and login-specific limits.
- **Session Security**: 24-hour timeout, SameSite=Lax, httponly flags.
- **Trip Permissions**: `TripService.is_trip_editable()` enforces closed trip protection.
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