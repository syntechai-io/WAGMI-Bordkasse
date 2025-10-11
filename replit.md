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
**Data Storage**: SQLite with SQLAlchemy ORM, using a file-based database (`/data/app.db`).
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
- **Expense**: Tracks spending, specifying `paid_from` (wallet/private) and `split_mode` (equal/participants).
- **ExpenseParticipant**: Links expenses to specific crew for custom splits.
- **Receipt**: Stores uploaded receipt files with metadata.
- **Trip**: Organizes all related data for a specific sailing trip.

#### Settlement Algorithm

The application uses a greedy matching algorithm to calculate net balances for each crew member and determine the minimal number of transfers required to settle debts, matching the largest debtor with the largest creditor.

#### Security

Security measures include file upload validation, UUID-based filenames for receipts, input validation via Pydantic schemas, and reliance on environment variables for sensitive authentication credentials.

#### Frontend Architecture

**Technology Stack**: Jinja2 for templates, Tailwind CSS (CDN) for styling, HTMX for AJAX, and PWA support for mobile and offline use.
**Design Principles**:
- **Mobile-First Design**: Touch-optimized interface with responsive elements.
- **Maritime UI Theme**: A comprehensive nautical aesthetic with a custom color palette, porthole-style cards, rope dividers, maritime gradient buttons, and ship wheel branding.
- **PWA Support**: Manifest and service worker enable home screen installation and offline functionality.
- **Professional PDF Export**: Replaced CSV with ReportLab for maritime-themed PDF exports of trip data.

### External Dependencies

#### Python Packages
- **FastAPI**: Core web framework.
- **SQLAlchemy**: ORM for database interactions.
- **Jinja2**: Template engine.
- **python-multipart**: Handles file uploads.
- **python-dotenv**: Manages environment variables.
- **ReportLab**: Generates PDF reports.

#### Frontend Libraries (CDN)
- **Tailwind CSS**: Utility-first CSS framework.
- **HTMX**: For dynamic HTML interactions.

#### Database
- **SQLite**: Embedded file-based database (`/data/app.db`).

#### File Storage
- **Local filesystem**: For receipt uploads in the `/uploads` directory.

#### External Services
- **ECB (European Central Bank) API**: Used for fetching daily exchange rates for multi-currency support.