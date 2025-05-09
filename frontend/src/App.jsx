import { useState, useEffect } from "react";
import mqtt from "mqtt";
import { WiDaySunny, WiCloudy, WiRain, WiWindy } from "react-icons/wi";
import "./App.css";

function App() {
  const [weather, setWeather] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [moodSuggestion, setMoodSuggestion] = useState("");

  useEffect(() => {
    // Connect to MQTT broker
    const client = mqtt.connect("ws://localhost:8083", {
      clientId: "moodcast_frontend_" + Math.random().toString(16).slice(3),
      protocolVersion: 4, // MQTT 3.1.1
    });

    client.on("connect", () => {
      console.log("Connected to MQTT broker");
      client.subscribe("moodcast/weather");
      client.subscribe("moodcast/forecast");
      client.subscribe("moodcast/alerts");
    });

    client.on("message", (topic, message) => {
      const data = JSON.parse(message.toString());
      if (topic === "moodcast/weather") {
        setWeather(data);
        updateMoodSuggestion(data);
      } else if (topic === "moodcast/forecast") {
        setForecast(data);
      } else if (topic === "moodcast/alerts") {
        setAlerts((prev) => [...prev, data.message].slice(-3));
      }
    });

    client.on("error", (err) => {
      console.error("MQTT error:", err);
    });

    return () => client.end();
  }, []);

  const updateMoodSuggestion = (data) => {
    if (!data) return;
    if (data.pressure < 1000) {
      setMoodSuggestion(
        "Low pressure detected—try a calming tea or meditation!"
      );
    } else if (data.clouds > 70) {
      setMoodSuggestion("Cloudy day? Brighten up with a fun playlist!");
    } else if (data.rain_1h > 0) {
      setMoodSuggestion("Rainy day? Earn a Cozy Reader badge by staying in!");
    } else if (
      new Date().getHours() >= new Date(data.sunset * 1000).getHours()
    ) {
      setMoodSuggestion("Sunset time—relax with a book or evening walk!");
    } else {
      setMoodSuggestion(
        "Great weather! Go for a run to earn a Sunshine badge!"
      );
    }
  };

  const getWeatherIcon = (icon) => {
    switch (icon) {
      case "01d":
      case "01n":
        return <WiDaySunny size={50} />;
      case "02d":
      case "02n":
      case "03d":
      case "03n":
      case "04d":
      case "04n":
        return <WiCloudy size={50} />;
      case "09d":
      case "09n":
      case "10d":
      case "10n":
        return <WiRain size={50} />;
      default:
        return <WiDaySunny size={50} />;
    }
  };

  return (
    <div className="app">
      <h1>MoodCast</h1>
      {/* Current Weather */}
      {weather && (
        <div className="weather">
          <h2>Current Weather in {weather.city}</h2>
          <div className="weather-icon">{getWeatherIcon(weather.icon)}</div>
          <p>
            Temperature: {weather.temperature}°C (Feels Like:{" "}
            {weather.feels_like}°C)
          </p>
          <p>Pressure: {weather.pressure} hPa</p>
          <p>Humidity: {weather.humidity}%</p>
          <p>Clouds: {weather.clouds}%</p>
          <p>Rain (1h): {weather.rain_1h} mm</p>
          <p>Description: {weather.description}</p>
          <p>
            Sunrise: {new Date(weather.sunrise * 1000).toLocaleTimeString()}
          </p>
          <p>Sunset: {new Date(weather.sunset * 1000).toLocaleTimeString()}</p>
        </div>
      )}

      {/* Mood Suggestion */}
      {moodSuggestion && (
        <div className="mood-suggestion">
          <h3>MoodSync Suggestion</h3>
          <p>{moodSuggestion}</p>
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="alerts">
          <h3>Alerts</h3>
          <ul>
            {alerts.map((alert, index) => (
              <li key={index}>{alert}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Forecast */}
      {forecast.length > 0 && (
        <div className="forecast">
          <h2>48-Hour Forecast</h2>
          <div className="forecast-list">
            {forecast.map((item, index) => (
              <div key={index} className="forecast-item">
                <p>{new Date(item.timestamp * 1000).toLocaleString()}</p>
                <div className="weather-icon">{getWeatherIcon(item.icon)}</div>
                <p>Temp: {item.temperature}°C</p>
                <p>Pressure: {item.pressure} hPa</p>
                <p>Clouds: {item.clouds}%</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
