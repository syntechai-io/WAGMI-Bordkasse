"""
Comprehensive Regression Tests for Logbook Features
Tests dropdowns, weather API, GPS, motor hours, and PDF export
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base
import os

def test_dropdown_fields_exist_in_form():
    """Test that hybrid select/manual fields are present in logbook form"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    # Check for hybrid select dropdowns (default mode)
    assert 'id="wind_direction_select"' in form_html
    assert 'id="wind_strength_select"' in form_html
    assert 'id="visibility_select"' in form_html
    assert 'id="sail_plan_select"' in form_html
    
    # Check for manual entry inputs (hidden by default)
    assert 'id="wind_direction_manual"' in form_html
    assert 'id="wind_strength_manual"' in form_html
    assert 'id="visibility_manual"' in form_html
    assert 'id="sail_plan_manual"' in form_html
    
    # Check for toggle buttons
    assert 'hybrid-toggle' in form_html
    assert 'Eigenen Wert eingeben' in form_html
    
    # Check option values still exist
    assert 'option value="N"' in form_html
    assert 'option value="SW"' in form_html
    assert '4 Bft (11-16 kn) - Mäßige Brise' in form_html
    assert 'Sehr gut (>10 nm)' in form_html
    assert 'Großsegel + Genua' in form_html
    
    # Check for hybrid field JavaScript logic
    assert 'getHybridFieldControl' in form_html
    assert 'enableManualMode' in form_html

def test_weather_button_exists():
    """Test that weather fetch button is present"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'id="weather-button"' in form_html
    assert '🌤️ Wetterdaten automatisch abrufen' in form_html

def test_weather_endpoint_exists():
    """Test that weather API endpoint is defined"""
    from pathlib import Path
    router_code = Path('routers/logbook.py').read_text()
    
    assert '@router.get("/weather")' in router_code
    assert 'WeatherService.fetch_weather_data' in router_code

def test_weather_service_import():
    """Test that weather service can be imported"""
    from weather_service import WeatherService
    
    assert hasattr(WeatherService, 'fetch_weather_data')
    assert hasattr(WeatherService, 'wind_speed_to_beaufort')
    assert hasattr(WeatherService, '_degrees_to_compass')

def test_existing_logbook_functionality():
    """Test that existing logbook fields still work"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'name="latitude"' in form_html
    assert 'name="longitude"' in form_html
    assert 'name="temperature"' in form_html
    assert 'name="pressure_hpa"' in form_html
    assert 'name="cog_deg"' in form_html
    assert 'name="sog_kn"' in form_html
    assert 'name="engine_on_time"' in form_html
    assert 'name="engine_off_time"' in form_html
    assert 'name="main_furl_pct"' in form_html
    assert 'name="headsail"' in form_html

def test_gps_button_still_exists():
    """Test that GPS button functionality is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'id="gps-button"' in form_html
    assert '📍 GPS-Position abrufen' in form_html
    assert 'id="gps-tracking-toggle"' in form_html

def test_motor_hours_calculation_preserved():
    """Test that motor hours calculation JavaScript is still present"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'function calculateMotorHours()' in form_html
    assert 'id="motor-on-btn"' in form_html
    assert 'id="motor-off-btn"' in form_html

def test_pdf_export_endpoints_preserved():
    """Test that PDF export endpoints are still defined"""
    from pathlib import Path
    router_code = Path('routers/logbook.py').read_text()
    
    assert '@router.get("/export/pdf/entry/{entry_id}")' in router_code
    assert '@router.get("/export/pdf/daily")' in router_code
    assert 'render_logbook_pdf' in router_code

def test_in_mast_furling_preserved():
    """Test that in-mast furling slider is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'id="main_furl_slider"' in form_html
    assert 'id="main-furl-display"' in form_html
    assert 'id="furl-in-btn"' in form_html
    assert 'id="furl-out-btn"' in form_html

def test_watch_leader_preserved():
    """Test that watch leader field is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'name="watch_leader_id"' in form_html

def test_default_departure_port():
    """Test that default departure port is set"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'Fredericia DK' in form_html

def test_sea_state_enum_dropdown():
    """Test that sea state dropdown is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'select name="sea_state"' in form_html
    assert 'for state in sea_states' in form_html

def test_event_category_dropdown():
    """Test that event category dropdown is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'select name="event_category"' in form_html
    assert 'Manöver' in form_html
    assert 'Wetterwechsel' in form_html
    assert 'Notfall' in form_html

def test_csrf_protection_preserved():
    """Test that CSRF protection is still in place"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert '{{ csrf_input | safe }}' in form_html

def test_offline_storage_preserved():
    """Test that offline storage functionality is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'createOfflineEntry' in form_html
    assert 'logbookEntries' in form_html

def test_gps_tracking_module_preserved():
    """Test that GPS tracking module is still present"""
    from pathlib import Path
    gps_js = Path('static/js/logbook-gps.js').read_text()
    
    assert 'class LogbookGPSTracker' in gps_js
    assert 'start()' in gps_js
    assert 'stop()' in gps_js

def test_all_phase_a_fields_preserved():
    """Test that all Phase A fields are preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    phase_a_fields = [
        'cog_deg', 'sog_kn', 'log_kn', 'dist_day_nm',
        'pressure_hpa', 'pressure_trend', 'weather_source',
        'engine_on', 'engine_on_time', 'engine_off_time', 
        'eng_hours_total', 'fuel_level_l',
        'main_furl_pct', 'headsail', 'sail_action',
        'event_category', 'event_details'
    ]
    
    for field in phase_a_fields:
        assert f'name="{field}"' in form_html, f"Field {field} is missing!"

if __name__ == '__main__':
    print("Running Logbook Regression Tests...")
    print("=" * 60)
    pytest.main([__file__, '-v', '--tb=short'])
