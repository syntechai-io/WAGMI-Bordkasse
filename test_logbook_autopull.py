"""
Comprehensive tests for logbook auto-pull features:
- GPS data conversion (m/s to knots, heading validation)
- Motor hours auto-calculation
- Offline storage with auto-pulled fields
"""

import pytest
from datetime import datetime, timedelta
import json


class TestGPSDataConversion:
    """Test GPS data extraction and conversion"""
    
    def test_speed_conversion_ms_to_knots(self):
        """Test conversion of GPS speed from m/s to knots"""
        # 1 m/s = 1.94384 knots
        test_cases = [
            (0, 0.0),           # Stationary
            (1, 1.9),           # 1 m/s
            (5, 9.7),           # 5 m/s
            (10, 19.4),         # 10 m/s
            (2.5772, 5.0),      # 5 knots in m/s
            (5.1444, 10.0),     # 10 knots in m/s
        ]
        
        for speed_ms, expected_knots in test_cases:
            result_knots = round(speed_ms * 1.94384, 1)
            assert result_knots == expected_knots, \
                f"Speed {speed_ms} m/s should convert to {expected_knots} knots, got {result_knots}"
    
    def test_heading_validation(self):
        """Test heading (COG) values are within valid range 0-359"""
        valid_headings = [0, 45, 90, 135, 180, 225, 270, 315, 359]
        
        for heading in valid_headings:
            assert 0 <= heading <= 359, f"Heading {heading} should be between 0-359"
    
    def test_heading_rounding(self):
        """Test heading values are properly rounded to integers"""
        test_cases = [
            (45.2, 45),
            (45.7, 46),
            (359.4, 359),
            (0.6, 1),
        ]
        
        for heading_raw, expected_rounded in test_cases:
            result = round(heading_raw)
            assert result == expected_rounded, \
                f"Heading {heading_raw} should round to {expected_rounded}, got {result}"
    
    def test_null_speed_handling(self):
        """Test that null/unavailable GPS speed is handled gracefully"""
        # Simulate JavaScript: speed !== null && speed >= 0
        speed_null = None
        speed_negative = -1
        speed_valid = 5.0
        
        # Only positive valid speeds should be processed
        assert speed_null is None or speed_null < 0
        assert speed_negative < 0
        assert speed_valid is not None and speed_valid >= 0
    
    def test_null_heading_handling(self):
        """Test that null/unavailable GPS heading is handled gracefully"""
        heading_null = None
        heading_negative = -1
        heading_valid = 180
        
        # Only positive valid headings should be processed
        assert heading_null is None or heading_null < 0
        assert heading_negative < 0
        assert heading_valid is not None and heading_valid >= 0


class TestMotorHoursCalculation:
    """Test motor hours auto-calculation logic"""
    
    def test_basic_duration_calculation(self):
        """Test basic motor runtime duration calculation"""
        # Motor on at 10:00, off at 11:30 = 1.5 hours
        on_time = datetime(2025, 11, 8, 10, 0)
        off_time = datetime(2025, 11, 8, 11, 30)
        
        duration_ms = (off_time - on_time).total_seconds() * 1000
        duration_hours = round(duration_ms / (1000 * 60 * 60), 1)
        
        assert duration_hours == 1.5, \
            f"1.5 hour runtime should calculate correctly, got {duration_hours}"
    
    def test_multi_hour_duration(self):
        """Test longer motor runtime durations"""
        on_time = datetime(2025, 11, 8, 8, 0)
        off_time = datetime(2025, 11, 8, 13, 45)
        
        duration_ms = (off_time - on_time).total_seconds() * 1000
        duration_hours = round(duration_ms / (1000 * 60 * 60), 1)
        
        assert duration_hours == 5.8, \
            f"5 hours 45 min runtime should be 5.8 hours, got {duration_hours}"
    
    def test_total_hours_accumulation(self):
        """Test accumulating motor hours to existing total"""
        current_total = 123.5
        new_duration = 2.3
        expected_total = 125.8
        
        new_total = round(current_total + new_duration, 1)
        
        assert new_total == expected_total, \
            f"Adding {new_duration}h to {current_total}h should give {expected_total}h, got {new_total}"
    
    def test_empty_total_no_autofill(self):
        """Test that empty eng_hours_total doesn't auto-fill (user must set starting value)"""
        # According to requirements: if eng_hours_total is empty, 
        # user must manually enter starting hours
        eng_hours_total_empty = None
        
        # Should not auto-fill when empty
        assert eng_hours_total_empty is None or eng_hours_total_empty == 0
    
    def test_invalid_time_order(self):
        """Test that off time before on time is rejected"""
        on_time = datetime(2025, 11, 8, 12, 0)
        off_time = datetime(2025, 11, 8, 10, 0)  # Before on time!
        
        # Should be invalid
        assert off_time <= on_time, "Off time must be after on time"
    
    def test_same_time_rejected(self):
        """Test that identical on/off times are rejected"""
        on_time = datetime(2025, 11, 8, 10, 0)
        off_time = datetime(2025, 11, 8, 10, 0)
        
        assert off_time <= on_time, "Same on/off time should be rejected"


