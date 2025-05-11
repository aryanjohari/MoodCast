import sqlite3
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"

def init_db():
    """Initialize database with new schema."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Sensor data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                temp REAL,
                humidity REAL,
                pressure REAL,
                wind_speed REAL,
                clouds REAL,
                rain REAL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                mood_score REAL
            )
        """)
        # Create index on lat, lon
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lat_lon ON sensor_data (lat, lon)
        """)
        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                completeness REAL,
                freshness INTEGER,
                error TEXT
            )
        """)
        # Mood predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mood_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                predicted_mood_score REAL,
                confidence REAL
            )
        """)
        conn.commit()
        logger.info("Database initialized")

def compute_mood_score(data):
    """Compute MoodSync score based on weather data."""
    try:
        score = 50  # Base score
        if data.get("pressure", 1013) < 1000:
            score -= 10
        if data.get("clouds", 0) > 50:
            score -= 5
        if data.get("rain", 0) > 0:
            score -= 10
        if data.get("wind_speed", 0) > 10:
            score -= 5
        hour = datetime.fromisoformat(data["timestamp"]).hour
        if 6 <= hour <= 18:
            score += 10  # Daytime bonus
        return max(0, min(100, score))
    except Exception as e:
        logger.error(f"Error computing mood score: {e}")
        return None

def store_sensor_data(data):
    """Store preprocessed sensor data and quality metrics."""
    city  = data["city"] if data["city"] else None
    lat = data["lat"] if data["lat"] else None
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Store sensor data
        cursor.execute("""
            INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city, lat, data["lon"], data["temp"], data["humidity"],
            data["pressure"], data["wind_speed"], data["clouds"], data["rain"],
            data["timestamp"], data["source"], data.get("mood_score")
        ))
        # Store quality metrics (simple for Phase 1)
        completeness = sum(1 for key in ["temp", "humidity", "pressure", "clouds", "rain"] if key in data and data[key] is not None) / 5 * 100
        freshness = (datetime.utcnow() - datetime.fromisoformat(data["timestamp"])).seconds
        cursor.execute("""
            INSERT INTO quality_metrics (city, timestamp, completeness, freshness, error)
            VALUES (?, ?, ?, ?, ?)
        """, (data["city"], datetime.utcnow().isoformat(), completeness, freshness, None))
        conn.commit()
        logger.info(f"Stored sensor data for {data['city']}")

def prune_old_data(days=7):
    """Remove data older than specified days."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor.execute("DELETE FROM sensor_data WHERE timestamp < ?", (cutoff,))
        cursor.execute("DELETE FROM quality_metrics WHERE timestamp < ?", (cutoff,))
        cursor.execute("DELETE FROM mood_predictions WHERE timestamp < ?", (cutoff,))
        conn.commit()
        logger.info(f"Pruned data older than {days} days")

if __name__ == "__main__":
    init_db()