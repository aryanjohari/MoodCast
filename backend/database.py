import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"

def init_db():
    """Initialize the database with required tables."""
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
                mood_score REAL
            )
        """)
        logger.info("Created/verified sensor_data table")

        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                completeness REAL,
                freshness REAL,
                missing_fields TEXT,
                error TEXT,
                timestamp TEXT
            )
        """)
        logger.info("Created/verified quality_metrics table")

        # IoT nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT UNIQUE,
                pi_id TEXT,
                sensor_id TEXT,
                last_seen TEXT,
                lat REAL,
                lon REAL
            )
        """)
        logger.info("Created/verified iot_nodes table")

        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                type TEXT,
                message TEXT,
                timestamp TEXT,
                severity TEXT
            )
        """)
        logger.info("Created/verified alerts table")

        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()