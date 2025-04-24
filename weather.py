from typing import Any
import logging

import httpx
from mcp.server.fastmcp import FastMCP

# Init FastMCP server
mcp = FastMCP("weather")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    timeout = 30.0
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Error occurred while making NWS request to {url}: {e}")


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code, i.e. CA, NY
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    
    if not data["features"]:
        return "No active alerts for this state."
    
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # Step 1: build the forecast grid endpoint and get the points data, handle failure
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    if not points_data:
        return "Unable to fetch points data for this location."
    if "properties" not in points_data or "forecast" not in points_data["properties"]:
        return "Invalid points data received: missing forecast information."
    
    # Step 2: get the forecast URL and then the forecast data, handle validation
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)
    if not forecast_data:
        return "Unable to fetch forecast data for this location."
    if "properties" not in forecast_data or "periods" not in forecast_data["properties"]:
        return "Invalid forecast data received: missing period information."

    # Step 3: format the periods from forecast data into a human-readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    periods_count = 5
    for period in periods[:periods_count]:
        forecasts.append(f"""
{period['name']}
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
""")
        
    return "\n---\n".join(forecasts)

if __name__ == "__main__":
    mcp.run(transport='stdio')
