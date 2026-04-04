from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import Trip, LogbookEntry, TripStatus
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

class WagmiAnnualReportService:
    """Service for generating yearly sailing reports"""

    @staticmethod
    def get_yearly_report(db: Session, account_id: int = 1, start_year: Optional[int] = None) -> Dict[int, Dict]:
        """
        Generate yearly report for all trips in the given account.

        Args:
            db: Database session
            account_id: Account to scope the report to
            start_year: First year to include (default: auto-detected from earliest trip)

        Returns:
            Dictionary with years as keys and aggregated statistics as values
        """
        current_year = datetime.now().year

        # Base query — all trips for the account with a start date (no name filter)
        base_query = db.query(Trip).filter(
            Trip.account_id == account_id,
            Trip.start_date.isnot(None),
        )

        # Auto-detect the earliest year if not specified
        if start_year is None:
            earliest = base_query.order_by(Trip.start_date.asc()).first()
            start_year = earliest.start_date.year if earliest else current_year

        # Fetch all trips from start_year onwards
        all_trips = base_query.filter(
            extract('year', Trip.start_date) >= start_year
        ).order_by(Trip.start_date.asc()).all()

        # Group trips by year
        trips_by_year = defaultdict(list)
        for trip in all_trips:
            if trip.start_date:
                year = trip.start_date.year
                trips_by_year[year].append(trip)

        # Calculate statistics for each year
        yearly_stats = {}
        for year in range(start_year, current_year + 1):
            trips = trips_by_year.get(year, [])
            
            if not trips:
                # Include year even if no trips for completeness
                yearly_stats[year] = {
                    'year': year,
                    'trip_count': 0,
                    'trips': [],
                    'total_nm': 0,
                    'motor_hours': 0,
                    'sail_hours': 0,
                    'incidents': 0
                }
                continue
            
            # Aggregate statistics across all trips in the year
            total_nm = 0
            total_motor_hours = 0
            total_sail_hours = 0
            total_incidents = 0
            trip_details = []
            
            for trip in trips:
                trip_stats = WagmiAnnualReportService._calculate_trip_stats(db, trip)
                
                total_nm += trip_stats['nautical_miles']
                total_motor_hours += trip_stats['motor_hours']
                total_sail_hours += trip_stats['sail_hours']
                total_incidents += trip_stats['incidents']
                
                trip_details.append({
                    'id': trip.id,
                    'name': trip.name,
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'status': trip.status.value,
                    'nautical_miles': trip_stats['nautical_miles'],
                    'motor_hours': trip_stats['motor_hours'],
                    'sail_hours': trip_stats['sail_hours'],
                    'incidents': trip_stats['incidents'],
                    'entry_count': trip_stats['entry_count']
                })
            
            yearly_stats[year] = {
                'year': year,
                'trip_count': len(trips),
                'trips': trip_details,
                'total_nm': round(total_nm, 1),
                'motor_hours': round(total_motor_hours, 1),
                'sail_hours': round(total_sail_hours, 1),
                'incidents': total_incidents
            }
        
        return yearly_stats
    
    @staticmethod
    def _calculate_trip_stats(db: Session, trip: Trip) -> Dict:
        """
        Calculate statistics for a single trip from its logbook entries.
        
        Args:
            db: Database session
            trip: Trip object
            
        Returns:
            Dictionary with trip statistics
        """
        entries = db.query(LogbookEntry).filter(
            LogbookEntry.trip_id == trip.id
        ).order_by(LogbookEntry.entry_date.asc()).all()
        
        if not entries:
            return {
                'nautical_miles': 0,
                'motor_hours': 0,
                'sail_hours': 0,
                'incidents': 0,
                'entry_count': 0
            }
        
        # Calculate nautical miles (sum of daily distances)
        nautical_miles = sum(
            entry.dist_day_nm for entry in entries 
            if entry.dist_day_nm is not None
        )
        
        # Calculate motor hours (delta between max and min engine hours if available)
        engine_hours_readings = [
            entry.eng_hours_total for entry in entries 
            if entry.eng_hours_total is not None
        ]
        motor_hours = 0
        if len(engine_hours_readings) >= 2:
            motor_hours = max(engine_hours_readings) - min(engine_hours_readings)
        
        # Calculate sail hours (approximate from entries with sails and engine off)
        sail_hours = 0
        for i, entry in enumerate(entries):
            if i == 0:
                continue
            
            prev_entry = entries[i - 1]
            
            # Check if sails are deployed (sail_plan set or main_furl_pct < 100)
            sails_deployed = (
                entry.sail_plan is not None or 
                (entry.main_furl_pct is not None and entry.main_furl_pct < 100) or
                entry.headsail is not None
            )
            
            # If sails are deployed and engine is off, count the time difference
            if (sails_deployed and 
                entry.engine_on is False and 
                prev_entry.entry_date and 
                entry.entry_date):
                
                time_diff = entry.entry_date - prev_entry.entry_date
                hours = time_diff.total_seconds() / 3600
                sail_hours += hours
        
        # Count incidents (entries marked with specific incident-related events)
        incident_keywords = ['incident', 'emergency', 'damage', 'medical', 'collision', 'grounding', 'fire', 'injury']
        incidents = sum(
            1 for entry in entries 
            if (entry.event_category and 
                any(keyword in entry.event_category.lower() for keyword in incident_keywords))
        )
        
        return {
            'nautical_miles': nautical_miles,
            'motor_hours': motor_hours,
            'sail_hours': sail_hours,
            'incidents': incidents,
            'entry_count': len(entries)
        }
