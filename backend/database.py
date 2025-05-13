import sqlite3
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"

def init_db():
    """Initialize SQLite database with required tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sensor data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                lat REAL,
                lon REAL,
                temp REAL,
                humidity REAL,
                pressure REAL,
                wind_speed REAL,
                clouds REAL,
                rain REAL,
                timestamp TEXT,
                source TEXT,
                mood_score INTEGER
            )
        """)
        logger.info("Created/verified sensor_data table")
        
        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                completeness REAL,
                freshness INTEGER,
                missing_fields TEXT,
                error TEXT,
                timestamp TEXT
            )
        """)
        logger.info("Created/verified quality_metrics table")
        
        # IoT nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_nodes (
                city TEXT PRIMARY KEY,
                pi_id TEXT,
                sensor_id TEXT,
                last_seen TEXT
            )
        """)
        logger.info("Created/verified iot_nodes table")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def compute_mood_score(data):
    """Compute mood score based on weather data (0-100)."""
    try:
        temp = data.get("temp", 20)  # Default 20°C if missing
        rain = data.get("rain", 0)   # Default 0mm if missing
        clouds = data.get("clouds", 0)  # Default 0% if missing
        
        # Simple heuristic: higher temp, lower rain, and fewer clouds improve mood
        temp_score = min(max((temp + 50) * 1.5, 0), 100)  # Normalize -50°C to 50°C
        rain_penalty = min(rain * 5, 50)  # Heavy rain reduces score
        cloud_penalty = clouds * 0.3  # Cloudiness slightly reduces score
        
        mood_score = int(temp_score - rain_penalty - cloud_penalty)
        mood_score = max(0, min(mood_score, 100))  # Clamp to 0-100
        
        return mood_score
    except Exception as e:
        logger.error(f"Error computing mood score: {e}")
        return 50  # Default score on error

def insert_sensor_data(data):
    """Insert sensor data into database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["city"], data["lat"], data["lon"], data["temp"], data["humidity"],
            data["pressure"], data["wind_speed"], data["clouds"], data["rain"],
            data["timestamp"], data["source"], data["mood_score"]
        ))
        conn.commit()
        conn.close()
        logger.info(f"Inserted sensor data for {data['city']}")
    except sqlite3.Error as e:
        logger.error(f"Error inserting sensor data: {e}")

def insert_quality_metrics(city, completeness, freshness, missing_fields, error):
    """Insert quality metrics into database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quality_metrics (city, completeness, freshness, missing_fields, error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (city, completeness, freshness, missing_fields, error, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        logger.info(f"Inserted quality metrics for {city}")
    except sqlite3.Error as e:
        logger.error(f"Error inserting quality metrics: {e}")

def update_iot_node(city, pi_id, sensor_id):
    """Update or insert IoT node metadata."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO iot_nodes (city, pi_id, sensor_id, last_seen)
            VALUES (?, ?, ?, ?)
        """, (city, pi_id, sensor_id, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        logger.info(f"Updated IoT node for {city}")
    except sqlite3.Error as e:
        logger.error(f"Error updating IoT node: {e}")