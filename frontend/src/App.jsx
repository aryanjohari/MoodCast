import { useState, useEffect } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { MapContainer, TileLayer, Circle, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Line } from "react-chartjs-2";
import { Chart, registerables } from "chart.js";
import "./App.css";

// Register Chart.js components
Chart.register(...registerables);

// Fix Leaflet marker icon issue (for popups)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const cities = [
  { name: "Auckland", lat: -36.8485, lon: 174.7633 },
  { name: "Tokyo", lat: 35.6762, lon: 139.6503 },
  { name: "London", lat: 51.5074, lon: -0.1278 },
  { name: "New York", lat: 40.7128, lon: -74.006 },
  { name: "Sydney", lat: -33.8688, lon: 151.2093 },
  { name: "Paris", lat: 48.8566, lon: 2.3522 },
  { name: "Singapore", lat: 1.3521, lon: 103.8198 },
  { name: "Dubai", lat: 25.2048, lon: 55.2708 },
  { name: "Mumbai", lat: 19.076, lon: 72.8777 },
  { name: "Cape Town", lat: -33.9249, lon: 18.4241 },
];

// Simulated logs for IoT nodes
const nodeLogs = cities.reduce((acc, city) => {
  acc[city.name] = [
    `${new Date().toISOString()} - ${city.name} sensor started`,
    `${new Date().toISOString()} - Connected to MQTT broker`,
    `${new Date().toISOString()} - Published weather data`,
  ];
  return acc;
}, {});

// Component to recenter map
function MapRecenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// Weather animation component
function WeatherAnimation({ condition }) {
  const baseStyle = { marginRight: "8px", display: "inline-block" };
  if (condition === "sunny") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "28px" }}
        animate={{ rotate: [0, 360], scale: [1, 1.2, 1], opacity: [1, 0.8, 1] }}
        transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
      >
        ☀️
      </motion.span>
    );
  } else if (condition === "cloudy") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "28px" }}
        animate={{
          x: [-10, 10, -10],
          opacity: [0.7, 1, 0.7],
          scale: [1, 1.1, 1],
        }}
        transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
      >
        ☁️
      </motion.span>
    );
  } else if (condition === "rainy") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "28px" }}
        animate={{ y: [0, 10, 0], opacity: [1, 0.6, 1] }}
        transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
      >
        🌧️
      </motion.span>
    );
  }
  return null;
}

