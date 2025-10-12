# Crew Wallet - Bordkasse

### Overview

Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members. It enables secure user authentication, manages up to 12 crew members, tracks deposits into a shared wallet, records expenses with flexible splitting, and automatically calculates optimized settlement transfers. The application supports multi-currency transactions with automatic conversion, provides PWA capabilities for mobile use, and includes professional PDF export functionality for trip documentation.

### User Preferences

Preferred communication style: Simple, everyday language.

### System Architecture

#### Backend Architecture

**Framework**: FastAPI (Python) for routing and API endpoints, structured with modular routers for different functionalities (crew, deposits, expenses, etc.).
**Authentication**: Session-based with Admin and Crew roles, using `werkzeug.security` for password hashing. Requires `SESSION_SECRET`, `ADMIN_PASSWORD`, and `CREW_PASSWORD` from environment variables.
**Template Engine**: Jinja2 for server-side rendering, integrated with HTMX for dynamic interactions.
**Data Storage**: PostgreSQL with SQLAlchemy ORM, using Replit's managed PostgreSQL database.
**Key Architectural Decisions**:
- **Modular Router Structure**: Enhances maintainability and separation of concerns.
- **Authentication Model**: Session-based with two roles (Admin, Crew) and environment variable-based secrets for security.
- **File Upload Security**: UUID-based filenames, type validation (PDF/JPG/PNG), and size limits (10MB) for receipt uploads.
- **Trip Management**: Introduced a `Trip` model to organize expenses and deposits, supporting active and archived trips, with all data scoped to a specific trip.
- **Multi-Currency Support**: Integrated ECB API for daily exchange rates to convert DKK, SEK, GBP to EUR for calculations, with rates cached to minimize API calls.
- **Performance Optimization** (Oct 2025): Eliminated N+1 query problems through pre-aggregation with GROUP BY, eager loading with joinedload(), and database indexes on all foreign keys. Balances calculation reduced from O(n*m) queries to O(1) with 4-5 total queries.

#### Data Model

**Core Entities**:
- **CrewMember**: Stores crew details, unique per trip.
- **Deposit**: Records shared wallet contributions.
- **Expense**: Tracks spending, specifying `paid_from` (wallet/private) and `split_mode` (equal/participants/percentage).
- **ExpenseParticipant**: Links expenses to specific crew for custom splits, with optional percentage field for percentage-based splitting.
- **Receipt**: Stores uploaded receipt files with metadata.
- **Trip**: Organizes all related data for a specific sailing trip.
- **AuditLog**: Records all financial transactions with user attribution, action type, entity reference, and timestamps for compliance and debugging.

#### Settlement Algorithm

The application uses a greedy matching algorithm to calculate net balances for each crew member and determine the minimal number of transfers required to settle debts, matching the largest debtor with the largest creditor.

#### Security

**Enhanced Security Features** (October 2025):
- **CSRF Protection**: FastAPI-CSRF-Jinja middleware protects all POST/PUT/DELETE requests with cookie-based CSRF token validation. All routers configured with csrf_token_processor for automatic token injection into forms using `{{ csrf_input | safe }}` template syntax. Supports both form-based and header-based (HTMX) token submission.
- **Rate Limiting**: SlowAPI with unified limiter instance enforces global limits (200/hour, 50/minute) and login-specific limits (5/minute per IP), returning proper 429 responses with Retry-After headers
- **Session Security**: 24-hour session timeout, SameSite=Lax cookies, httponly flags for XSS protection
- **Audit Logging**: AuditLog model tracks all financial transactions (deposits, expenses, settlements) with user attribution and timestamps
- **File Upload Validation**: UUID-based filenames, type validation (PDF/JPG/PNG), 10MB size limits for receipt uploads
- **Input Validation**: Pydantic schemas with type checking and bounds validation
- **Environment Variables**: SESSION_SECRET, CSRF_SECRET, ADMIN_PASSWORD, CREW_PASSWORD stored securely

#### Frontend Architecture

**Technology Stack**: Jinja2 for templates, Tailwind CSS (CDN) for styling, HTMX for AJAX, and PWA support for mobile and offline use.
**Design Principles**:
- **Mobile-First Design**: Touch-optimized interface with responsive elements.
- **Maritime UI Theme**: A comprehensive nautical aesthetic with a custom color palette, porthole-style cards, rope dividers, maritime gradient buttons, and ship wheel branding.
- **PWA Support**: Manifest and service worker enable home screen installation and offline functionality.
- **Professional PDF Export**: Replaced CSV with ReportLab for maritime-themed PDF exports of trip data.
- **Mobile Camera/File Upload** (Oct 2025): Dual-button interface for photo/receipt uploads - separate "📷 Kamera" and "📁 Datei" buttons. Uses single hidden file input with dynamic `capture` attribute toggling for iOS Safari compatibility (avoids DataTransfer API issues). Camera button sets `capture="environment"` to trigger rear camera on mobile devices.

