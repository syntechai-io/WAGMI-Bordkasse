# WAGMI CrewLog - Test Suite Documentation

## Overview

This test suite provides comprehensive end-to-end testing for the WAGMI CrewLog application. It validates all functionality including authentication, trip management, crew operations, logbook entries, financial transactions, calculations, exports, and PWA features.

## Test Coverage

### ✅ Authentication & Sessions
- Login/logout flows for Admin and Crew roles
- Session persistence across requests
- Protected route authentication
- Invalid credential handling

### ✅ Trip Management
- Trip creation with dates
- Active trip switching
- Trip archiving
- Data isolation per trip

### ✅ Crew Management
- Create, edit, delete crew members
- Duplicate code validation
- Code length validation (up to 20 chars)
- IBAN/payment handle storage

### ✅ Deposits
- Create deposits in EUR, DKK, SEK, GBP
- Multi-currency conversion to EUR
- Edit and delete operations
- Date and note handling

### ✅ Expenses
- Create expenses with equal/participant split modes
- Receipt file uploads (PDF, JPG, PNG)
- Multi-currency support
- Wallet vs. private payment tracking
- Category and description fields

### ✅ Balance & Settlement
- Balance calculations
- Settlement algorithm recommendations
- EUR conversion accuracy

### ✅ PDF Export
- PDF generation and download
- Trip data inclusion
- File integrity validation

### ✅ PWA Features
- Manifest accessibility and configuration
- App icons (192x192, 512x512)
- Service worker registration
- Offline capability

### ✅ Edge Cases & Validation
- Negative amount rejection
- Invalid currency rejection
- Crew deletion with dependencies

## Setup Instructions

### 1. Install Dependencies

The test suite requires `pytest` and `requests`:

```bash
# Already installed in this project
pytest --version
```

### 2. Configure Test Environment

Set environment variables for your deployment:

```bash
# For local testing (default)
export TEST_BASE_URL="http://localhost:5000"

# For testing published/deployed app
export TEST_BASE_URL="https://your-app-url.replit.app"

# Set admin/crew passwords (if different from defaults)
export ADMIN_PASSWORD="your_admin_password"
export CREW_PASSWORD="your_crew_password"
```

### 3. Verify Configuration

Check that `test_config.py` is correctly configured:

```python
# test_config.py will use these defaults:
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")
ADMIN_CREDENTIALS = {"username": "admin", "password": os.getenv("ADMIN_PASSWORD", "admin123")}
CREW_CREDENTIALS = {"username": "crew", "password": os.getenv("CREW_PASSWORD", "crew123")}
```

## Running Tests

### Run All Tests

```bash
pytest test_app_e2e.py -v
```

### Run Specific Test Categories

```bash
# Test only authentication
pytest test_app_e2e.py -v -k "test_auth"

# Test only trip management
pytest test_app_e2e.py -v -k "TestTripManagement"

# Test only financial operations
pytest test_app_e2e.py -v -k "TestDeposits or TestExpenses"

# Test only PWA features
pytest test_app_e2e.py -v -k "TestPWA"
```

### Generate HTML Report

```bash
pytest test_app_e2e.py -v --html=test_report.html --self-contained-html
```

### Run with Detailed Output

```bash
# Show print statements and detailed failures
pytest test_app_e2e.py -v -s

# Stop on first failure
pytest test_app_e2e.py -v -x

# Show slowest tests
pytest test_app_e2e.py -v --durations=10
```

## Testing Published App

### Before Publishing

```bash
# Test locally first
export TEST_BASE_URL="http://localhost:5000"
pytest test_app_e2e.py -v
```

### After Publishing

```bash
# Test your deployed app
export TEST_BASE_URL="https://your-app.replit.app"
export ADMIN_PASSWORD="your_actual_admin_password"
export CREW_PASSWORD="your_actual_crew_password"
pytest test_app_e2e.py -v
```

## Understanding Test Results

### ✅ Successful Test Run

```
test_app_e2e.py::TestAuthentication::test_login_page_accessible PASSED
test_app_e2e.py::TestAuthentication::test_admin_login_success PASSED
test_app_e2e.py::TestAuthentication::test_crew_login_success PASSED
...
======================== 35 passed in 12.5s =========================
```

### ❌ Failed Test

```
test_app_e2e.py::TestAuthentication::test_admin_login_success FAILED

E   AssertionError: Admin login failed: 401
E   assert 401 == 303
```

This indicates an authentication issue - check credentials.

### ⚠️ Common Issues

**1. Connection Refused**
```
requests.exceptions.ConnectionError: Connection refused
```
→ Server not running. Start with `uvicorn main:app --host 0.0.0.0 --port 5000`

