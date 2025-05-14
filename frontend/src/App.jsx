import { useState, useEffect } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { MapContainer, TileLayer, Circle, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Line } from "react-chartjs-2";
import { Chart, registerables } from "chart.js";
import { formatInTimeZone } from "date-fns-tz";
import { Tooltip } from "react-tooltip";
import "./App.css";

// Register Chart.js components
Chart.register(...registerables);

// Fix Leaflet marker icon issue
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
  const [forecastData, setForecastData] = useState({ api: [], model: [] });
  const [statusData, setStatusData] = useState(null);
  const [networkData, setNetworkData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("weather");
  const [showWeatherDetails, setShowWeatherDetails] = useState(false);
  const [predictionSource, setPredictionSource] = useState("api");
  const [selectedNode, setSelectedNode] = useState(null);
  const [showInfo, setShowInfo] = useState(false);

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

        // Fetch 48-hour forecast
        const forecastResponse = await axios.get(
          `http://localhost:5000/forecast?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("Forecast API Response:", forecastResponse.data);
        const now = new Date();
        const fortyEightHoursLater = new Date(
          now.getTime() + 48 * 60 * 60 * 1000
        );
        const filteredForecast = {
          api: (forecastResponse.data.api || []).filter(
            (f) => new Date(f.timestamp) <= fortyEightHoursLater
          ),
          model: (forecastResponse.data.model || []).filter(
            (f) => new Date(f.timestamp) <= fortyEightHoursLater
          ),
        };
        setForecastData(filteredForecast);
        console.log("Filtered Forecast Data:", filteredForecast);

        // Fetch IoT status for selected city
        const statusResponse = await axios.get(
          `http://localhost:5000/status?city=${selectedCity.name}`
        );
        console.log("Status API Response:", statusResponse.data);
        setStatusData(statusResponse.data || null);

        // Fetch all IoT nodes
        const nodesResponse = await axios.get("http://localhost:5000/nodes");
        console.log("Nodes API Response:", nodesResponse.data);
        setNetworkData(nodesResponse.data || []);

        // Fetch alerts
        const alertsResponse = await axios.get(
          `http://localhost:5000/alerts?city=${selectedCity.name}`
        );
        console.log("Alerts API Response:", alertsResponse.data);
        setAlerts(alertsResponse.data.slice(-5)); // Keep last 5 alerts
      } catch (error) {
        console.error("Error fetching data:", error);
        setError(`Failed to fetch data: ${error.message}`);
      }
    }
    fetchData();

    // Poll alerts every 60 seconds
    const alertInterval = setInterval(async () => {
      try {
        const alertsResponse = await axios.get(
          `http://localhost:5000/alerts?city=${selectedCity.name}`
        );
        setAlerts(alertsResponse.data.slice(-5));
      } catch (error) {
        console.error("Error fetching alerts:", error);
      }
    }, 60000);

    return () => clearInterval(alertInterval);
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

  // Chart data
  const chartData = {
    labels: forecastData[predictionSource].map((f) =>
      formatInTimeZone(new Date(f.timestamp), "Pacific/Auckland", "d MMM, h a")
    ),
    datasets: [
      {
        label: "Temperature (°C)",
        data: forecastData[predictionSource].map((f) => f.weather.temp ?? 0),
        borderColor: "#22d3ee",
        backgroundColor: "rgba(34, 211, 238, 0.2)",
        fill: true,
        tension: 0.4,
      },
      {
        label: "Humidity (%)",
        data: forecastData[predictionSource].map(
          (f) => f.weather.humidity ?? 0
        ),
        borderColor: "#60a5fa",
        backgroundColor: "rgba(96, 165, 250, 0.2)",
        fill: true,
        tension: 0.4,
      },
      {
        label: "Mood Score",
        data: forecastData[predictionSource].map((f) => f.mood_score ?? 50),
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
      legend: { labels: { color: "#e5e7eb" } },
      tooltip: {
        backgroundColor: "#1f2937",
        titleColor: "#e5e7eb",
        bodyColor: "#e5e7eb",
      },
    },
    scales: {
      x: {
        grid: { borderColor: "#4b5563" },
        ticks: { color: "#e5e7eb" },
        afterFit: (scale) => {
          scale.backgroundColor = "rgba(34, 211, 238, 0.1)";
        },
      },
      y: { grid: { borderColor: "#4b5563" }, ticks: { color: "#e5e7eb" } },
    },
  };

  const renderInfoTab = () => (
    <motion.div
      className=" p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 150 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h3 className="text-2xl font-orbitron-semibold text-cyan-400 mb-4">
        Barometric Data Insights
      </h3>
      <motion.button
        className="px-4 py-2 bg-cyan-500 text-gray-900 rounded-lg"
        onClick={() => setShowInfo(true)}
        whileHover={{
          scale: 1.05,
          boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
        }}
      >
        Learn About Barometric Data
      </motion.button>
      {showInfo && (
        <motion.div
          className="fixed inset-0 bg-gray-900 bg-opacity-80 flex items-center justify-center z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400 max-w-lg w-full"
            initial={{ scale: 0.8, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <h4 className="text-xl font-inter-semibold text-cyan-400 mb-4">
              Barometric Data Monitoring
            </h4>
            <p className="text-gray-300 mb-2 font-inter">
              <strong>
                What can you get from continuous barometric data monitoring?
              </strong>
            </p>
            <ul className="list-disc pl-5 text-gray-300 mb-4 font-inter">
              <li>
                <strong>Storm Prediction</strong>: Rapid pressure drops (4–6 hPa
                in 3 hours) signal storms, enabling alerts in MoodCast.
              </li>
              <li>
                <strong>Weather Trends</strong>: Pressure patterns predict clear
                or rainy conditions, improving forecasts.
              </li>
              <li>
                <strong>Climate Analysis</strong>: Long-term data reveals
                regional climate trends across cities like Auckland.
              </li>
              <li>
                <strong>Aviation and Navigation</strong>: Stable pressure
                ensures safe flight planning for cities like Dubai.
              </li>
            </ul>
            <p className="text-gray-300 mb-2 font-inter">
              <strong>How does the human body get affected?</strong>
            </p>
            <ul className="list-disc pl-5 text-gray-300 mb-4 font-inter">
              <li>
                <strong>Joint Pain</strong>: Low pressure increases arthritis
                pain due to tissue expansion.
              </li>
              <li>
                <strong>Headaches/Migraines</strong>: Rapid pressure changes
                trigger migraines.
              </li>
              <li>
                <strong>Heat/Cold Stress</strong>: Extreme temperatures cause
                dehydration or hypothermia.
              </li>
              <li>
                <strong>Respiratory Issues</strong>: High/low humidity affects
                asthma or allergies.
              </li>
              <li>
                <strong>Mood Impact</strong>: Low pressure and clouds correlate
                with lower mood, tracked by mood_score.
              </li>
            </ul>
            <motion.button
              className="px-4 py-2 bg-cyan-500 text-gray-900 rounded-lg"
              onClick={() => setShowInfo(false)}
              whileHover={{ scale: 1.05 }}
            >
              Close
            </motion.button>
          </motion.div>
        </motion.div>
      )}
    </motion.div>
  );

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 relative">
      <Tooltip id="mood-score-tooltip" className="futuristic-tooltip" />
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

        <div className="mb-6">
          {alerts.length > 0 && (
            <motion.div
              className="mb-4"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              {alerts.map((alert, index) => (
                <motion.div
                  key={index}
                  className={`p-3 mb-2 rounded-lg ${
                    alert.severity === "critical"
                      ? "bg-red-500 text-white"
                      : "bg-yellow-400 text-gray-900"
                  }`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                >
                  <strong>{alert.city}</strong>: {alert.message} (
                  {formatInTimeZone(
                    new Date(alert.timestamp),
                    "Pacific/Auckland",
                    "d MMM, h:mm a"
                  )}
                  )
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>

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
          <motion.button
            className={`px-4 py-2 rounded-lg ${
              activeTab === "info"
                ? "bg-cyan-500 text-gray-900"
                : "bg-gray-800 text-cyan-400 border border-cyan-400"
            }`}
            onClick={() => setActiveTab("info")}
            whileHover={{
              scale: 1.05,
              boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
            }}
          >
            Info
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
                className="mb-6 p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400 font-inter"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                whileHover={{
                  scale: 1.02,
                  boxShadow: "0 0 15px rgba(34, 211, 238, 0.3)",
                }}
              >
                <h3 className="text-3xl font-inter-semibold text-cyan-400 mb-2 flex items-center">
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
                <p
                  className="text-lg mt-4 text-purple-400 font-inter"
                  data-tooltip-id="mood-score-tooltip"
                  data-tooltip-content="Mood Score (0-100) estimates mood based on temperature and cloud cover. Formula: (100 - clouds) * (temp / 30). Higher scores indicate better mood conditions."
                >
                  Mood Score: {weatherData.mood_score ?? "N/A"}/100
                </p>
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
                <p className="font-inter">City: {statusData.city}</p>
                <p className="font-inter">
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
                <p className="font-inter">
                  Data Freshness: {statusData.freshness ?? "N/A"}s
                </p>
                <p className="font-inter">Pi ID: {statusData.pi_id ?? "N/A"}</p>
                <p className="font-inter">
                  Sensor ID: {statusData.sensor_id ?? "N/A"}
                </p>
              </motion.div>
            )}

            <motion.div
              className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              <h3 className="text-2xl font-semibold text-cyan-400 mb-4">
                48-Hour Prediction
              </h3>
              <div className="flex space-x-4 mb-4">
                <motion.button
                  className={`px-4 py-2 rounded-lg ${
                    predictionSource === "api"
                      ? "bg-cyan-500 text-gray-900"
                      : "bg-gray-800 text-cyan-400 border border-cyan-400"
                  }`}
                  onClick={() => setPredictionSource("api")}
                  whileHover={{
                    scale: 1.05,
                    boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
                  }}
                >
                  API Prediction
                </motion.button>
                <motion.button
                  className={`px-4 py-2 rounded-lg ${
                    predictionSource === "model"
                      ? "bg-cyan-500 text-gray-900"
                      : "bg-gray-800 text-cyan-400 border border-cyan-400"
                  }`}
                  onClick={() => setPredictionSource("model")}
                  whileHover={{
                    scale: 1.05,
                    boxShadow: "0 0 10px rgba(34, 211, 238, 0.5)",
                  }}
                >
                  Model Prediction
                </motion.button>
              </div>
              {forecastData[predictionSource].length === 0 ? (
                <p className="text-red-400">
                  {predictionSource === "api"
                    ? "No API forecast data available"
                    : "No sufficient data for model prediction"}
                </p>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 max-h-[400px] overflow-y-auto font-inter">
                    <AnimatePresence>
                      {forecastData[predictionSource].map((forecast, index) => (
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
                            {formatInTimeZone(
                              new Date(forecast.timestamp),
                              "Pacific/Auckland",
                              "d MMM yyyy, h:mm a"
                            )}
                          </p>
                          <p>Temp: {forecast.weather.temp ?? "N/A"}°C</p>
                          <p>Rain: {forecast.weather.rain ?? "N/A"}mm</p>
                          <p>Clouds: {forecast.weather.clouds ?? "N/A"}%</p>
                          <p
                            data-tooltip-id="mood-score-tooltip"
                            data-tooltip-content="Mood Score (0-100) estimates mood based on temperature and cloud cover. Formula: (100 - clouds) * (temp / 30). Higher scores indicate better mood conditions."
                          >
                            Mood Score: {forecast.mood_score ?? "N/A"}/100
                          </p>
                          <WeatherAnimation
                            condition={getWeatherCondition(forecast.weather)}
                          />
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                  <h3 className="text-xl font-semibold text-cyan-400 mb-4">
                    48-Hour Prediction Trends
                  </h3>
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <Line data={chartData} options={chartOptions} />
                  </div>
                </>
              )}
            </motion.div>
          </>
        )}

        {activeTab === "network" && (
          <motion.div
            className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400 h-[calc(100vh-200px)]"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <h3 className="text-2xl font-semibold text-cyan-400 mb-4">
              IoT Network Map
            </h3>
            <div className="h-[475px]">
              <MapContainer
                center={[0, 0]}
                zoom={2}
                style={{ height: "100%", width: "100%" }}
                className="futuristic-map"
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='© <a href="https://carto.com/attributions">CARTO</a>'
                />
                {networkData.map((node) => (
                  <Circle
                    key={node.city}
                    center={[node.lat, node.lon]}
                    radius={50000}
                    pathOptions={{
                      color: node.status === "Online" ? "#22c55e" : "#ef4444",
                      fillColor:
                        node.status === "Online" ? "#22c55e" : "#ef4444",
                      fillOpacity: 0.5,
                    }}
                    eventHandlers={{
                      click: () => setSelectedNode(node),
                    }}
                  >
                    <Popup className="futuristic-popup">
                      <div>
                        <h3 className="text-lg font-bold text-cyan-400">
                          {node.city}
                        </h3>
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
                        <p>Pi ID: {node.pi_id}</p>
                        <p>Sensor ID: {node.sensor_id}</p>
                        <p>Freshness: {node.freshness}s</p>
                        <motion.button
                          className="mt-2 px-3 py-1 bg-cyan-500 text-gray-900 rounded-lg"
                          onClick={() => setSelectedNode(node)}
                          whileHover={{ scale: 1.05 }}
                        >
                          View More
                        </motion.button>
                      </div>
                    </Popup>
                  </Circle>
                ))}
              </MapContainer>
            </div>
            {selectedNode && (
              <motion.div
                className="fixed inset-0 bg-gray-900 bg-opacity-80 flex items-center justify-center z-50"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <motion.div
                  className="p-6 bg-gray-800 bg-opacity-80 backdrop-blur-md rounded-xl shadow-lg border border-cyan-400 max-w-md w-full"
                  initial={{ scale: 0.8, y: 20 }}
                  animate={{ scale: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <h3 className="text-2xl font-semibold text-cyan-400 mb-4">
                    {selectedNode.city} Node Details
                  </h3>
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
                  <p>Pi ID: {selectedNode.pi_id}</p>
                  <p>Sensor ID: {selectedNode.sensor_id}</p>
                  <p>Freshness: {selectedNode.freshness}s</p>
                  <p className="mt-4 font-semibold text-cyan-400">
                    Recent Logs:
                  </p>
                  <ul className="text-sm text-gray-300 max-h-40 overflow-y-auto">
                    {selectedNode.logs.map((log, idx) => (
                      <li key={idx}>{log}</li>
                    ))}
                  </ul>
                  <motion.button
                    className="mt-4 px-4 py-2 bg-cyan-500 text-gray-900 rounded-lg"
                    onClick={() => setSelectedNode(null)}
                    whileHover={{ scale: 1.05 }}
                  >
                    Close
                  </motion.button>
                </motion.div>
              </motion.div>
            )}
          </motion.div>
        )}

        {activeTab === "info" && renderInfoTab()}
      </div>
    </div>
  );
}

export default App;
