# Crew Wallet - Bordkasse

## Overview

Crew Wallet is a minimalist expense tracking and settlement application designed for sailing crew members to manage shared expenses during trips. The application features secure user authentication with two roles (Admin and Crew) and allows up to 12 crew members to track deposits into a shared wallet, record expenses (both from the wallet and private payments), and automatically calculate who owes whom at the end of the trip using an optimized settlement algorithm.

Key features:
- **Secure authentication system** - Session-based login with Admin and Crew roles
- Crew member management for up to 12 members with unique codes (up to 20 chars) and payment handles (IBAN/PayPal/etc.)
- Deposit tracking into shared wallet with **edit and delete** capabilities
- Expense recording with flexible split modes (equal split or specific participants) and **edit and delete** capabilities
- **Receipt upload directly when creating expenses** - optional file upload with camera integration on mobile devices
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
- **Implemented complete maritime/nautical UI theme** for sailing crew use case:
  - Maritime color palette: navy-deep (#1e3a5f), ocean-blue (#0077be), sea-foam (#2ecc71), coral (#ff6b35), sand (#d4a574)
  - Porthole-style cards with sky-blue rounded borders
  - Rope dividers with dashed sandy borders
  - Nautical emojis throughout (⚓🌊💰⛵📊👥📂)
  - Maritime gradient buttons (ocean, sea-foam, coral, purple with sailboat)
  - Ship wheel branding and anchor navigation icons
  - Wave-themed borders and maritime typography (Bebas Neue headers)
- **Implemented secure authentication system**:
  - Session-based authentication with SessionMiddleware
  - Two user roles: Admin (full access) and Crew (standard access)
  - Password hashing with werkzeug.security
  - Global auth middleware protecting all routes except /login
  - Secure login/logout flow with maritime-themed login page
  - Navigation displays logged-in user with logout button
  - All secrets (SESSION_SECRET, ADMIN_PASSWORD, CREW_PASSWORD) required from environment
  - No hardcoded credentials or fallback secrets for production security
- **Added receipt upload directly in expense creation form**:
  - Optional file upload field in "Ausgabe erfassen" form
  - Mobile camera integration via HTML5 capture attribute
  - Supports PDF, JPG, PNG (max 10MB)
  - Automatic redirect to detail page when receipt is uploaded
  - Simple and robust browser-native implementation
  - Receipt viewer page with navigation (Dashboard & Back buttons)
  - Users can always navigate back from receipt view
- **Integrated PayPal Money Pool link**:
  - Prominent PayPal Pool button on Dashboard and Einzahlungen page
  - Direct link to https://www.paypal.com/pool/9j4PpWiLVC?sr=ancr
  - Opens in new tab for easy crew deposits
  - Clear call-to-action: "Hier ins Wallet einzahlen"

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture

**Framework**: FastAPI (Python)
- Router-based modular structure with separate modules for crew, deposits, expenses, receipts, balances, export, and auth
- **Secure authentication** - Session-based login with Admin/Crew roles
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

2. **Authentication Model**: Session-based authentication with two roles (Admin and Crew). Admin has full access to all features including deleting records. Crew has standard access. Passwords are hashed with werkzeug.security. All routes except /login are protected by AuthMiddleware. The app requires SESSION_SECRET, ADMIN_PASSWORD, and CREW_PASSWORD from environment variables for security.

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

**Maritime UI Theme**:
- Complete nautical design aesthetic with ocean blues, sea-foam greens, coral oranges, and sandy gold
- Custom CSS properties for maritime color palette (--navy-deep, --ocean-blue, --sea-foam, --coral, --sand)
- Porthole-card styling for all containers (rounded borders with sky-blue color)
- Rope dividers for section separation (dashed sandy borders)
- Maritime gradient buttons and status badges throughout
- Nautical emojis and ship wheel branding
- Bebas Neue font for headers with maritime letter-spacing
- Zero Tailwind gray colors - 100% maritime palette compliance

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