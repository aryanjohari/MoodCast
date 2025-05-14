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
                city TEXT NOT NULL,
                lat REAL,
                lon REAL,
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
        logger.info("Created/verified sensor_data table")
        
        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                completeness REAL,
                freshness REAL,
                missing_fields TEXT,
                error TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        logger.info("Created/verified quality_metrics table")
        
        # IoT nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL UNIQUE,
                pi_id TEXT,
                sensor_id TEXT,
                last_seen TEXT,
                lat REAL,
                lon REAL
            )
        """)
        logger.info("Created/verified iot_nodes table")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

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

def update_iot_node(city, pi_id, sensor_id, lat, lon):
    """Update or insert IoT node metadata."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO iot_nodes (city, pi_id, sensor_id, last_seen, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (city, pi_id, sensor_id, datetime.utcnow().isoformat(), lat, lon))
        conn.commit()
        conn.close()
        logger.info(f"Updated IoT node for {city}")
    except sqlite3.Error as e:
        logger.error(f"Error updating IoT node: {e}")


if __name__ == "__main__":
    init_db()