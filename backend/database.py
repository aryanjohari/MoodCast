import sqlite3
from datetime import datetime, timedelta
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"
QUALITY_THRESHOLD_COMPLETENESS = 80.0
QUALITY_THRESHOLD_FRESHNESS = 300

def init_db():
    """Initialize database with schema and handle migrations."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("SELECT MAX(version) FROM schema_version")
        current_version = cursor.fetchone()[0] or 0
        logger.debug(f"Current schema version: {current_version}")

        if current_version < 1:
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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lat_lon ON sensor_data (lat, lon)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    completeness REAL,
                    freshness INTEGER,
                    error TEXT,
                    missing_fields TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mood_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    predicted_mood_score REAL,
                    confidence REAL
                )
            """)
            cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                         (1, datetime.utcnow().isoformat()))
            logger.info("Applied schema version 1")

        if current_version < 2:
            cursor.execute("PRAGMA table_info(quality_metrics)")
            columns = [col[1] for col in cursor.fetchall()]
            if "missing_fields" not in columns:
                cursor.execute("ALTER TABLE quality_metrics ADD COLUMN missing_fields TEXT")
                logger.info("Added missing_fields column to quality_metrics")
            cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                         (2, datetime.utcnow().isoformat()))
            logger.info("Applied schema version 2")

        if current_version < 3:
            cursor.execute("PRAGMA table_info(quality_metrics)")
            columns = [col[1] for col in cursor.fetchall()]
            if "source" not in columns:
                cursor.execute("ALTER TABLE quality_metrics ADD COLUMN source TEXT")
                logger.info("Added source column to quality_metrics")
            cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                         (3, datetime.utcnow().isoformat()))
            logger.info("Applied schema version 3")

        conn.commit()
        logger.info("Database initialized")

def compute_mood_score(data):
    """Compute MoodSync score based on weather data."""
    try:
        score = 50
        if data.get("pressure") and data["pressure"] < 1000:
            score -= 10
        if data.get("clouds") and data["clouds"] > 50:
            score -= 5
        if data.get("rain") and data["rain"] > 0:
            score -= 10
        if data.get("wind_speed") and data["wind_speed"] > 10:
            score -= 5
        hour = datetime.fromisoformat(data["timestamp"]).hour
        if 6 <= hour <= 18:
            score += 10
        return max(0, min(100, score))
    except Exception as e:
        logger.error(f"Error computing mood score: {e}")
        return None

def store_sensor_data(data):
    """Store preprocessed sensor data and quality metrics."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["city"], data["lat"], data["lon"], data["temp"], data.get("humidity"),
                data.get("pressure"), data.get("wind_speed"), data.get("clouds"), data.get("rain"),
                data["timestamp"], data["source"], data.get("mood_score")
            ))
        except sqlite3.Error as e:
            logger.error(f"Database error storing sensor data for {data['city']}: {e}")
            raise

        optional_fields = ["temp", "humidity", "pressure", "wind_speed", "clouds", "rain"]
        present_fields = [key for key in optional_fields if key in data and data[key] is not None]
        completeness = len(present_fields) / len(optional_fields) * 100
        missing_fields = [key for key in optional_fields if key not in data or data[key] is None]
        freshness = (datetime.utcnow() - datetime.fromisoformat(data["timestamp"])).seconds

        error = None
        if completeness < QUALITY_THRESHOLD_COMPLETENESS:
            error = f"Low completeness: {completeness}%"
        if freshness > QUALITY_THRESHOLD_FRESHNESS:
            error = error + f"; Stale data: {freshness}s" if error else f"Stale data: {freshness}s"

        try:
            cursor.execute("""
                INSERT INTO quality_metrics (city, timestamp, completeness, freshness, missing_fields, error, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data["city"], datetime.utcnow().isoformat(), completeness, freshness,
                json.dumps(missing_fields), error, data["source"]
            ))
        except sqlite3.Error as e:
            logger.error(f"Database error storing quality metrics for {data['city']}: {e}")
            raise

        conn.commit()
        logger.info(f"Stored sensor data for {data['city']} with completeness {completeness}%")

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