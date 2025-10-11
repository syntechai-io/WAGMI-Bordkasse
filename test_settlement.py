#!/usr/bin/env python3
"""
Test script for settlement calculation algorithm.
Tests various scenarios and verifies correctness with step-by-step calculation.
"""

from settlement import compute_settlement
from typing import Dict, List, Tuple

def print_scenario(title: str, net_map: Dict[str, float]):
    """Print test scenario details"""
    print(f"\n{'='*80}")
    print(f"📊 SZENARIO: {title}")
    print(f"{'='*80}")
    print("\n💰 Netto-Salden:")
    total_positive = 0
    total_negative = 0
    
    for code, amount in sorted(net_map.items()):
        status = "erhält" if amount > 0 else "zahlt" if amount < 0 else "ausgeglichen"
        print(f"  {code}: {amount:>8.2f} € ({status})")
        if amount > 0:
            total_positive += amount
        elif amount < 0:
            total_negative += amount
    
    print(f"\n✅ Summe Guthaben: {total_positive:.2f} €")
    print(f"❌ Summe Schulden:  {total_negative:.2f} €")
    print(f"⚖️  Balance-Check:  {total_positive + total_negative:.2f} € (sollte 0.00 sein)")

def verify_settlement(net_map: Dict[str, float], transfers: List[Tuple[str, str, float]]):
    """Verify settlement transfers are correct"""
    print("\n🔍 VERIFIZIERUNG:")
    
    # Calculate balances after transfers
    final_balance = {code: amount for code, amount in net_map.items()}
    
    for from_code, to_code, amount in transfers:
        final_balance[from_code] += amount  # debtor pays, reduces their negative
        final_balance[to_code] -= amount     # creditor receives, reduces their positive
    
    print("\n📋 Finale Salden nach Ausgleich:")
    all_settled = True
    for code, balance in sorted(final_balance.items()):
        settled = abs(balance) < 0.01
        status = "✅" if settled else "❌"
        print(f"  {status} {code}: {balance:>8.2f} €")
        if not settled:
            all_settled = False
    
    if all_settled:
        print("\n✅ ERFOLGREICH: Alle Salden ausgeglichen!")
    else:
        print("\n❌ FEHLER: Nicht alle Salden ausgeglichen!")
    
    return all_settled

def show_calculation_steps(net_map: Dict[str, float], transfers: List[Tuple[str, str, float]]):
    """Show step-by-step calculation"""
    print("\n📝 BERECHNUNGSSCHRITTE (Greedy-Algorithmus):")
    
    # Separate creditors and debtors
    creditors = [(code, amount) for code, amount in net_map.items() if amount > 0.01]
    debtors = [(code, -amount) for code, amount in net_map.items() if amount < -0.01]
    
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n1️⃣ Gläubiger (sortiert nach Betrag):")
    for code, amount in creditors:
        print(f"   {code}: {amount:.2f} €")
    
    print(f"\n2️⃣ Schuldner (sortiert nach Betrag):")
    for code, amount in debtors:
        print(f"   {code}: {amount:.2f} €")
    
    print(f"\n3️⃣ Greedy-Matching (größter Schuldner mit größtem Gläubiger):")
    for idx, (from_code, to_code, amount) in enumerate(transfers, 1):
        print(f"   Transfer {idx}: {from_code} → {to_code}: {amount:.2f} €")
    
    print(f"\n📊 Anzahl der Transaktionen: {len(transfers)}")

def run_test(title: str, net_map: Dict[str, float]):
    """Run a complete test scenario"""
    print_scenario(title, net_map)
    
    transfers = compute_settlement(net_map)
    
    print(f"\n⛵ AUSGLEICHS-TRANSFERS:")
    if not transfers:
        print("  Keine Transfers nötig - alle ausgeglichen!")
    else:
        for from_code, to_code, amount in transfers:
            print(f"  💸 {from_code} zahlt {amount:.2f} € an {to_code}")
    
    show_calculation_steps(net_map, transfers)
    success = verify_settlement(net_map, transfers)
    
    return success

# Test scenarios
def main():
    print("\n🌊 SETTLEMENT ALGORITHM TESTS 🌊")
    print("Testing verschiedene Ausgleichs-Szenarien\n")
    
    all_passed = True
    
    # Test 1: Einfaches Szenario (3 Personen)
    test1 = {
        "SN": 100.0,   # Sarah hat 100€ mehr bezahlt
        "AB": -40.0,   # Alex schuldet 40€
        "CD": -60.0    # Chris schuldet 60€
    }
    all_passed &= run_test("Test 1: Einfacher Fall (3 Personen)", test1)
    
    # Test 2: Komplexeres Szenario (4 Personen)
    test2 = {
        "SN": 150.0,   # Sarah erhält 150€
        "AB": 50.0,    # Alex erhält 50€
        "CD": -100.0,  # Chris zahlt 100€
        "MK": -100.0   # Maria zahlt 100€
    }
    all_passed &= run_test("Test 2: Zwei Gläubiger, zwei Schuldner", test2)
    
    # Test 3: Ungleiche Beträge (5 Personen)
    test3 = {
        "SN": 301.67,   # Sarah erhält 301.67€
        "AB": 61.67,    # Alex erhält 61.67€
        "CD": -45.00,   # Chris zahlt 45€
        "MK": -250.00,  # Maria zahlt 250€
        "SV": -68.34    # Sven zahlt 68.34€
    }
    all_passed &= run_test("Test 3: Ungleiche Beträge (5 Personen)", test3)
    
    # Test 4: Alle ausgeglichen
    test4 = {
        "SN": 0.0,
        "AB": 0.0,
        "CD": 0.0
    }
    all_passed &= run_test("Test 4: Alle bereits ausgeglichen", test4)
    
    # Test 5: Nur Rundungsfehler (sehr kleine Beträge)
    test5 = {
        "SN": 0.005,
        "AB": -0.003,
        "CD": -0.002
    }
    all_passed &= run_test("Test 5: Rundungsfehler (< 1 Cent)", test5)
    
    # Test 6: Realistisches Crew-Szenario
    test6 = {
        "SN": 301.67,   # Sarah: 400€ bezahlt - 98.33€ Anteil = +301.67€
        "AB": 301.67,   # Alex: 400€ bezahlt - 98.33€ Anteil = +301.67€
        "CD": 61.67,    # Chris: 160€ bezahlt - 98.33€ Anteil = +61.67€
        "MK": -45.00,   # Maria: 0€ bezahlt - 45€ Anteil = -45.00€
        "SV": 0.00      # Sven: 0€ bezahlt - 0€ Anteil (nicht dabei) = 0.00€
    }
    # Korrigiere Test 6 - die Salden müssen sich zu 0 addieren
    test6_corrected = {
        "SN": 200.0,
        "AB": 150.0,
        "CD": 50.0,
        "MK": -200.0,
        "SV": -200.0
    }
    all_passed &= run_test("Test 6: Realistisches Crew-Szenario", test6_corrected)
    
    # Final summary
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ ALLE TESTS BESTANDEN! Die Ausgleichsberechnung funktioniert korrekt.")
    else:
        print("❌ EINIGE TESTS FEHLGESCHLAGEN! Bitte Algorithmus überprüfen.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
