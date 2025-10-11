# Crew Wallet - Bordkasse

## Overview

Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members to manage shared expenses during trips. The application allows crew members to track deposits into a shared wallet, record expenses (both from the wallet and private payments), and automatically calculate who owes whom at the end of the trip using an optimized settlement algorithm.

Key features:
- Crew member management with unique codes and payment handles (IBAN/PayPal/etc.)
- Deposit tracking into shared wallet
- Expense recording with flexible split modes (equal split or specific participants)
- Receipt upload and storage for expenses
- Automatic balance calculation and minimal settlement transfers
- CSV export functionality
- Progressive Web App (PWA) support for mobile usage

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture

**Framework**: FastAPI (Python)
- Router-based modular structure with separate modules for auth, crew, deposits, expenses, receipts, balances, and export
- Session-based authentication using itsdangerous serializer
- CSRF protection for all mutating operations
- Dependency injection for database sessions and authentication

**Template Engine**: Jinja2
- Server-side rendering for all pages
- HTMX integration for interactive elements without full page reloads
- Mobile-first responsive design using Tailwind CSS (CDN)

**Data Storage**: SQLite with SQLAlchemy ORM
- File-based database at `/data/app.db`
- Declarative model definitions using SQLAlchemy Base
- Session management with context managers for automatic cleanup
- Database initialization and seeding on startup

**Key Architectural Decisions**:

1. **Modular Router Structure**: Split functionality into domain-specific routers (auth, crew, deposits, expenses, etc.) for maintainability and clear separation of concerns. This allows independent development and testing of features.

2. **Session-Based Authentication**: Simple admin-only authentication using session cookies with URLSafeTimedSerializer. Chosen for simplicity over JWT/OAuth as the application has a single admin user. Sessions expire after 24 hours for security.

3. **CSRF Protection Pattern**: Every mutating POST request requires a CSRF token stored in session and validated on submission. This prevents cross-site request forgery attacks while maintaining simplicity.

4. **File Upload Security**: Receipts are stored with UUID-based filenames to prevent directory traversal attacks. File type validation (PDF/JPG/PNG only) and size limits (10MB max) enforce security boundaries.

### Data Model

**Core Entities**:

1. **CrewMember**: Stores crew member information with unique code (max 8 chars), name, and optional payment handle (IBAN/PayPal/Revolut)

2. **Deposit**: Records money added to shared wallet by crew members, including amount, date, and optional note

3. **Expense**: Tracks spending with payer reference, category, description, amount, and two key enums:
   - `paid_from`: wallet (from shared funds) or private (personal payment to be reimbursed)
   - `split_mode`: equal (split among all crew) or participants (split among specific subset)

4. **ExpenseParticipant**: Junction table linking expenses to participating crew members for custom splits

5. **Receipt**: Stores uploaded receipt files with UUID-based filenames, original names, content type, and size

**Relationships**: SQLAlchemy relationships with cascade deletes ensure data integrity when crew members are removed.

### Settlement Algorithm

**Purpose**: Calculate minimal transfers to settle all debts between crew members

**Algorithm**: Greedy matching approach in `settlement.py`
- Calculates net balance for each crew member (what they paid minus their share)
- Separates creditors (positive balance) and debtors (negative balance)
- Greedily matches largest debtor with largest creditor until all settled
- Returns list of (from, to, amount) tuples representing minimum transfers needed

**Rationale**: Minimizes number of transactions needed, making settlement more practical. Alternative approaches like full graph optimization were considered but rejected for complexity vs. benefit tradeoff.

### Authentication & Security

**Authentication**: 
- Environment variable-based admin credentials (ADMIN_USER, ADMIN_PASSWORD)
- Session secret key from environment or generated randomly
- Token-based session storage with 24-hour expiration
- No user registration - admin-only access model

**Security Measures**:
- CSRF tokens for all state-changing operations
- File upload validation (type, size, sanitized storage)
- Session middleware for secure cookie handling
- Input validation through Pydantic schemas

**Tradeoffs**: Chose simplicity over multi-user authentication system as application targets small crew groups with trusted admin. Could be extended with PIN-based crew access if needed.

### Frontend Architecture

**Technology Stack**:
- Jinja2 templates for server-side rendering
- Tailwind CSS (CDN) for responsive styling
- HTMX for AJAX interactions without full page reloads
- Progressive Web App (PWA) with service worker for offline capability

**Mobile-First Design**:
- Touch-optimized interface with large tap targets
- Viewport settings prevent zoom on input focus (font-size: 16px)
- Sticky navigation with mobile menu toggle
- Bottom padding accommodation for mobile browsers

**Key Design Decisions**:

1. **Server-Side Rendering**: Chosen over SPA for simplicity, better SEO, and reduced JavaScript bundle size. HTMX provides interactivity where needed without framework overhead.

2. **PWA Support**: Manifest and service worker enable installation on mobile devices and offline access to cached pages, critical for boat trips with limited connectivity.

3. **Responsive Tables**: Horizontal scroll on mobile for data tables rather than card layouts, preserving data density and scanning efficiency.

## External Dependencies

### Python Packages
- **FastAPI**: Web framework for API and page routing
- **SQLAlchemy**: ORM for database operations
- **Jinja2**: Template engine for HTML rendering
- **python-multipart**: File upload handling
- **itsdangerous**: Session token serialization and CSRF token generation
- **python-dotenv**: Environment variable management
- **Starlette**: ASGI framework (FastAPI dependency) providing session middleware

### Frontend Libraries (CDN)
- **Tailwind CSS**: Utility-first CSS framework
- **HTMX**: HTML-over-the-wire interactions

### Database
- **SQLite**: Embedded file-based database requiring no external server
- Database file location: `/data/app.db`
- No migration tool configured (Alembic mentioned in requirements but not implemented)

### File Storage
- **Local filesystem**: Receipt uploads stored in `/uploads` directory
- UUID-based filenames for security
- Supported formats: PDF, JPG, PNG

### Environment Variables
- `ADMIN_USER`: Administrator username (default: "admin")
- `ADMIN_PASSWORD`: Administrator password (default: "changeme123")
- `SESSION_SECRET`: Secret key for session signing (auto-generated if not provided)

### No External Services
The application is designed to run completely self-contained without external APIs, cloud storage, or third-party authentication services. This ensures functionality even in offline/boat environments.