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
    """Test that hybrid select/manual fields are present in logbook form.

    German labels were migrated to i18n keys (`{{ t('logbook.bft4') }}` etc.)
    so we assert both the i18n reference in the template AND the German
    string in the locale file.
    """
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    de = Path('locales/de.json').read_text()

    # Hybrid select dropdowns (default mode)
    assert 'id="wind_direction_select"' in form_html
    assert 'id="wind_strength_select"' in form_html
    assert 'id="visibility_select"' in form_html
    assert 'id="sail_plan_select"' in form_html

    # Manual entry inputs (hidden by default)
    assert 'id="wind_direction_manual"' in form_html
    assert 'id="wind_strength_manual"' in form_html
    assert 'id="visibility_manual"' in form_html
    assert 'id="sail_plan_manual"' in form_html

    # Toggle buttons + label (now via i18n key common.manual_input)
    assert 'hybrid-toggle' in form_html
    assert "t('common.manual_input')" in form_html
    assert 'Eigenen Wert eingeben' in de

    # Option values still exist
    assert 'option value="N"' in form_html
    assert 'option value="SW"' in form_html

    # Beaufort, visibility, sail plan: i18n key in template + German in locale
    assert "t('logbook.bft4')" in form_html
    assert '4 Bft (11-16 kn) - Mäßige Brise' in de
    assert "t('logbook.visibility_very_good')" in form_html
    assert 'Sehr gut (>10 nm)' in de
    assert "t('logbook.sail_main_genoa')" in form_html
    assert 'Großsegel + Genua' in de

    # Hybrid field JavaScript logic preserved
    assert 'getHybridFieldControl' in form_html
    assert 'enableManualMode' in form_html

def test_weather_button_exists():
    """Test that weather fetch button is present (label via i18n key)."""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    de = Path('locales/de.json').read_text()

    assert 'id="weather-button"' in form_html
    assert "t('logbook.weather_auto_fetch')" in form_html
    assert 'Wetterdaten automatisch abrufen' in de

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
    assert "t('logbook.gps_get_position')" in form_html
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
    """Test that the departure port input + i18n placeholder is wired up.

    The hardcoded "Fredericia DK" default value was removed when the form was
    internationalized. We now verify the input field exists and uses the
    `logbook.departure_placeholder` i18n key, with the German placeholder
    text living in the locale file.
    """
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    de = Path('locales/de.json').read_text()

    assert 'name="departure"' in form_html
    assert "t('logbook.placeholder_departure')" in form_html
    assert '"logbook.placeholder_departure"' in de

def test_sea_state_enum_dropdown():
    """Test that sea state dropdown is preserved"""
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    
    assert 'select name="sea_state"' in form_html
    assert 'for state in sea_states' in form_html

def test_event_category_dropdown():
    """Test that event category dropdown is preserved.

    Option labels were migrated to i18n keys (`{{ t('logbook.event_maneuver') }}`
    etc.). We assert the i18n key references in the template AND the German
    strings in the locale file.
    """
    from pathlib import Path
    form_html = Path('templates/logbook_form.html').read_text()
    de = Path('locales/de.json').read_text()

    assert 'select name="event_category"' in form_html
    assert "t('logbook.event_maneuver')" in form_html
    assert "t('logbook.event_weather_change')" in form_html
    assert "t('logbook.event_emergency')" in form_html

    assert '"Manöver"' in de
    assert '"Wetterwechsel"' in de
    assert '"Notfall"' in de

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

def test_night_mode_critical_css_present_in_layout():
    from pathlib import Path
    layout = Path('templates/layout.html').read_text()
    night_critical = Path('templates/_night_critical.html').read_text()
    # CSS link tags must carry the dynamic content-hash cache-buster — not
    # a hand-edited number — so a stylesheet deploy invalidates browsers
    # automatically. See asset_version.py.
    assert '?v={{ asset_version }}' in layout
    # The critical inline block was extracted into _night_critical.html
    # (single source of truth, included by both layout.html and login.html)
    # — assert the include is wired up and the partial still carries the
    # rules, rather than looking for them inline here.
    assert '_night_critical.html' in layout
    assert 'html[data-theme="night"]' in night_critical
    for primitive in ['.cl-card', '.cl-btn', '.cl-input', '.cl-tabbar', 'accent-color']:
        assert primitive in night_critical, f"_night_critical.html missing {primitive}"


