from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from weather_service import WeatherService
from services.currency import CurrencyService
from datetime import datetime
import os
from db import SessionLocal

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

@router.get("/health")
async def health_check():
    """Health check endpoint to monitor external service dependencies and configuration
    
    Returns status of:
    - Database connection
    - Open-Meteo Weather API
    - ECB Currency Exchange API
    - SESSION_SECRET configuration
    
    Useful for monitoring and alerting when services are down or tokens expire.
    """
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "healthy",
        "services": {}
    }
    
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["overall_status"] = "unhealthy"
    finally:
        db.close()
    
    test_lat, test_lon = 55.5536, 9.7306
    weather_data = WeatherService.fetch_weather_data(test_lat, test_lon)
    if weather_data and weather_data.get('temperature') is not None:
        health_status["services"]["open_meteo_api"] = {
            "status": "healthy",
            "message": "Weather API responding correctly",
            "last_fetch": weather_data.get('timestamp')
        }
    else:
        health_status["services"]["open_meteo_api"] = {
            "status": "unhealthy",
            "message": "Weather API not responding or returning invalid data"
        }
        health_status["overall_status"] = "unhealthy"
    
    try:
        rates = CurrencyService.get_rates()
        if rates and 'DKK' in rates and rates['DKK'] > 0:
            dkk_to_eur = 1.0 / rates['DKK']
            health_status["services"]["ecb_currency_api"] = {
                "status": "healthy",
                "message": "ECB currency API responding correctly",
                "sample_rate": f"1 DKK = {dkk_to_eur:.4f} EUR",
                "cache_age_hours": (datetime.utcnow() - CurrencyService._cache_timestamp).total_seconds() / 3600 if CurrencyService._cache_timestamp else None
            }
        else:
            health_status["services"]["ecb_currency_api"] = {
                "status": "degraded",
                "message": "ECB API using fallback rates (may be outdated)"
            }
    except Exception as e:
        health_status["services"]["ecb_currency_api"] = {
            "status": "unhealthy",
            "message": f"Currency API error: {str(e)}"
        }
        health_status["overall_status"] = "unhealthy"
    
    session_secret = os.getenv("SESSION_SECRET")
    if session_secret and len(session_secret) >= 32:
        health_status["services"]["session_secret"] = {
            "status": "healthy",
            "message": "SESSION_SECRET is configured and meets minimum length requirement"
        }
    elif session_secret:
        health_status["services"]["session_secret"] = {
            "status": "warning",
            "message": f"SESSION_SECRET is too short ({len(session_secret)} chars, recommended: 32+)"
        }
    else:
        health_status["services"]["session_secret"] = {
            "status": "unhealthy",
            "message": "SESSION_SECRET is not configured"
        }
        health_status["overall_status"] = "unhealthy"
    
    status_code = 200 if health_status["overall_status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)
