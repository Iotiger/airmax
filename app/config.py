"""
Configuration constants for the integrations module
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# MakerSuite API configuration
MAKERSUITE_API_URL = "https://api.makerssuite.com/api/Book/CreateBooking"
MAKERSUITE_API_KEY = "AE52969F-490C-4923-81CB-6BFE27E8B7C2"

# Airmax API configuration
AIRMAX_API_BASE_URL = "https://api.makerssuite.com"
AIRMAX_FLIGHT_SEARCH_ENDPOINT = (
    "/api/FlightSearch/GetOneWayFlightsForDateRange"
)

# Round trip booking storage configuration
ROUND_TRIP_CLEANUP_HOURS = 1  # Clean up bookings older than 1 hour

# Slack notification configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
