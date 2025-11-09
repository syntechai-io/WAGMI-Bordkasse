from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from weather_service import WeatherService

router = APIRouter()

@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    """Fetch weather data from Open-Meteo API for given coordinates
    
    This endpoint is publicly accessible (no authentication required) to support
    Quick Fill functionality in the logbook form.
    """
    weather_data = WeatherService.fetch_weather_data(lat, lon)
    
    if weather_data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")
    
    wind_direction_compass = weather_data.get('wind_direction_compass', '')
    wind_speed_kn = weather_data.get('wind_speed_kn')
    wind_strength_beaufort = WeatherService.wind_speed_to_beaufort(wind_speed_kn) if wind_speed_kn else ''
    
    return JSONResponse({
        'temperature': weather_data.get('temperature'),
        'wind_direction': wind_direction_compass,
        'wind_strength': wind_strength_beaufort,
        'pressure_hpa': weather_data.get('pressure_hpa'),
        'timestamp': weather_data.get('timestamp')
    })