#### Offline-First PWA Capabilities (Oct 2025)

**Complete offline functionality** enabling use in areas with poor connectivity:

**Phase 1-2: Cache-First Offline Viewing**
- IndexedDB storage for logbook entries, expenses, deposits, and crew data
- Cache-first strategy with "last synced" timestamps
- Auto-reload on reconnection to show latest data
- Visual indicators for offline mode and sync status

**Phase 3: Offline Entry Creation & Background Sync**
- Offline form submission for logbook, expenses, and deposits with optimistic UI
- Yellow "🔄 Pending" badges for entries awaiting sync
- Automatic background sync when connection restored
- Manual sync button in navbar with pending count indicator
- Database migration (12a376fa962e) adds `client_temp_id` for duplicate prevention
- Backend duplicate detection in all routers using clientTempId parameter
- Toast notifications for successful sync
- **CSRF Token Sync Support** (Oct 2025): Service worker requests CSRF token from client page via postMessage during background sync, extracts token from `fastapi-csrf-token` cookie using substring parsing (preserves base64 padding), and includes token in `X-CSRF-Token` header for all POST/PUT/DELETE sync requests to prevent 403 rejection

**Phase 4: Offline Photo/Receipt Uploads**
- Base64 conversion for offline photo/receipt storage in IndexedDB
- File-to-base64 conversion helper for expense receipts when offline
- Image preview thumbnail when photo selected offline
- Service worker base64-to-Blob conversion during sync
- FormData reconstruction with receipt file for proper backend upload
- Supports camera capture and file selection while offline
- Seamless sync of photos with expense data when connection restored
- **UX Improvements** (Oct 2025): Receipt upload only on expense creation form (removed duplicate from details page). Multiple offline expense entries supported with proper form reset - clears all form data, hides split mode UI sections, removes receipt previews, and shows success notification without page reload

### External Dependencies

#### Python Packages
- **FastAPI**: Core web framework.
- **SQLAlchemy**: ORM for database interactions.
- **psycopg2-binary**: PostgreSQL adapter for Python.
- **Jinja2**: Template engine.
- **python-multipart**: Handles file uploads.
- **python-dotenv**: Manages environment variables.
- **ReportLab**: Generates PDF reports.
- **Alembic**: Database migration management.
- **fastapi-csrf-jinja**: CSRF protection middleware with Jinja2 template integration.
- **slowapi**: Rate limiting for API endpoints.
- **werkzeug**: Password hashing utilities.

#### Frontend Libraries (CDN)
- **Tailwind CSS**: Utility-first CSS framework.
- **HTMX**: For dynamic HTML interactions.

#### Database
- **PostgreSQL**: Replit-managed PostgreSQL database (Neon-backed) accessed via the `DATABASE_URL` environment variable.

#### File Storage
- **Local filesystem**: For receipt uploads in the `/uploads` directory.

#### External Services
- **ECB (European Central Bank) API**: Used for fetching daily exchange rates for multi-currency support.

### Testing

#### Test Suite
The application includes a comprehensive E2E test suite (`test_app_e2e.py`) with **100% pass rate (36/36 tests)**.

**Test Coverage**:
- Authentication & session management (7 tests)
- Trip management & archiving (4 tests)
- Crew CRUD operations (4 tests)
- Deposits with multi-currency support (4 tests)
- Expenses with flexible splitting (4 tests)
- Balance calculations & settlement (3 tests)
- PDF export functionality (3 tests)
- PWA features (4 tests)
- Edge cases & validation (3 tests)

**Recent Improvements** (Oct 2025):
- Fixed login failure test to properly follow redirect flow and validate error messages
- Updated archive trip test to align with automatic archiving behavior when creating new trips
- Improved PDF validation using PyPDF2 for reliable text extraction from generated PDFs
- Enhanced SessionHelper with automatic CSRF token extraction and inclusion in POST requests
- Tests now properly handle CSRF protection and rate limiting (some tests may encounter 429 responses due to strict rate limits)

**Running Tests**:
```bash
pytest test_app_e2e.py -v                    # Run all tests
pytest test_app_e2e.py -v -k "test_auth"     # Run specific test category
```

**Notes**: 
- PyPDF2 is currently used for PDF parsing but shows a deprecation warning. Future upgrade to `pypdf` package is recommended.
- Test suite includes CSRF token handling but may encounter rate limiting (429 responses) during rapid test execution - this is expected behavior demonstrating security features working correctly.