MoodCast
MoodCast is a real-time weather application that delivers current weather, a 72-hour forecast, and mood-based suggestions via the MoodSync feature. Built with a modern web frontend, Python backend, and MQTT for communication, it’s designed for IoT deployment on a Raspberry Pi. The app features engaging animations, a temperature trend chart, and geolocation support, enhancing user experience with weather-driven mood insights.
Table of Contents

Features
Architecture
Setup
Prerequisites
Backend Setup
Frontend Setup
Mosquitto MQTT Broker


Running the Application
Testing
Development Steps Completed
Next Steps
Contributing
License

Features

Real-Time Weather: Displays current weather (temperature, humidity, pressure, clouds, rain, sunrise/sunset) for a selected city or geolocation.
72-Hour Forecast: Shows weather data for the next 72 hours, updated every 5 minutes via MQTT.
MoodSync: Calculates a mood score based on weather parameters (pressure, clouds, rain, wind, time of day) and suggests activities with badges (e.g., "Zen Master", "Sunshine Explorer").
Animations: Dynamic CSS animations (raindrops, drifting clouds, sunny glow) reflect weather conditions.
Temperature Trend Chart: Visualizes forecast temperatures using Chart.js.
Geolocation: Automatically detects the user’s city using browser geolocation and OpenWeatherMap’s reverse geocoding API.
City Selection: Curated list of global cities (e.g., Auckland, Tokyo, London) for manual selection.
MQTT Communication: Real-time updates via Mosquitto broker, with frontend publishing city changes and backend publishing weather/forecast data.
Error Handling: Displays loading states, errors (e.g., geolocation denied), and timeouts.
Vite Environment Variables: Securely manages API keys using .env.local.

Architecture