function App() {
  const [selectedCity, setSelectedCity] = useState(cities[0]);
  const [weatherData, setWeatherData] = useState(null);
  const [forecastData, setForecastData] = useState([]);
  const [statusData, setStatusData] = useState(null);
  const [networkData, setNetworkData] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("weather");
  const [showWeatherDetails, setShowWeatherDetails] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setError(null);
      try {
        // Fetch current weather
        const weatherResponse = await axios.get(
          `http://localhost:5000/weather?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("Weather API Response:", weatherResponse.data);
        if (weatherResponse.data && weatherResponse.data.city) {
          setWeatherData(weatherResponse.data);
        } else {
          setError("No valid weather data returned");
        }

        // Fetch 72-hour forecast
        const forecastResponse = await axios.get(
          `http://localhost:5000/forecast?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("Forecast API Response:", forecastResponse.data);
        setForecastData(forecastResponse.data || []);

        // Fetch IoT status for selected city
        const statusResponse = await axios.get(
          `http://localhost:5000/status?city=${selectedCity.name}`
        );
        console.log("Status API Response:", statusResponse.data);
        setStatusData(statusResponse.data || null);

        // Fetch IoT network data for all cities
        const networkResponses = await Promise.all(
          cities.map((city) =>
            axios.get(`http://localhost:5000/status?city=${city.name}`)
          )
        );
        console.log(
          "Network API Responses:",
          networkResponses.map((res) => res.data)
        );
        setNetworkData(networkResponses.map((res) => res.data));
      } catch (error) {
        console.error("Error fetching data:", error);
        setError("Failed to fetch data");
      }
    }
    fetchData();
  }, [selectedCity]);

  // Determine weather condition
  const getWeatherCondition = (weather) => {
    if (!weather) return "unknown";
    if (weather.rain && weather.rain > 0) return "rainy";
    if (weather.clouds && weather.clouds > 50) return "cloudy";
    return "sunny";
  };

  // Safely format missing_fields
  const formatMissingFields = (missingFields) => {
    if (Array.isArray(missingFields) && missingFields.length > 0) {
      return missingFields.join(", ");
    }
    return "None";
  };

  // Chart data for temperature, humidity, mood score
  const chartData = {
    labels: forecastData.map((f) => new Date(f.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: "Temperature (°C)",
        data: forecastData.map((f) => f.weather.temp ?? 0),
        borderColor: "#22d3ee",
        backgroundColor: "rgba(34, 211, 238, 0.2)",
        fill: true,
        tension: 0.4,
      },
      {
        label: "Humidity (%)",
        data: forecastData.map((f) => f.weather.humidity ?? 0),
        borderColor: "#60a5fa",
        backgroundColor: "rgba(96, 165, 250, 0.2)",
        fill: true,
        tension: 0.4,
      },
      {
        label: "Mood Score",
        data: forecastData.map((f) => weatherData?.mood_score ?? 50),
        borderColor: "#a78bfa",
        backgroundColor: "rgba(167, 139, 250, 0.2)",
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        labels: { color: "#e5e7eb" },
      },
      tooltip: {
        backgroundColor: "#1f2937",
        titleColor: "#e5e7eb",
        bodyColor: "#e5e7eb",
      },
    },
    scales: {
      x: { grid: { borderColor: "#4b5563" }, ticks: { color: "#e5e7eb" } },
      y: { grid: { borderColor: "#4b5563" }, ticks: { color: "#e5e7eb" } },
    },
  };

  return (
    <div className="min-h-screen text-gray-100 relative font-orbitron">
      {/* Map as background */}
      <div className="fixed inset-0 z-[-10] opacity-80">
        <MapContainer
          center={[selectedCity.lat, selectedCity.lon]}
          zoom={4}
          style={{ height: "100%", width: "100%" }}
          className="futuristic-map"
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
          />
          <MapRecenter center={[selectedCity.lat, selectedCity.lon]} zoom={4} />
          {activeTab === "weather" &&
            cities.map((city) => (
              <Circle
                key={city.name}
                center={[city.lat, city.lon]}
                radius={50000}
                pathOptions={{
                  color: "#22d3ee",
                  fillColor: "#22d3ee",
                  fillOpacity: 0.5,
                }}
                eventHandlers={{
                  click: () => setSelectedCity(city),
                }}
              >
                <Popup className="futuristic-popup">
                  <span className="text-gray-100">{city.name}</span>
                </Popup>
              </Circle>
            ))}
          {activeTab === "network" &&
            networkData.map((node) => (
              <Circle
                key={node.city}
                center={[
                  cities.find((c) => c.name === node.city)?.lat || 0,
                  cities.find((c) => c.name === node.city)?.lon || 0,
                ]}
                radius={50000}
                pathOptions={{
                  color: node.status === "Online" ? "#22c55e" : "#ef4444",
                  fillColor: node.status === "Online" ? "#22c55e" : "#ef4444",
                  fillOpacity: 0.5,
                }}
                eventHandlers={{
                  click: () => setSelectedNode(node),
                }}
              >
                <Popup className="futuristic-popup">
                  <div>
                    <h3 className="text-lg font-bold">{node.city}</h3>
                    <p>
                      Status:{" "}
                      <span
                        className={
                          node.status === "Online"
                            ? "text-green-400"
                            : "text-red-400"
                        }
                      >
                        {node.status}
                      </span>
                    </p>
                    <p>Pi ID: {node.pi_id ?? "N/A"}</p>
                    <p>Sensor ID: {node.sensor_id ?? "N/A"}</p>
                    <p className="mt-2 font-semibold">Recent Logs:</p>
                    <ul className="text-sm">
                      {nodeLogs[node.city]?.map((log, idx) => (
                        <li key={idx}>{log}</li>
                      ))}
                    </ul>
                  </div>
                </Popup>
              </Circle>
            ))}
        </MapContainer>
      </div>

      {/* Main content */}
      <div className="relative z-10 container mx-auto p-6">
        <header className="mb-6 text-center">
          <motion.h1
            className="text-5xl font-bold text-cyan-400"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            MoodCast
          </motion.h1>
        </header>

        {/* Tabs */}
        <div className="mb-6 flex justify-center space-x-4">
          <motion.button
            className={`px-4 py-2 rounded-lg ${
              activeTab === "weather"
                ? "bg-cyan-500 text-gray-900"
                : "bg-gray-800 text-cyan-400 border border-cyan-400"
            }`}
            onClick={() => setActiveTab("weather")}
            whileHover={{
              scale: 1.05,
              boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
            }}
          >
            Weather
          </motion.button>
          <motion.button
            className={`px-4 py-2 rounded-lg ${
              activeTab === "network"
                ? "bg-cyan-500 text-gray-900"
                : "bg-gray-800 text-cyan-400 border border-cyan-400"
            }`}
            onClick={() => setActiveTab("network")}
            whileHover={{
              scale: 1.05,
              boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
            }}
          >
            IoT Network
          </motion.button>
        </div>

        {activeTab === "weather" && (
          <>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-cyan-400 mb-2">
                Select City
              </h2>
              <motion.select
                className="p-3 w-full bg-gray-800 text-gray-100 rounded-lg border border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                onChange={(e) => {
                  const city = cities.find((c) => c.name === e.target.value);
                  if (city) setSelectedCity(city);
                }}
                value={selectedCity.name}
                whileHover={{ scale: 1.02 }}
              >
                {cities.map((city) => (
                  <option
                    key={city.name}
                    value={city.name}
                    className="bg-gray-800"
                  >
                    {city.name}
                  </option>
                ))}
              </motion.select>
            </div>

            {error && <p className="text-red-400 mb-4">{error}</p>}

            {weatherData && (
              <motion.div
                className="mb-6 p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                whileHover={{
                  scale: 1.02,
                  boxShadow: "0 0 15px rgba(34, 211, 238, 0.3)",
                }}
              >
                <h3 className="text-3xl font-semibold text-cyan-400 mb-2 flex items-center">
                  <WeatherAnimation
                    condition={getWeatherCondition(weatherData.weather)}
                  />
                  {weatherData.city}
                </h3>
                <div
                  className="grid grid-cols-1 sm:grid-cols-2 gap-4 cursor-pointer"
                  onClick={() => setShowWeatherDetails(!showWeatherDetails)}
                >
                  <p>Temp: {weatherData.weather?.temp ?? "N/A"}°C</p>
                  <p>Humidity: {weatherData.weather?.humidity ?? "N/A"}%</p>
                  <p>Pressure: {weatherData.weather?.pressure ?? "N/A"}hPa</p>
                  <p>
                    Wind Speed: {weatherData.weather?.wind_speed ?? "N/A"}m/s
                  </p>
                  <p>Clouds: {weatherData.weather?.clouds ?? "N/A"}%</p>
                  <p>Rain: {weatherData.weather?.rain ?? "N/A"}mm</p>
                </div>
                <motion.p
                  className="text-lg mt-4 text-purple-400"
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ repeat: Infinity, duration: 2 }}
                >
                  Mood Score: {weatherData.mood_score ?? "N/A"}/100
                </motion.p>
                {showWeatherDetails && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <p>Source: {weatherData.source ?? "N/A"}</p>
                    <p className="mt-2 font-semibold text-cyan-400">
                      Quality Metrics:
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <p>
                        Completeness:{" "}
                        {weatherData.quality?.completeness ?? "N/A"}%
                      </p>
                      <p>
                        Freshness: {weatherData.quality?.freshness ?? "N/A"}s
                      </p>
                      <p>
                        Missing Fields:{" "}
                        {formatMissingFields(
                          weatherData.quality?.missing_fields
                        )}
                      </p>
                      {weatherData.quality?.error && (
                        <p>Error: {weatherData.quality.error}</p>
                      )}
                    </div>
                    <p className="mt-2 font-semibold text-cyan-400">
                      IoT Node:
                    </p>
                    <p>Pi ID: {weatherData.iot_node?.pi_id ?? "N/A"}</p>
                    <p>Sensor ID: {weatherData.iot_node?.sensor_id ?? "N/A"}</p>
                  </motion.div>
                )}
              </motion.div>
            )}

            {statusData && (
              <motion.div
                className="mb-6 p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                whileHover={{
                  scale: 1.02,
                  boxShadow: "0 0 15px rgba(34, 211, 238, 0.3)",
                }}
              >
                <h3 className="text-xl font-semibold text-cyan-400 mb-2">
                  IoT Node Status
                </h3>
                <p>City: {statusData.city}</p>
                <p>
                  Status:{" "}
                  <span
                    className={
                      statusData.status === "Online"
                        ? "text-green-400"
                        : "text-red-400"
                    }
                  >
                    {statusData.status}
                  </span>
                </p>
                <p>Data Freshness: {statusData.freshness ?? "N/A"}s</p>
                <p>Pi ID: {statusData.pi_id ?? "N/A"}</p>
                <p>Sensor ID: {statusData.sensor_id ?? "N/A"}</p>
              </motion.div>
            )}

            {forecastData.length > 0 && (
              <motion.div
                className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              >
                <h3 className="text-2xl font-semibold text-cyan-400 mb-4">
                  72-Hour Forecast
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  <AnimatePresence>
                    {forecastData.slice(0, 6).map((forecast, index) => (
                      <motion.div
                        key={index}
                        className="p-4 bg-gray-700 bg-opacity-80 rounded-lg border border-cyan-400 cursor-pointer"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{
                          duration: 0.3,
                          ease: "easeOut",
                          delay: index * 0.1,
                        }}
                        whileHover={{
                          scale: 1.05,
                          boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
                        }}
                      >
                        <p className="font-semibold text-cyan-400">
                          {new Date(forecast.timestamp).toLocaleString()}
                        </p>
                        <p>Temp: {forecast.weather.temp ?? "N/A"}°C</p>
                        <p>Rain: {forecast.weather.rain ?? "N/A"}mm</p>
                        <p>Clouds: {forecast.weather.clouds ?? "N/A"}%</p>
                        <WeatherAnimation
                          condition={getWeatherCondition(forecast.weather)}
                        />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
                <h3 className="text-xl font-semibold text-cyan-400 mb-4">
                  Forecast Trends
                </h3>
                <div className="p-4 bg-gray-700 rounded-lg">
                  <Line data={chartData} options={chartOptions} />
                </div>
              </motion.div>
            )}
          </>
        )}

        {activeTab === "network" && (
          <motion.div
            className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <h3 className="text-2xl font-semibold text-cyan-400 mb-4">
              IoT Network Architecture
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              <AnimatePresence>
                {networkData.map((node, index) => (
                  <motion.div
                    key={node.city}
                    className="p-4 bg-gray-700 bg-opacity-80 rounded-lg border border-cyan-400 cursor-pointer"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    whileHover={{
                      scale: 1.05,
                      boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
                    }}
                    onClick={() => setSelectedNode(node)}
                  >
                    <h4 className="text-lg font-semibold text-cyan-400">
                      {node.city}
                    </h4>
                    <p>
                      Status:{" "}
                      <span
                        className={
                          node.status === "Online"
                            ? "text-green-400"
                            : "text-red-400"
                        }
                      >
                        {node.status}
                      </span>
                    </p>
                    <p>Pi ID: {node.pi_id ?? "N/A"}</p>
                    <p>Sensor ID: {node.sensor_id ?? "N/A"}</p>
                    <p>Freshness: {node.freshness ?? "N/A"}s</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            {selectedNode && (
              <motion.div
                className="p-4 bg-gray-700 bg-opacity-80 rounded-lg border border-cyan-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <h4 className="text-xl font-semibold text-cyan-400 mb-2">
                  {selectedNode.city} Details
                </h4>
                <p>
                  Status:{" "}
                  <span
                    className={
                      selectedNode.status === "Online"
                        ? "text-green-400"
                        : "text-red-400"
                    }
                  >
                    {selectedNode.status}
                  </span>
                </p>
                <p>Pi ID: {selectedNode.pi_id ?? "N/A"}</p>
                <p>Sensor ID: {selectedNode.sensor_id ?? "N/A"}</p>
                <p>Freshness: {selectedNode.freshness ?? "N/A"}s</p>
                <p className="mt-2 font-semibold text-cyan-400">Recent Logs:</p>
                <ul className="text-sm text-gray-300">
                  {nodeLogs[selectedNode.city]?.map((log, idx) => (
                    <li key={idx}>{log}</li>
                  ))}
                </ul>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default App;
