from fetch_weather import fetch_weather, fetch_forecast
from database import store_weather_data, store_forecast_data
from mqtt_publisher import publish_weather, publish_forecast, publish_alert

CITY = "London"  # Change to your preferred city

def main():
    # Fetch and store current weather
    weather_data = fetch_weather(CITY)
    if weather_data:
        store_weather_data(
            weather_data,
            location=weather_data["city"],
            device_label="MoodCast"
        )
        publish_weather(weather_data)
        print("Current weather stored and published.")
        # Check for low pressure alert
        if weather_data["pressure"] < 1000:
            publish_alert("Low pressure detected—possible fatigue. Try a calming activity!")
    else:
        print("Failed to store current weather.")

    # Fetch and store 48-hour forecast
    forecast_data = fetch_forecast(CITY)
    if forecast_data:
        store_forecast_data(
            forecast_data,
            location=weather_data["city"] if weather_data else CITY,
            device_label="MoodCast"
        )
        publish_forecast(forecast_data)
        print("48-hour forecast stored and published.")
    else:
        print("Failed to store forecast.")

if __name__ == "__main__":
    main()