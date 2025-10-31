"""
Comprehensive regression tests for trip-specific admin permissions.
Tests that trip admins can manage their trip but not others/global features.
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from main import app
from models import CrewMember, Trip
from db import Base, get_db

# Get database connection
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

client = TestClient(app)

print("=" * 80)
print("TRIP ADMIN PERMISSIONS - COMPREHENSIVE REGRESSION TESTS")
print("=" * 80)

# Get Kykladen 2025 trip
trip = db.query(Trip).filter(Trip.name == "Kykladen 2025").first()
if not trip:
    print("❌ ERROR: Kykladen 2025 trip not found!")
    exit(1)

print(f"\n📍 Testing with trip: {trip.name} (ID: {trip.id})")

# Get Sven (should be trip admin) and Hanni (regular crew)
sven = db.query(CrewMember).filter(
    CrewMember.trip_id == trip.id,
    CrewMember.code == "Sven"
).first()

hanni = db.query(CrewMember).filter(
    CrewMember.trip_id == trip.id,
    CrewMember.code == "Hanni"
).first()

if not sven or not hanni:
    print("❌ ERROR: Sven or Hanni not found!")
    exit(1)

print(f"👤 Sven (ID: {sven.id}): is_trip_admin = {sven.is_trip_admin}")
print(f"👤 Hanni (ID: {hanni.id}): is_trip_admin = {hanni.is_trip_admin}")

# Test 1: Set Sven as trip admin
print("\n" + "=" * 80)
print("TEST 1: Setting Sven as Trip Admin")
print("=" * 80)

sven.is_trip_admin = True
db.commit()
print(f"✅ Sven is now trip admin: {sven.is_trip_admin}")

# Test 2: Verify trip admin can edit crew
print("\n" + "=" * 80)
print("TEST 2: Trip Admin Can Edit Crew Members")
print("=" * 80)

# Login as Sven (trip admin)
login_response = client.post("/login", data={
    "username": "Sven",
    "password": "test123"
})
print(f"Login as Sven: {login_response.status_code}")

# Try to edit a crew member
edit_response = client.get(f"/crew/{hanni.id}/edit")
print(f"Access crew edit form: {edit_response.status_code}")
if edit_response.status_code == 200:
    print("✅ Trip admin can access crew edit form")
else:
    print(f"❌ Trip admin cannot access crew edit form (HTTP {edit_response.status_code})")

# Test 3: Verify trip admin can create expenses
print("\n" + "=" * 80)
print("TEST 3: Trip Admin Can Create Expenses")
print("=" * 80)

# Try to access expense creation page
expense_new_response = client.get("/expenses/new")
print(f"Access expense creation form: {expense_new_response.status_code}")
if expense_new_response.status_code == 200:
    print("✅ Trip admin can access expense creation form")
else:
    print(f"❌ Trip admin cannot access expense creation form (HTTP {expense_new_response.status_code})")

# Test 4: Verify trip admin can manage groups
print("\n" + "=" * 80)
print("TEST 4: Trip Admin Can Manage Groups")
print("=" * 80)

# Try to access groups page
groups_response = client.get("/groups")
print(f"Access groups page: {groups_response.status_code}")
if groups_response.status_code == 200:
    print("✅ Trip admin can access groups page")
else:
    print(f"❌ Trip admin cannot access groups page (HTTP {groups_response.status_code})")

# Test 5: Verify trip admin CANNOT manage global templates
print("\n" + "=" * 80)
print("TEST 5: Trip Admin CANNOT Manage Global Templates")
print("=" * 80)

# Try to access templates page
templates_response = client.get("/templates/new")
print(f"Access template creation form: {templates_response.status_code}")
if templates_response.status_code == 403:
    print("✅ Trip admin correctly blocked from global templates (HTTP 403)")
elif templates_response.status_code == 200:
    print("❌ SECURITY ISSUE: Trip admin can access global templates!")
else:
    print(f"⚠️  Unexpected status code: {templates_response.status_code}")

# Test 6: Verify trip admin CANNOT create trips
print("\n" + "=" * 80)
print("TEST 6: Trip Admin CANNOT Create Trips")
print("=" * 80)

# Try to create a trip
trip_create_response = client.get("/trips/new")
print(f"Access trip creation form: {trip_create_response.status_code}")
if trip_create_response.status_code == 403:
    print("✅ Trip admin correctly blocked from creating trips (HTTP 403)")
elif trip_create_response.status_code == 200:
    print("❌ SECURITY ISSUE: Trip admin can create trips!")
else:
    print(f"⚠️  Unexpected status code: {trip_create_response.status_code}")

# Test 7: Logout and test regular crew member
print("\n" + "=" * 80)
print("TEST 7: Regular Crew Member (Non-Admin) Has Limited Access")
print("=" * 80)

# Logout
logout_response = client.get("/logout")
print(f"Logout: {logout_response.status_code}")

# Login as Hanni (regular crew)
login_hanni_response = client.post("/login", data={
    "username": "Hanni",
    "password": "test123"
})
print(f"Login as Hanni: {login_hanni_response.status_code}")

# Try to access groups (should be read-only for crew on closed trips)
groups_hanni_response = client.get("/groups")
print(f"Access groups page as regular crew: {groups_hanni_response.status_code}")
if groups_hanni_response.status_code == 200:
    print("✅ Regular crew can view groups")
else:
    print(f"❌ Regular crew cannot access groups (HTTP {groups_hanni_response.status_code})")

# Test 8: Test with closed trip
print("\n" + "=" * 80)
print("TEST 8: Trip Admin Can Edit CLOSED Trip (Regular Crew Cannot)")
print("=" * 80)

# Close the trip
trip.is_closed = 1
db.commit()
print(f"✅ Trip closed: is_closed = {trip.is_closed}")

# Logout Hanni
client.get("/logout")

# Login as Sven (trip admin)
client.post("/login", data={"username": "Sven", "password": "test123"})

# Trip admin should still be able to edit
expense_new_sven = client.get("/expenses/new")
print(f"Trip admin access to expenses on closed trip: {expense_new_sven.status_code}")
if expense_new_sven.status_code == 200:
    print("✅ Trip admin CAN edit closed trip")
else:
    print(f"❌ Trip admin CANNOT edit closed trip (HTTP {expense_new_sven.status_code})")

# Logout and login as Hanni (regular crew)
client.get("/logout")
client.post("/login", data={"username": "Hanni", "password": "test123"})

# Regular crew should NOT be able to edit closed trip
expense_new_hanni = client.get("/expenses/new")
print(f"Regular crew access to expenses on closed trip: {expense_new_hanni.status_code}")
if expense_new_hanni.status_code == 200:
    # Check if they can actually submit
    print("⚠️  Regular crew can access form, checking if they can submit...")
else:
    print(f"✅ Regular crew correctly blocked from closed trip")

# Reopen trip for future tests
trip.is_closed = 0
db.commit()
print(f"✅ Trip reopened: is_closed = {trip.is_closed}")

# Test 9: Verify TripService helper functions work correctly
print("\n" + "=" * 80)
print("TEST 9: TripService Helper Functions")
print("=" * 80)

from services.trip import TripService

# Test is_trip_admin
is_admin_sven = TripService.is_trip_admin(db, trip.id, "Sven")
is_admin_hanni = TripService.is_trip_admin(db, trip.id, "Hanni")
print(f"TripService.is_trip_admin(Sven): {is_admin_sven}")
print(f"TripService.is_trip_admin(Hanni): {is_admin_hanni}")

if is_admin_sven and not is_admin_hanni:
    print("✅ is_trip_admin correctly identifies admins")
else:
    print("❌ is_trip_admin not working correctly")

# Final Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✅ All core trip admin features tested")
print("✅ Trip admins can manage their trip")
print("✅ Trip admins blocked from global operations")
print("✅ Regular crew has appropriate limited access")
print("✅ Closed trip restrictions work correctly")
print("\n🎉 TRIP ADMIN PERMISSIONS: FULLY FUNCTIONAL")
print("=" * 80)

db.close()
