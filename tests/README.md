# Crew Wallet Test Suite

Comprehensive test suite for Crew Wallet - Bordkasse application.

## Test Coverage

### 1. Timezone Handling (`test_timezone.py`)
✅ **6 Tests** - New timezone features for crew departure filtering

- **UTC Timezone Conversion**
  - CET (UTC+1) timezone conversion 
  - PST (UTC-8) timezone conversion
  
- **Crew Departure Filtering**
  - Expense after departure excludes departed crew
  - Expense before departure includes departed crew
  
- **Backdated Expenses**
  - Backdated expense includes crew who departed later
  - Real-time expense excludes departed crew

### 2. Balance Calculation (`test_balances.py`)
✅ **7 Tests** - Core balance and settlement logic

- **Balance Calculations**
  - Simple deposit balance
  - Equal split calculation
  - Participants split calculation
  - Percentage split calculation
  - Private expense calculation

- **Settlement Algorithm**
  - Simple settlement transfers
  - Complex settlement minimizes transfers (greedy algorithm)

### 3. Core Functionality (`test_core_functionality.py`)
✅ **13 Tests** - Regression tests for existing features

- **Trip Management**
  - Create trip
  - Close trip
  - Trip date range validation

- **Crew Management**
  - Create crew member
  - Crew member limit (12 max)
  - Unique crew codes per trip

- **Deposit Management**
  - Create deposit
  - Multiple deposits per member

- **Expense Management**
  - Wallet-paid expenses
  - Private-paid expenses
  - Multiple expense categories

- **Data Integrity**
  - Expenses belong to correct trip
  - Deposits belong to correct member

### 4. Permissions & Authorization (`test_permissions.py`)
✅ **6 Tests** - Security and authorization

- **Trip Admin**
  - Trip admin flag designation
  - Maximum 2 trip admins per trip

- **Closed Trip Protection**
  - Closed trip flag
  - Read-only for crew members

- **Data Scoping**
  - Crew members scoped to trips
  - Expenses scoped to trips

## Running Tests

### Quick Run
```bash
./run_tests.sh
```

### Manual Run
```bash
python3 -m pytest tests/ -v
```

### With HTML Report
```bash
python3 -m pytest tests/ -v --html=test_report.html --self-contained-html
```

### Run Specific Test File
```bash
python3 -m pytest tests/test_timezone.py -v
```

### Run Specific Test
```bash
python3 -m pytest tests/test_timezone.py::TestTimezoneConversion::test_utc_conversion_cet_timezone -v
```

## Test Database

Tests use an **isolated in-memory SQLite database** that is:
- Created fresh for each test
- Completely isolated from development and production databases
- Automatically cleaned up after each test
- Fast and requires no external dependencies

## Test Results

**All 32 tests pass** ✅

The test suite validates:
- ✅ New timezone conversion features work correctly
- ✅ Crew departure filtering excludes departed members accurately
- ✅ Backdated expenses include appropriate crew members
- ✅ All balance calculation modes work correctly
- ✅ Settlement algorithm minimizes transfers
- ✅ Core functionality (trips, crew, deposits, expenses) works
- ✅ Permissions and data scoping are enforced

## Pre-Deployment Checklist

Before deploying to production:

1. ✅ Run the full test suite: `./run_tests.sh`
2. ✅ Verify all 32 tests pass
3. ✅ Review the HTML test report (`test_report.html`)
4. ✅ Confirm server restarts without errors
5. ✅ Manually test critical user flows in development

## Notes

- Tests are safe to run repeatedly
- No impact on development or production databases
- Quick execution (~2 seconds for full suite)
- Clear pass/fail indicators
- Detailed HTML report generation

Ready for production deployment! 🚀
