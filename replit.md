# Crew Wallet - Bordkasse

## Overview

Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members to manage shared expenses during trips. The application works without login/authentication and allows up to 12 crew members to track deposits into a shared wallet, record expenses (both from the wallet and private payments), and automatically calculate who owes whom at the end of the trip using an optimized settlement algorithm.

Key features:
- **No authentication required** - instant access without login
- Crew member management for up to 12 members with unique codes (up to 20 chars) and payment handles (IBAN/PayPal/etc.)
- Deposit tracking into shared wallet with **edit and delete** capabilities
- Expense recording with flexible split modes (equal split or specific participants) and **edit and delete** capabilities
- Receipt upload and storage for expenses with camera integration
- Automatic balance calculation and minimal settlement transfers
- CSV export functionality
- Progressive Web App (PWA) support for mobile usage and home screen installation

## Recent Changes

**October 11, 2025**:
- Added **edit and delete functionality** for deposits and expenses
- Users can now correct mistakes in deposits and expenses through intuitive edit forms
- Delete operations include confirmation dialogs for safety
- Robust error handling for edge cases (stale IDs, deleted records, concurrent modifications)
- User-friendly error messages displayed when records are not found or cannot be modified
- Crew member deletion now validates for related deposits/expenses before allowing deletion

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture

**Framework**: FastAPI (Python)
- Router-based modular structure with separate modules for crew, deposits, expenses, receipts, balances, and export
- **No authentication required** - open access model for trusted crew environments
- Dependency injection for database sessions

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

1. **Modular Router Structure**: Split functionality into domain-specific routers (crew, deposits, expenses, etc.) for maintainability and clear separation of concerns. This allows independent development and testing of features.

2. **No Authentication Model**: Removed authentication system for instant access. Designed for trusted crew environments on sailing trips where simplicity and speed are prioritized. The app is intended for temporary use during a single trip without long-term data retention.

3. **File Upload Security**: Receipts are stored with UUID-based filenames to prevent directory traversal attacks. File type validation (PDF/JPG/PNG only) and size limits (10MB max) enforce security boundaries.

### Data Model

**Core Entities**:

1. **CrewMember**: Stores crew member information with unique code (up to 20 chars, supporting 12+ members), name, and optional payment handle (IBAN/PayPal/Revolut)

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

### Security

**Security Measures**:
- File upload validation (type, size, sanitized storage)
- UUID-based filename generation to prevent directory traversal
- Input validation through Pydantic schemas
- No authentication required - designed for trusted crew environments on isolated sailing trips

**Design Philosophy**: Prioritizes simplicity and instant access over authentication complexity. The app is intended for temporary use during a single sailing trip with a small, trusted group. Data is not persisted beyond the trip duration.

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
- **python-dotenv**: Environment variable management
- **Starlette**: ASGI framework (FastAPI dependency)

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
- No environment variables required (authentication removed)

### No External Services
The application is designed to run completely self-contained without external APIs, cloud storage, or third-party authentication services. This ensures functionality even in offline/boat environments.