Frontend (frontend/):
Built with React, Vite, and MQTT.js.
Connects to Mosquitto via WebSocket (ws://localhost:8083).
Publishes city changes to moodcast/city.
Subscribes to moodcast/weather, moodcast/forecast, moodcast/alerts for updates.
Uses App.jsx for core logic, App.css for animations, and Chart.js for visualization.


Backend (backend/):
Python with Flask, Paho MQTT, and SQLite.
Subscribes to moodcast/city and publishes to moodcast/weather, moodcast/forecast, moodcast/alerts.
Fetches weather data from OpenWeatherMap API (fetch_weather.py).
Stores historical data in SQLite (database.py).
Publishes updates immediately on city change and every 5 minutes (main.py, mqtt_publisher.py).


MQTT Broker: Mosquitto on localhost:1883 (backend, TCP) and localhost:8083 (frontend, WebSocket).
Data Flow:
Frontend publishes { city: "Auckland" } to moodcast/city.
Backend receives city, fetches weather/forecast from OpenWeatherMap, and publishes to MQTT topics.
Frontend updates UI with received data, including MoodSync and chart.



Setup
Prerequisites

System: Linux/macOS/Windows (Raspberry Pi deployment pending).
Software:
Node.js 16+ (npm)
Python 3.8+
Mosquitto MQTT broker
Git


Accounts:
OpenWeatherMap API key (free tier, sign up).


Network:
Ports 1883 (MQTT TCP) and 8083 (MQTT WebSocket) open.
Stable internet for API calls.



Backend Setup

Clone Repository:git clone <your-repo> moodcast
cd moodcast/backend


Create Virtual Environment:python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:pip install -r requirements.txt


Includes paho-mqtt, requests, schedule, python-dotenv.


Configure Environment:
Create backend/.env:OPENWEATHERMAP_API_KEY=your_api_key_here


Replace your_api_key_here with your OpenWeatherMap API key.


Initialize Database:
Run database.py to create SQLite database (moodcast.db):python database.py





Frontend Setup

Navigate to Frontend:cd moodcast/frontend


Install Dependencies:npm install


Includes react, mqtt, axios, chart.js, react-icons.


Configure Environment:
Create frontend/.env.local:VITE_OPENWEATHERMAP_API_KEY=your_api_key_here


Replace your_api_key_here with your OpenWeatherMap API key.
Ensure .gitignore includes .env.local.


Verify Vite Config:
vite.config.js:export default {
  assetsInclude: ['**/*.crt'] // For TLS in production
};





Mosquitto MQTT Broker

Install Mosquitto:sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto


Configure Mosquitto:
Edit /etc/mosquitto/mosquitto.conf:listener 1883 0.0.0.0
listener 8083 0.0.0.0
protocol websockets
allow_anonymous true  # To be secured during Pi deployment




Verify Ports:netstat -tuln | grep -E '1883|8083'



Running the Application

Start Mosquitto:sudo systemctl start mosquitto


Run Backend:cd backend
source venv/bin/activate
python main.py


Logs: “Connected to MQTT broker”, “Received new city”, “Published weather”.


Run Frontend:cd frontend
npm run dev


Open http://localhost:5173.
Logs: “MQTT: Connected to broker”, “MQTT: Publishing initial city”, “MQTT: Received message on moodcast/weather”.


Interact:
Select a city (e.g., Tokyo) or use geolocation.
View weather, 72-hour forecast, MoodSync suggestions, and animations.
Verify periodic updates every 5 minutes.



Testing

Frontend:
Console logs (F12 → Console):
Single “MQTT: Connected to broker”.
Single “MQTT: Publishing initial city: { city: 'Auckland' }” on load.
“useEffect: selectedCity.name: ” once per city change.
“MQTT: Received message on moodcast/weather” on initial load and every 5 minutes.


UI: Weather data, 72-hour forecast (24 entries), MoodSync badges, animations (raindrops, clouds), chart.


Backend:
Logs: Single “Received new city” per city change, “Published weather” every 5 minutes.
Database: Verify entries in moodcast.db using sqlite3 moodcast.db "SELECT * FROM weather".


Mosquitto:
Logs: journalctl -u mosquitto -n 100.
Test publish: mosquitto_pub -h localhost -p 1883 -t "moodcast/city" -m '{"city":"Tokyo"}'.


Debug:
Check .env and .env.local for API keys.
Restart services if MQTT connections fail.
Verify no multiple MQTT connections or publishes.



Development Steps Completed

Step 1: Project Setup
Initialized Git repository, created frontend/ (React, Vite) and backend/ (Python).
Configured OpenWeatherMap API and .env files.


Step 2: Backend Development
Built main.py (MQTT client, periodic fetches), fetch_weather.py (API calls), mqtt_publisher.py (publishing), database.py (SQLite storage).
Implemented immediate and 5-minute weather updates.


Step 3: Frontend Development
Developed App.jsx with city selection, geolocation, weather display, and MoodSync.
Added App.css with animations (raindrops, drifting clouds, sunny glow).
Integrated Chart.js for temperature trend visualization.


Step 4: MQTT Integration
Configured Mosquitto for TCP (1883) and WebSocket (8083).
Connected frontend (ws://localhost:8083) and backend (localhost:1883) via MQTT.
Ensured real-time city-to-weather data flow.


Step 5: MoodSync and Enhancements
Implemented MoodSync scoring (pressure, clouds, rain, wind, time of day).
Added badges and suggestions (e.g., “Cozy Reader”, “Energy Star”).
Enhanced UI with error handling, loading states, and curated city list.


Step 6: Stabilization and Security Prep
Fixed useEffect issues in App.jsx for single MQTT connection and city publish.
Switched to import.meta.env for Vite environment variables.
Changed MQTT to ws://localhost:8083 (temporary, to be secured).
Prepared for secure MQTT (authentication, TLS, ACLs) in Pi deployment.



Next Steps

Step 7: Raspberry Pi Deployment
Deploy MoodCast on Raspberry Pi (e.g., Pi 4).
Install Mosquitto, Node.js, Python.
Secure MQTT with:
Username/password authentication (allow_anonymous false).
TLS/SSL for wss://<pi-ip>:8083 and 1883.
ACLs to restrict topic access.
Firewall (e.g., ufw) to limit ports.


Create systemd services for backend and Mosquitto.
Update App.jsx to use wss://<pi-ip>:8083.
Test deployment for single connections, periodic updates, and UI functionality.



Contributing

Fork the repository.
Create a feature branch: git checkout -b feature-name.
Commit changes: git commit -m "Add feature".
Push: git push origin feature-name.
Open a pull request.

License
MIT License. See LICENSE for details.