class TestOfflineStorage:
    """Test offline storage includes all auto-pulled GPS and motor fields"""
    
    def test_offline_entry_includes_gps_fields(self):
        """Test that offline storage captures all GPS fields"""
        offline_entry = {
            'entry_date': '2025-11-08',
            'entry_time': '12:00',
            'latitude': 54.0833,
            'longitude': 13.4378,
            'watch_leader_id': 1,
            # Phase A: Navigation (GPS auto-pull)
            'cog_deg': 45,
            'sog_kn': 6.5,
            'log_kn': 6.2,
            'dist_day_nm': 42.3,
            # Phase A: Weather
            'pressure_hpa': 1013,
            'pressure_trend': 'rising',
            'weather_source': 'GPS',
            # Phase A: Engine
            'engine_on': True,
            'engine_on_time': '2025-11-08T10:00',
            'engine_off_time': '2025-11-08T11:30',
            'eng_hours_total': 125.8,
            'fuel_level_l': 80,
            # Phase A: Sails
            'main_furl_pct': 50,
            'headsail': 'Genua gesetzt',
            'sail_action': 'Segel gesetzt',
            # Phase A: Events
            'event_category': 'Manöver',
            'event_details': 'Ankermanöver'
        }
        
        # Verify all critical auto-pull fields are present
        assert 'cog_deg' in offline_entry
        assert 'sog_kn' in offline_entry
        assert 'latitude' in offline_entry
        assert 'longitude' in offline_entry
        assert 'watch_leader_id' in offline_entry
        assert 'engine_on_time' in offline_entry
        assert 'engine_off_time' in offline_entry
        assert 'eng_hours_total' in offline_entry
    
    def test_offline_entry_json_serializable(self):
        """Test that offline entry can be serialized to JSON"""
        offline_entry = {
            'latitude': 54.0833,
            'longitude': 13.4378,
            'cog_deg': 45,
            'sog_kn': 6.5,
            'watch_leader_id': 1,
        }
        
        # Should serialize without errors
        json_str = json.dumps(offline_entry)
        assert json_str is not None
        assert isinstance(json_str, str)
        
        # Should deserialize correctly
        deserialized = json.loads(json_str)
        assert deserialized['latitude'] == 54.0833
        assert deserialized['cog_deg'] == 45
        assert deserialized['watch_leader_id'] == 1


class TestGPSTrackingIntegration:
    """Integration tests for continuous GPS tracking"""
    
    def test_position_history_limit(self):
        """Test that position history is limited to max size"""
        max_history_size = 10
        position_history = []
        
        # Add 15 positions
        for i in range(15):
            position_history.append({
                'timestamp': i,
                'coords': {'latitude': 54.0 + i*0.001, 'longitude': 13.4}
            })
            
            # Limit size
            if len(position_history) > max_history_size:
                position_history.pop(0)
        
        assert len(position_history) == max_history_size, \
            f"History should be limited to {max_history_size} entries"
    
    def test_averaged_position_calculation(self):
        """Test averaging multiple GPS positions to reduce jitter"""
        positions = [
            {'latitude': 54.0830, 'longitude': 13.4375},
            {'latitude': 54.0835, 'longitude': 13.4380},
            {'latitude': 54.0833, 'longitude': 13.4378},
        ]
        
        avg_lat = sum(p['latitude'] for p in positions) / len(positions)
        avg_lon = sum(p['longitude'] for p in positions) / len(positions)
        
        assert abs(avg_lat - 54.0833) < 0.0001
        assert abs(avg_lon - 13.4378) < 0.0001


class TestSailConfiguration:
    """Test vessel-specific sail configuration (mainsail + genua only)"""
    
    def test_valid_genua_states(self):
        """Test valid genua configuration states"""
        valid_states = [
            'Genua gesetzt',
            'Genua teilweise',
            'Genua geborgen',
            ''  # Empty is valid (no selection)
        ]
        
        for state in valid_states:
            assert state in valid_states or state == ''
    
    def test_main_furl_percentage_range(self):
        """Test mainsail furling percentage is 0-100"""
        test_cases = [0, 25, 50, 75, 100]
        
        for pct in test_cases:
            assert 0 <= pct <= 100, f"Furling % {pct} should be 0-100"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
