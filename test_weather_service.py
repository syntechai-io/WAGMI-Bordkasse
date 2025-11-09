import pytest
from weather_service import WeatherService
from unittest.mock import Mock, patch

def test_degrees_to_compass_conversion():
    """Test compass direction conversion from degrees"""
    assert WeatherService._degrees_to_compass(0) == 'N'
    assert WeatherService._degrees_to_compass(22.5) == 'NNE'
    assert WeatherService._degrees_to_compass(45) == 'NE'
    assert WeatherService._degrees_to_compass(90) == 'E'
    assert WeatherService._degrees_to_compass(135) == 'SE'
    assert WeatherService._degrees_to_compass(180) == 'S'
    assert WeatherService._degrees_to_compass(225) == 'SW'
    assert WeatherService._degrees_to_compass(270) == 'W'
    assert WeatherService._degrees_to_compass(315) == 'NW'
    assert WeatherService._degrees_to_compass(359) == 'N'
    assert WeatherService._degrees_to_compass(360) == 'N'

def test_degrees_to_compass_edge_cases():
    """Test edge cases for compass conversion"""
    assert WeatherService._degrees_to_compass(None) == ''
    assert WeatherService._degrees_to_compass(11) == 'N'
    assert WeatherService._degrees_to_compass(12) == 'NNE'
    assert WeatherService._degrees_to_compass(370) == 'N'  # Wrap around

def test_wind_speed_to_beaufort():
    """Test Beaufort scale conversion"""
    assert WeatherService.wind_speed_to_beaufort(0) == "0 Bft (0 kn) - Windstille"
    assert WeatherService.wind_speed_to_beaufort(1) == "1 Bft (1-3 kn) - Leiser Zug"
    assert WeatherService.wind_speed_to_beaufort(5) == "2 Bft (4-6 kn) - Leichte Brise"
    assert WeatherService.wind_speed_to_beaufort(8) == "3 Bft (7-10 kn) - Schwache Brise"
    assert WeatherService.wind_speed_to_beaufort(12) == "4 Bft (11-16 kn) - Mäßige Brise"
    assert WeatherService.wind_speed_to_beaufort(18) == "5 Bft (17-21 kn) - Frische Brise"
    assert WeatherService.wind_speed_to_beaufort(25) == "6 Bft (22-27 kn) - Starker Wind"
    assert WeatherService.wind_speed_to_beaufort(30) == "7 Bft (28-33 kn) - Steifer Wind"
    assert WeatherService.wind_speed_to_beaufort(37) == "8 Bft (34-40 kn) - Stürmischer Wind"
    assert WeatherService.wind_speed_to_beaufort(45) == "9 Bft (41-47 kn) - Sturm"
    assert WeatherService.wind_speed_to_beaufort(52) == "10 Bft (48-55 kn) - Schwerer Sturm"
    assert WeatherService.wind_speed_to_beaufort(60) == "11 Bft (56-63 kn) - Orkanartiger Sturm"
    assert WeatherService.wind_speed_to_beaufort(70) == "12 Bft (64+ kn) - Orkan"

def test_wind_speed_to_beaufort_edge_cases():
    """Test Beaufort conversion edge cases"""
    assert WeatherService.wind_speed_to_beaufort(None) == ''
    assert WeatherService.wind_speed_to_beaufort(0.5) == "0 Bft (0 kn) - Windstille"
    assert WeatherService.wind_speed_to_beaufort(3.9) == "1 Bft (1-3 kn) - Leiser Zug"
    assert WeatherService.wind_speed_to_beaufort(4.0) == "2 Bft (4-6 kn) - Leichte Brise"

@patch('weather_service.requests.get')
def test_fetch_weather_data_success(mock_get):
    """Test successful weather data fetch"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'current': {
            'time': '2025-11-08T21:00',
            'temperature_2m': 18.5,
            'wind_speed_10m': 12.3,
            'wind_direction_10m': 225.0,
            'surface_pressure': 1013.2
        }
    }
    mock_get.return_value = mock_response
    
    result = WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    assert result is not None
    assert result['temperature'] == 18.5
    assert result['wind_speed_kn'] == 12.3
    assert result['wind_direction_deg'] == 225.0
    assert result['wind_direction_compass'] == 'SW'
    assert result['pressure_hpa'] == 1013.2
    assert result['timestamp'] == '2025-11-08T21:00'

@patch('weather_service.requests.get')
def test_fetch_weather_data_api_error(mock_get):
    """Test weather API error handling"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response
    
    result = WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    assert result is None

@patch('weather_service.requests.get')
def test_fetch_weather_data_network_error(mock_get):
    """Test network error handling"""
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    
    result = WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    assert result is None

@patch('weather_service.requests.get')
def test_fetch_weather_data_invalid_response(mock_get):
    """Test invalid API response handling"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'error': 'Invalid request'}
    mock_get.return_value = mock_response
    
    result = WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    assert result is None

@patch('weather_service.requests.get')
def test_fetch_weather_data_partial_data(mock_get):
    """Test handling of partial/missing data fields"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'current': {
            'time': '2025-11-08T21:00',
            'temperature_2m': 18.5,
            'wind_direction_10m': None,
            'surface_pressure': 1013.2
        }
    }
    mock_get.return_value = mock_response
    
    result = WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    assert result is not None
    assert result['temperature'] == 18.5
    assert result['wind_direction_compass'] is None
    assert result['pressure_hpa'] == 1013.2

@patch('weather_service.requests.get')
def test_fetch_weather_data_coordinates_validation(mock_get):
    """Test that correct coordinates are passed to API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'current': {
            'time': '2025-11-08T21:00',
            'temperature_2m': 18.5
        }
    }
    mock_get.return_value = mock_response
    
    WeatherService.fetch_weather_data(55.5647, 9.7529)
    
    call_args = mock_get.call_args
    params = call_args[1]['params']
    
    assert params['latitude'] == 55.5647
    assert params['longitude'] == 9.7529
    assert params['current'] == 'temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure'
    assert params['wind_speed_unit'] == 'kn'
    assert params['timezone'] == 'auto'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
