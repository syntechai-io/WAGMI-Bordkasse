"""
Test script to verify settlement calculation for Kykladen 2025 trip.
This script calculates expected settlement values and compares with actual.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from routers.balances import calculate_balances
from settlement import compute_settlement

# Get database connection
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

# Kykladen 2025 trip ID
TRIP_ID = 6

print("=" * 80)
print("SETTLEMENT CALCULATION TEST - Kykladen 2025")
print("=" * 80)

# Calculate balances using the actual function
balances, settlement_net_map = calculate_balances(db, TRIP_ID)

print("\n1. INDIVIDUAL BALANCES (before grouping):")
print("-" * 80)
print(f"{'Code':<15} {'Name':<25} {'Paid':<12} {'Owed':<12} {'Net':<12} {'Status':<10}")
print("-" * 80)

individual_nets = {}
for balance in balances:
    member = balance["member"]
    individual_nets[member.code] = balance["net"]
    grouped_info = ""
    if balance.get("grouped"):
        if balance.get("is_representative"):
            grouped_info = f" [Group: {balance.get('group_name')} - Representative]"
        else:
            grouped_info = f" [Group: {balance.get('group_name')} - Member of {balance.get('representative_code')}]"
    
    print(f"{member.code:<15} {member.name:<25} {balance['paid_total']:>10.2f}€ {balance['share_owed']:>10.2f}€ {balance['net']:>10.2f}€ {balance['status']:<10}{grouped_info}")

print("-" * 80)
total_net = sum(individual_nets.values())
print(f"{'TOTAL (should be ~0)':<40} {total_net:>10.2f}€")

print("\n2. SETTLEMENT NET MAP (after group aggregation):")
print("-" * 80)
print(f"{'Code':<15} {'Net Amount':<15} {'Status':<20}")
print("-" * 80)

creditors = []
debtors = []
for code, net in sorted(settlement_net_map.items(), key=lambda x: x[1], reverse=True):
    status = "RECEIVES" if net > 0.01 else "PAYS" if net < -0.01 else "SETTLED"
    print(f"{code:<15} {net:>12.2f}€ {status:<20}")
    if net > 0.01:
        creditors.append((code, net))
    elif net < -0.01:
        debtors.append((code, abs(net)))

print("-" * 80)
total_creditors = sum(net for _, net in creditors)
total_debtors = sum(net for _, net in debtors)
print(f"{'Total to receive:':<15} {total_creditors:>12.2f}€")
print(f"{'Total to pay:':<15} {total_debtors:>12.2f}€")
print(f"{'Difference:':<15} {abs(total_creditors - total_debtors):>12.2f}€")

print("\n3. OPTIMIZED SETTLEMENT TRANSFERS:")
print("-" * 80)
transfers = compute_settlement(settlement_net_map)
print(f"{'From':<15} {'To':<15} {'Amount':<15}")
print("-" * 80)

if transfers:
    for from_code, to_code, amount in transfers:
        print(f"{from_code:<15} {to_code:<15} {amount:>12.2f}€")
    print("-" * 80)
    print(f"Total transfers needed: {len(transfers)}")
else:
    print("No transfers needed - all settled!")

print("\n4. EXPECTED VALUES (manual calculation):")
print("-" * 80)
print("Total expenses: 2,903.40 EUR")
print("Crew count: 10")
print("Per person share: 290.34 EUR")
print("\nExpected settlement net map:")
expected = {
    "Sven": 1137.13 - 290.34 - 290.34,  # Niederheides: Sven + Hanni
    "Mario": 810.88 - 290.34 - 290.34,   # A&M: Mario + Andrea
    "Robert": 329.49 - 290.34,           # Solo
    "Kathi": 348.00 - 290.34 - 290.34,   # Kathi&Viktor: Kathi + Victor
    "Nicole": 278.00 - 290.34 - 290.34,  # Nicole&Pia: Nicole + Pia
    "Nicola Georg": 0 - 290.34,          # Solo
}

for code, expected_net in sorted(expected.items(), key=lambda x: x[1], reverse=True):
    actual_net = settlement_net_map.get(code, 0.0)
    match = "✓" if abs(expected_net - actual_net) < 0.01 else "✗ MISMATCH!"
    print(f"{code:<15} Expected: {expected_net:>10.2f}€  Actual: {actual_net:>10.2f}€  {match}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

db.close()
