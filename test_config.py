"""
Test configuration for WAGMI Bordkasse E2E tests.

Configure the base URL and credentials for testing against deployed app.
"""

import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")

ADMIN_CREDENTIALS = {
    "username": "Sven",
    "password": os.getenv("ADMIN_PASSWORD", "admin123")
}

CREW_CREDENTIALS = {
    "username": "crew",
    "password": os.getenv("CREW_PASSWORD", "crew123")
}

TEST_TIMEOUT = 30

SUPPORTED_CURRENCIES = ["EUR", "DKK", "SEK", "GBP"]

print(f"Test configuration loaded: BASE_URL={BASE_URL}")
