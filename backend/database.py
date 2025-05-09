from datetime import datetime
import sqlite3
import logging

logger = logging.getLogger(__name__)

def store_weather_data(weather_data, location, device_label):
    try:
        conn = sqlite3.connect('moodcast.db')
        cursor = conn.cursor()
        timestamp = datetime.utcfromtimestamp(weather_data["timestamp"]).isoformat()
        cursor.execute('''
            INSERT INTO weather (
                timestamp, location, device_label, temperature, feels_like, pressure,
                humidity, clouds, rain_1h, wind_speed, description, icon, sunrise, sunset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, location, device_label, weather_data["temperature"],
            weather_data["feels_like"], weather_data["pressure"], weather_data["humidity"],
            weather_data["clouds"], weather_data["rain_1h"], weather_data["wind_speed"],
            weather_data["description"], weather_data["icon"], weather_data["sunrise"],
            weather_data["sunset"]
        ))
        conn.commit()
        logger.info(f"Stored weather data for {location}")
    except Exception as e:
        logger.error(f"Error storing weather data: {e}")
    finally:
        conn.close()

def store_forecast_data(forecast_data, location, device_label):
    try:
        conn = sqlite3.connect('moodcast.db')
        cursor = conn.cursor()
        for item in forecast_data:
            timestamp = datetime.utcfromtimestamp(item["timestamp"]).isoformat()
            cursor.execute('''
                INSERT INTO forecast (
                    timestamp, location, device_label, temperature, pressure, clouds, icon
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, location, device_label, item["temperature"],
                item["pressure"], item["clouds"], item["icon"]
            ))
        conn.commit()
        logger.info(f"Stored forecast data for {location}")
    except Exception as e:
        logger.error(f"Error storing forecast data: {e}")
    finally:
        conn.close()