def test_night_mode_critical_css_present_in_login():
    from pathlib import Path
    login = Path('templates/login.html').read_text()
    night_critical = Path('templates/_night_critical.html').read_text()
    assert '?v={{ asset_version }}' in login
    assert '_night_critical.html' in login
    assert 'html[data-theme="night"]' in night_critical
    assert 'Critical first-paint Night Mode' in night_critical


def test_night_mode_svg_rule_no_longer_overreaches():
    from pathlib import Path
    import re
    night_css = Path('static/ui_night_mode.css').read_text()
    blocks = re.findall(r'html\[data-theme="night"\]\s+svg\s*\{[^}]*\}', night_css)
    for block in blocks:
        assert 'color' not in block.split(';')[0] or '!important' not in block, block
        assert 'currentColor' in block


def test_night_mode_blue_overrides_stripped_from_ios_prime():
    from pathlib import Path
    import re
    ios = Path('static/ui_ios_prime.css').read_text()
    blocks = re.findall(r'html\[data-theme="night"\][^{]*\{[^}]*\}', ios)
    for block in blocks:
        for hex_val in ('#1a2f4a', '#0d3b5e', '#0a3a5e'):
            assert hex_val.lower() not in block.lower(), block[:200]


def test_service_worker_cache_name_derived_from_asset_version():
    """sw.js holds a placeholder; the /sw.js route binds CACHE_NAME to the
    same content hash that drives the templates' ?v= cache-buster."""
    from pathlib import Path
    from asset_version import CACHE_NAME_PLACEHOLDER, cache_name

    sw = Path('static/sw.js').read_text()
    # Raw file uses the placeholder, never a hand-rolled crewlog-vNN string.
    assert CACHE_NAME_PLACEHOLDER in sw
    assert "crewlog-v28" not in sw and "crewlog-v29" not in sw
    assert any(s in sw for s in ("networkFirstStatic", "network-first", "networkFirst"))
    assert "caches.keys" in sw and "delete" in sw

    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        pytest.skip(f"app not importable: {e}")

    client = TestClient(app)
    r = client.get("/sw.js")
    assert r.status_code == 200
    body = r.text
    expected = cache_name()
    assert expected in body, f"served sw.js missing {expected}"
    assert CACHE_NAME_PLACEHOLDER not in body, "placeholder was not substituted"


def test_diagnostics_theme_route_renders_night_with_correct_palette():
    from pathlib import Path
    tpl = Path('templates/theme_diagnostics.html').read_text()
    # The <html> tag must always stamp an explicit data-theme (night or day)
    # rather than leaving it unstamped for non-night requests — an
    # unstamped root falls through to cl_design.css's dark-default tokens
    # regardless of the requested theme. See test_night_mode_e2e.py's
    # test_day_mode_remains_unchanged_no_regression for the live-render
    # check of this.
    assert 'data-theme=' in tpl
    assert "'night'" in tpl and "'day'" in tpl
    assert 'ui_night_mode.css?v={{ asset_version }}' in tpl
    for primitive in [
        'cl-btn--primary', 'cl-btn--accent', 'cl-btn--success', 'cl-btn--warn',
        'cl-input', 'cl-check-row', 'cl-tabbar', 'cl-tabbar__item--active',
        'cl-pill', 'cl-alert', 'cl-card',
    ]:
        assert primitive in tpl, f"theme_diagnostics.html missing {primitive}"

    main_py = Path('main.py').read_text()
    assert '@app.get("/diagnostics/theme")' in main_py
    assert 'no-store' in main_py and 'no-cache' in main_py

    auth_mw = Path('middleware/auth.py').read_text()
    assert '/diagnostics/theme' in auth_mw


def test_night_mode_diagnostics_page_live_response():
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        pytest.skip(f"app not importable: {e}")
    from asset_version import asset_version

    client = TestClient(app)
    r = client.get("/diagnostics/theme", params={"theme": "night"})
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "").lower()
    assert "no-store" in cc and "no-cache" in cc

    body = r.text
    assert 'data-theme="night"' in body
    assert f'ui_night_mode.css?v={asset_version()}' in body
    assert 'cl-tabbar__item--active' in body
    assert body.count('cl-tabbar__item') >= 2

    r2 = client.get("/diagnostics/theme", params={"theme": "light"})
    assert r2.status_code == 200
    assert 'data-theme="night"' not in r2.text


if __name__ == '__main__':
    print("Running Logbook Regression Tests...")
    print("=" * 60)
    pytest.main([__file__, '-v', '--tb=short'])
