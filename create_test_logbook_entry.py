"""
Create a test logbook entry with realistic sailing data for PDF export testing.
"""

from datetime import datetime, timedelta
from db import SessionLocal
from models import LogbookEntry, Trip, CrewMember

def create_test_entry():
    """Create a realistic test logbook entry"""
    db = SessionLocal()
    
    try:
        # Get the first active trip (use status='active' instead of is_closed)
        trip = db.query(Trip).filter(Trip.status == 'active').first()
        if not trip:
            # Try getting any trip
            trip = db.query(Trip).first()
        
        if not trip:
            print("❌ No trip found. Please create a trip first.")
            return None
        
        print(f"✅ Using trip: {trip.name}")
        
        # Get first crew member as watch leader
        watch_leader = db.query(CrewMember).filter(CrewMember.trip_id == trip.id).first()
        
        # Create realistic test entry
        test_entry = LogbookEntry(
            trip_id=trip.id,
            watch_leader_id=watch_leader.id if watch_leader else None,
            entry_date=datetime.now(),
            entry_date_utc=datetime.utcnow(),
            
            # GPS Position (Fredericia, Denmark area)
            latitude=55.5647,
            longitude=9.7529,
            
            # Navigation data
            cog_deg=135,  # Heading SE
            sog_kn=6.5,   # 6.5 knots speed
            log_kn=6.2,   # Log speed
            dist_day_nm=42.3,  # 42.3 nautical miles today
            
            # Weather data
            pressure_hpa=1018,
            pressure_trend='rising',
            weather_source='GPS + Barometer',
            wind_direction='SW',
            wind_strength='4 Bft (11-16 kn)',
            sea_state='slight',
            visibility='Good (5-10 nm)',
            temperature=18.5,
            
            # Engine tracking
            engine_on=False,
            engine_on_time=datetime.now() - timedelta(hours=3),
            engine_off_time=datetime.now() - timedelta(hours=1, minutes=30),
            eng_hours_total=125.8,  # Total engine hours
            fuel_level_l=80.0,
            
            # Sails (in-mast furling)
            main_furl_pct=75,  # Mainsail 75% out
            headsail='Genua gesetzt',
            sail_action='Segel gesetzt bei gutem Wind',
            sail_plan='Groß (75%) + Genua',
            
            # Port/destination
            departure='Fredericia DK',
            destination='Ærøskøbing',
            
            # Events
            event_category='Navigation',
            event_details='Schöner Segeltag, konstanter SW-Wind 4 Bft, Kurs auf Ærøskøbing',
            
            # Notes
            notes='Perfekte Segelbedingungen. Crew arbeitet gut zusammen. Autopilot aktiviert auf Kurs 135°.',
            
            # Safety
            safety_checks_completed='Rettungswesten überprüft, Feuer löscher griffbereit, MOB-Ausrüstung bereit',
            
            # Legacy fields
            engine_hours=125.8
        )
        
        db.add(test_entry)
        db.commit()
        db.refresh(test_entry)
        
        print(f"\n✅ Test logbook entry created!")
        print(f"   ID: {test_entry.id}")
        print(f"   Date: {test_entry.entry_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Position: {test_entry.latitude}°N, {test_entry.longitude}°E")
        print(f"   SOG: {test_entry.sog_kn} kn, COG: {test_entry.cog_deg}°")
        print(f"   Motor hours: {test_entry.eng_hours_total}h")
        print(f"   Sails: Mainsail {test_entry.main_furl_pct}%, {test_entry.headsail}")
        print(f"   Watch leader: {watch_leader.name if watch_leader else 'None'}")
        print(f"\n📄 To export PDF, visit:")
        print(f"   https://YOUR_DOMAIN/logbook/export/pdf/entry/{test_entry.id}")
        
        return test_entry.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test entry: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    create_test_entry()