**2. Authentication Failed**
```
AssertionError: Admin login failed: 200
```
→ Wrong credentials. Check ADMIN_PASSWORD and CREW_PASSWORD environment variables.

**3. 404 Not Found**
```
assert response.status_code == 200  # was 404
```
→ Route doesn't exist. Check if feature is implemented.

## Test Suite Structure

### Fixtures

- `admin_session`: Pre-authenticated admin session
- `crew_session`: Pre-authenticated crew session

### Helper Classes

- `TestSession`: Manages HTTP sessions with cookies
  - `login(username, password)`: Authenticate user
  - `logout()`: Clear session
  - `get(path)`: Authenticated GET request
  - `post(path, data)`: Authenticated POST request

### Test Classes

1. `TestAuthentication` - Login/logout flows
2. `TestTripManagement` - Trip CRUD operations
3. `TestCrewManagement` - Crew member operations
4. `TestDeposits` - Deposit creation and currency
5. `TestExpenses` - Expense tracking and receipts
6. `TestBalanceAndSettlement` - Calculations
7. `TestExport` - PDF generation
8. `TestPWA` - Progressive Web App features
9. `TestEdgeCases` - Error handling

## Continuous Testing

### Pre-Deployment Checklist

```bash
# 1. Test locally
export TEST_BASE_URL="http://localhost:5000"
pytest test_app_e2e.py -v

# 2. Generate report
pytest test_app_e2e.py -v --html=pre_deploy_report.html

# 3. Review results
# All tests should pass before publishing
```

### Post-Deployment Verification

```bash
# 1. Test published app
export TEST_BASE_URL="https://your-app.replit.app"
pytest test_app_e2e.py -v

# 2. Verify critical flows
pytest test_app_e2e.py -v -k "test_login or test_create or test_export"

# 3. Generate production report
pytest test_app_e2e.py -v --html=production_report.html
```

## Adding New Tests

### Example: Test New Feature

```python
class TestNewFeature:
    """Test description"""
    
    def test_feature_works(self, admin_session):
        """Test should do X"""
        response = admin_session.get("/new-feature")
        assert response.status_code == 200
        assert "expected content" in response.text
```

### Best Practices

1. **Use descriptive test names**: `test_deposit_eur_conversion`
2. **One assertion per test** (when possible)
3. **Use fixtures** for authentication
4. **Clean up test data** when necessary
5. **Test both success and failure** cases

## Performance Benchmarks

Expected test execution times:

- Full suite: ~15-30 seconds
- Authentication: ~2 seconds
- Financial operations: ~5 seconds
- Export tests: ~3 seconds
- PWA tests: ~1 second

Slower execution may indicate:
- Network latency (if testing remote deployment)
- Database performance issues
- External API delays (currency conversion)

## Troubleshooting

### Issue: Tests timeout

```bash
# Increase timeout in test_config.py
TEST_TIMEOUT = 60  # seconds
```

### Issue: Session cookies not working

```python
# Check session configuration in test
session.session.cookies  # Should contain session cookie
```

### Issue: File upload tests fail

```python
# Verify multipart form data is correct
# Check file size limits (max 10MB for receipts)
```

## i18n Hardcoded-String Regression

`test_i18n_no_hardcoded_strings.py` scans every file under `templates/` and
fails the build if it finds German-only characters (`ä`, `ö`, `ü`, `ß`, …) or
known German words (`Törn`, `Statistik`, …) outside `{{ t('your.key') }}`
calls and template comments. It also cross-checks that every `t('foo.bar')`
referenced in a template exists in both `locales/de.json` and
`locales/en.json`.

Run it with the rest of the suite via `pytest`, or on its own:

```bash
pytest test_i18n_no_hardcoded_strings.py -v
```

### Adding a legitimate exception

If a German-looking token is intentional (date format, brand name, proper
noun used in both languages), add a tuple `(template_filename, snippet)` to
the `ALLOWLIST` constant at the top of `test_i18n_no_hardcoded_strings.py`.
The `snippet` is matched as a substring of the offending line — keep it
short and unique. Add a one-line comment explaining why the exception is
legitimate.

For translation keys that are intentionally staged but not yet present in
both locale files, add the key to `MISSING_KEY_ALLOWLIST` in the same file.

## Support

For issues with the test suite:
1. Check test output for specific error messages
2. Verify environment configuration
3. Review recent changes to application code
4. Check server logs for backend errors

## Summary

This comprehensive test suite ensures WAGMI Bordkasse works flawlessly:

✅ **35+ test cases** covering all features  
✅ **Automated validation** of critical flows  
✅ **Pre/post-deployment** testing support  
✅ **HTML reports** for documentation  
✅ **Easy configuration** via environment variables  

Run `pytest test_app_e2e.py -v` to validate your app is production-ready!
