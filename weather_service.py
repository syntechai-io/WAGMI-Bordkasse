import requests
from typing import Optional, Dict, Any
from datetime import datetime

class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    @staticmethod
    def fetch_weather_data(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure',
                'wind_speed_unit': 'kn',
                'timezone': 'auto'
            }
            
            response = requests.get(
                WeatherService.BASE_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if 'current' not in data:
                return None
            
            current = data['current']
            
            wind_dir_deg = current.get('wind_direction_10m')
            wind_dir_compass = WeatherService._degrees_to_compass(wind_dir_deg) if wind_dir_deg is not None else None
            
            return {
                'temperature': current.get('temperature_2m'),
                'wind_speed_kn': current.get('wind_speed_10m'),
                'wind_direction_deg': wind_dir_deg,
                'wind_direction_compass': wind_dir_compass,
                'pressure_hpa': current.get('surface_pressure'),
                'timestamp': current.get('time')
            }
            
        except requests.exceptions.RequestException:
            return None
        except (KeyError, ValueError):
            return None
    
    @staticmethod
    def _degrees_to_compass(degrees: float) -> str:
        if degrees is None:
            return ''
        
        degrees = degrees % 360
        
        compass_points = [
            (0, 'N'), (11.25, 'N'), 
            (11.25, 'NNE'), (33.75, 'NNE'),
            (33.75, 'NE'), (56.25, 'NE'),
            (56.25, 'ENE'), (78.75, 'ENE'),
            (78.75, 'E'), (101.25, 'E'),
            (101.25, 'ESE'), (123.75, 'ESE'),
            (123.75, 'SE'), (146.25, 'SE'),
            (146.25, 'SSE'), (168.75, 'SSE'),
            (168.75, 'S'), (191.25, 'S'),
            (191.25, 'SSW'), (213.75, 'SSW'),
            (213.75, 'SW'), (236.25, 'SW'),
            (236.25, 'WSW'), (258.75, 'WSW'),
            (258.75, 'W'), (281.25, 'W'),
            (281.25, 'WNW'), (303.75, 'WNW'),
            (303.75, 'NW'), (326.25, 'NW'),
            (326.25, 'NNW'), (348.75, 'NNW'),
            (348.75, 'N'), (360, 'N')
        ]
        
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                     'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    @staticmethod
    def wind_speed_to_beaufort(wind_speed_kn: float) -> str:
        if wind_speed_kn is None:
            return ''
        
        beaufort_scale = [
            (1, "0 Bft (0 kn) - Windstille"),
            (4, "1 Bft (1-3 kn) - Leiser Zug"),
            (7, "2 Bft (4-6 kn) - Leichte Brise"),
            (11, "3 Bft (7-10 kn) - Schwache Brise"),
            (17, "4 Bft (11-16 kn) - Mäßige Brise"),
            (22, "5 Bft (17-21 kn) - Frische Brise"),
            (28, "6 Bft (22-27 kn) - Starker Wind"),
            (34, "7 Bft (28-33 kn) - Steifer Wind"),
            (41, "8 Bft (34-40 kn) - Stürmischer Wind"),
            (48, "9 Bft (41-47 kn) - Sturm"),
            (56, "10 Bft (48-55 kn) - Schwerer Sturm"),
            (64, "11 Bft (56-63 kn) - Orkanartiger Sturm"),
            (float('inf'), "12 Bft (64+ kn) - Orkan")
        ]
        
        for max_speed, description in beaufort_scale:
            if wind_speed_kn < max_speed:
                return description
        
        return beaufort_scale[-1][1]
