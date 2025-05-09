import sqlite3
import json
from datetime import datetime

DATABASE = "weather_data.db"

def init_db():
    """Initialize the SQLite database and create tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Current weather table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            device_label TEXT NOT NULL,
            data JSON NOT NULL
        )
    """)
    # Forecast table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            device_label TEXT NOT NULL,
            forecast_time TEXT NOT NULL,
            data JSON NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def store_weather_data(weather_data, location="London", device_label="MoodCast"):
    """Store current weather data in the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    timestamp = datetime.utcfromtimestamp(weather_data["timestamp"]).isoformat()
    data_json = json.dumps(weather_data)
    cursor.execute(
        "INSERT INTO weather (timestamp, location, device_label, data) VALUES (?, ?, ?, ?)",
        (timestamp, location, device_label, data_json)
    )
    conn.commit()
    conn.close()

def store_forecast_data(forecast_data, location="London", device_label="MoodCast"):
    """Store forecast data in the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    for forecast in forecast_data:
        timestamp = datetime.utcnow().isoformat()  # Time of storage
        forecast_time = datetime.utcfromtimestamp(forecast["timestamp"]).isoformat()
        data_json = json.dumps(forecast)
        cursor.execute(
            "INSERT INTO forecast (timestamp, location, device_label, forecast_time, data) VALUES (?, ?, ?, ?, ?)",
            (timestamp, location, device_label, forecast_time, data_json)
        )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")