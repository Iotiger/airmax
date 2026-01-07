"""
Helper functions for booking data processing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import country_converter as cc
from app.logger import log_info, log_warning, log_error, log_debug


def is_round_trip(booking_data: Dict[str, Any]) -> bool:
    """
    Check if this is a round trip booking based on order field
    """
    return booking_data.get("order") is not None and booking_data.get("order", {}).get("display_id") is not None


def get_order_display_id(booking_data: Dict[str, Any]) -> Optional[str]:
    """
    Get the order display ID for round trip bookings
    """
    order = booking_data.get("order")
    if order and isinstance(order, dict):
        return order.get("display_id")
    return None


def extract_flight_numbers(booking_data: Dict[str, Any]) -> List[int]:
    """
    Extract flight numbers from booking data (legacy method - kept for backward compatibility)
    This will be replaced by get_flight_identifiers_from_api which uses the Airmax API
    """
    flights = []
    booking_custom_fields = {field["name"]: field["value"] for field in booking_data.get("custom_field_values", [])}
    
    for field_name, field_value in booking_custom_fields.items():
        if "Flight Number" in field_name:
            # Extract flight number from field name (e.g., "Flight Number 516" -> 516)
            numbers = re.findall(r'\d+', field_name)
            if numbers:
                flights.append(int(numbers[0]))
                continue
            
            # If no number in field name, try to extract from field value if it's not empty
            if field_value.strip():
                try:
                    flight_num = int(field_value.strip())
                    flights.append(flight_num)
                except ValueError:
                    pass
    
    # If no flight numbers found in custom fields, fall back to availability item pk
    if not flights and booking_data.get("availability") and booking_data["availability"].get("item"):
        flights.append(booking_data["availability"]["item"]["pk"])
    
    return flights


async def get_flight_identifiers_from_api(booking_data: Dict[str, Any]) -> List[int]:
    """
    Get flight identifiers by searching flights via Airmax API
    This is the new method that replaces extract_flight_numbers
    """
    from app.api_client import search_flights
    
    try:
        # Step 1: Build flight search payload
        search_payload = build_flight_search_payload(booking_data)
        
        # Step 2: Call flight search API
        search_result = await search_flights(search_payload)
        
        if not search_result.get("success"):
            log_warning("Flight search failed", {"error": search_result.get('error')})
            # Fallback to old method
            return extract_flight_numbers(booking_data)
        
        # Step 3: Extract flight list from response
        flight_list_response = search_result.get("response", {})
        
        # Handle different response formats - could be a list directly or wrapped in an object
        flight_list = flight_list_response.get("DepartFlights", [])
        
        if not flight_list:
            log_warning("No flights found in search response")
            # Fallback to old method
            return extract_flight_numbers(booking_data)
        
        # Step 4: Extract FlightDate and FlightNumber from booking
        flight_date, flight_number = extract_flight_date_and_number(booking_data)
        
        if not flight_date or not flight_number:
            log_warning("Could not extract flight_date or flight_number from booking")
            # Fallback to old method
            return extract_flight_numbers(booking_data)
        
        # Step 5: Find matching flight identifiers
        flight_identifiers = find_flight_identifier(flight_list, flight_date, flight_number)
        
        if flight_identifiers:
            return flight_identifiers
        else:
            log_warning("Could not find matching flight identifier", {"flight_number": flight_number})
            # Fallback to old method
            return extract_flight_numbers(booking_data)
            
    except Exception as e:
        log_error("Exception in get_flight_identifiers_from_api", str(e))
        # Fallback to old method
        return extract_flight_numbers(booking_data)


def determine_flight_directions(existing_flights: List[int], current_flights: List[int], 
                              existing_booking: Dict[str, Any], current_booking: Dict[str, Any]) -> tuple[List[int], List[int]]:
    """
    Determine which flights are depart and which are return based on flight dates
    Flight with earlier date = depart flight
    Flight with later date = return flight
    """
    # Extract flight dates from both bookings
    existing_date_str = existing_booking.get("availability", {}).get("start_at", "")
    current_date_str = current_booking.get("availability", {}).get("start_at", "")
    
    try:
        # Parse dates for comparison
        existing_date = None
        current_date = None
        
        if existing_date_str:
            # Fix timezone format if needed
            if not existing_date_str.endswith('Z'):
                timezone_pattern = r'([+-])(\d{2})(\d{2})$'
                match = re.search(timezone_pattern, existing_date_str)
                if match:
                    sign, hours, minutes = match.groups()
                    existing_date_str = existing_date_str[:match.start()] + f"{sign}{hours}:{minutes}"
            existing_date = datetime.fromisoformat(existing_date_str.replace('Z', '+00:00'))
        
        if current_date_str:
            # Fix timezone format if needed
            if not current_date_str.endswith('Z'):
                timezone_pattern = r'([+-])(\d{2})(\d{2})$'
                match = re.search(timezone_pattern, current_date_str)
                if match:
                    sign, hours, minutes = match.groups()
                    current_date_str = current_date_str[:match.start()] + f"{sign}{hours}:{minutes}"
            current_date = datetime.fromisoformat(current_date_str.replace('Z', '+00:00'))
        
        # Compare dates and assign flights accordingly
        if existing_date and current_date:
            if existing_date < current_date:
                # Existing booking has earlier date -> depart flight
                # Current booking has later date -> return flight
                depart_flights = existing_flights
                return_flights = current_flights
            else:
                # Current booking has earlier date -> depart flight
                # Existing booking has later date -> return flight
                depart_flights = current_flights
                return_flights = existing_flights
        else:
            # Fallback to order-based logic if dates can't be parsed
            log_warning(
                "Could not parse flight dates, using order-based logic",
                {
                    "existing_date_str": existing_date_str,
                    "current_date_str": current_date_str
                }
            )
            depart_flights = existing_flights  # First request is depart
            return_flights = current_flights  # Second request is return
        
        return depart_flights, return_flights
            
    except Exception as e:
        # Fallback to order-based logic if date parsing fails
        log_warning(
            f"Error parsing flight dates: {str(e)}, using order-based logic",
            {
                "existing_date_str": existing_date_str,
                "current_date_str": current_date_str
            }
        )
        depart_flights = existing_flights  # First request is depart
        return_flights = current_flights  # Second request is return
        return depart_flights, return_flights


def get_country_iso3(country_name: str) -> str:
    """
    Convert country name to ISO3 code using country-converter
    """
    if not country_name:
        return ""
    
    # If already an ISO3 code (3 uppercase letters), return as-is
    if len(country_name) == 3 and country_name.isupper() and country_name.isalpha():
        return country_name
    
    try:
        # Try to convert country name to ISO3 code
        iso3_code = cc.convert(country_name, to='ISO3')
        
        # If conversion returns the same string, it means no match was found
        if iso3_code == country_name:
            log_warning(f"Country '{country_name}' not found in country converter, using original name", {"country_name": country_name})
            return country_name
        
        return iso3_code
        
    except Exception as e:
        log_warning(f"Error converting country '{country_name}'", None, {"country_name": country_name, "error": str(e)})
        return country_name


def clean_name(name: str) -> str:
    """
    Remove all special characters from a name, keeping only letters (A-Z, a-z).
    Examples:
        D'Agostino -> DAgostino
        Carter-Bowers -> CarterBowers
        O'Brien -> OBrien
    """
    if not name:
        return ""
    
    # Remove all non-letter characters, keep only A-Z and a-z
    cleaned = re.sub(r'[^A-Za-z]', '', name)
    return cleaned


def clean_phone(phone: str) -> str:
    """
    Remove all special characters from a phone number, keeping only digits.
    Examples:
        +34(241)-335-39-39 -> 342413353939
        (555) 123-4567 -> 5551234567
        +1-800-555-1234 -> 18005551234
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters, keep only 0-9
    cleaned = re.sub(r'[^\d]', '', phone)
    return cleaned


def clean_alphanumeric(value: str) -> str:
    """
    Remove all spaces and special characters, keeping only letters and numbers.
    Examples:
        555 555 987 -> 555555987
        AB 123 CD -> AB123CD
        A1-B2 C3 -> A1B2C3
    """
    if not value:
        return ""
    
    # Remove all non-alphanumeric characters, keep only A-Z, a-z, and 0-9
    cleaned = re.sub(r'[^A-Za-z0-9]', '', value)
    return cleaned


def get_flight_direction(booking_data: Dict[str, Any]) -> str:
    """
    Determine if a flight is depart or return based on the availability item name
    (Kept for potential future use, though not currently used in round trip logic)
    """
    item_name = booking_data.get("availability", {}).get("item", {}).get("name", "")
    
    # Check for common patterns in flight direction
    if "Fort Lauderdale Executive (FXE)" in item_name and "South Andros (COX)" in item_name:
        if item_name.startswith("Fort Lauderdale Executive (FXE)"):
            return "depart"  # FXE -> COX is depart
        else:
            return "return"  # COX -> FXE is return
    elif "South Andros (COX)" in item_name and "Fort Lauderdale Executive (FXE)" in item_name:
        if item_name.startswith("South Andros (COX)"):
            return "return"  # COX -> FXE is return
        else:
            return "depart"  # FXE -> COX is depart
    
    # Default fallback - assume it's depart if we can't determine
    log_warning(f"Could not determine flight direction for: {item_name}", {"item_name": item_name})
    return "depart"


def extract_airport_codes(item_name: str) -> tuple:
    """
    Extract origin and destination airport codes from item name
    Example: "Fort Lauderdale Executive (FXE) → South Andros (COX)" -> ("FXE", "COX")
    """
    # Pattern to match airport codes in parentheses
    pattern = r'\(([A-Z]{3})\)'
    matches = re.findall(pattern, item_name)
    
    if len(matches) >= 2:
        return matches[0], matches[1]
    elif len(matches) == 1:
        # Only one code found, might be a different format
        return matches[0], None
    
    return None, None


def build_flight_search_payload(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build flight search payload from booking data
    """
    availability = booking_data.get("availability", {})
    item = availability.get("item", {})
    item_name = item.get("name", "")
    start_at = availability.get("start_at", "")
    
    # Extract origin and destination
    origin, destination = extract_airport_codes(item_name)
    
    if not origin or not destination:
        raise ValueError(f"Could not extract airport codes from item name: {item_name}")
    
    # Extract date from start_at (format: "2025-10-28T08:00:00-0400")
    try:
        # Fix timezone format: convert -0400 to -04:00 for ISO format
        if start_at and not start_at.endswith('Z'):
            # Try to fix timezone format (e.g., -0400 -> -04:00)
            import re
            timezone_pattern = r'([+-])(\d{2})(\d{2})$'
            match = re.search(timezone_pattern, start_at)
            if match:
                sign, hours, minutes = match.groups()
                start_at = start_at[:match.start()] + f"{sign}{hours}:{minutes}"
        
        # Parse ISO format date
        date_obj = datetime.fromisoformat(start_at.replace('Z', '+00:00'))
        date_str = date_obj.strftime("%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Could not parse date from start_at: {start_at}, error: {e}")
    
    # Count passengers
    customers = booking_data.get("customers", [])
    adult_count = 1
    infant_count = 0
    
    # Build payload
    payload = {
        "DepartDateStart": date_str,
        "DepartDateEnd": date_str,
        "DepartOrigin": origin,
        "DepartDestination": destination,
        "AdultCount": adult_count,
        "InfantCount": infant_count,
        "IsDepartFirstClass": False
    }
    
    return payload


def extract_flight_date_and_number(booking_data: Dict[str, Any]) -> tuple:
    """
    Extract FlightDate and FlightNumber from booking data
    Returns: (FlightDate, FlightNumber)
    
    Flight number extraction priority:
    1. From availability.item.headline (e.g., "N146WM - 2112" -> "2112")
    2. From custom_field_values with "Flight Number" in name
    3. Fallback to None
    """
    # Extract FlightDate from availability.start_at
    availability = booking_data.get("availability", {})
    start_at = availability.get("start_at", "")
    
    flight_date = None
    if start_at:
        try:
            # Parse ISO format date and return as-is (with time)
            flight_date = start_at
        except Exception as e:
            log_warning("Could not parse flight date", {"start_at": start_at, "error": str(e)})
    
    # Extract FlightNumber - Priority 1: From availability headline (e.g., "N146WM - 2112")
    flight_number = None
    headline = availability.get("headline", "")
    
    if headline:
        # Extract flight number from headline format: "N146WM - 2112" -> "2112"
        # Pattern: look for digits after " - " or at the end
        headline_match = re.search(r'\s*-\s*(\d+)$', headline)
        if headline_match:
            flight_number = headline_match.group(1)
        else:
            # Try to find any sequence of digits at the end
            digits_match = re.search(r'(\d+)$', headline.strip())
            if digits_match:
                flight_number = digits_match.group(1)
    
    # Priority 2: Extract FlightNumber from custom_field_values if not found in headline
    if not flight_number:
        booking_custom_fields = booking_data.get("custom_field_values", [])
        
        for field in booking_custom_fields:
            field_name = field.get("name", "")
            if "Flight Number" in field_name:
                # Extract flight number from field name (e.g., "Flight Number 516" -> "516")
                numbers = re.findall(r'\d+', field_name)
                if numbers:
                    flight_number = numbers[0]
                    break
                # Or try to get from display_value if available
                display_value = field.get("display_value", "")
                if display_value and display_value.strip().isdigit():
                    flight_number = display_value.strip()
                    break
    
    if not flight_number:
        log_warning("Could not extract flight number from booking data")
    
    return flight_date, flight_number


def find_flight_identifier(flight_list: List[Dict[str, Any]], flight_date: str, flight_number: str) -> Optional[List[int]]:
    """
    Find flight identifiers from flight list that matches FlightDate and FlightNumber
    Returns a list of identifiers (can contain multiple if FlightIdentifier is comma-separated)
    """
    if not flight_date or not flight_number:
        log_warning("Cannot find flight identifier - missing flight_date or flight_number", {"flight_date": flight_date, "flight_number": flight_number})
        return None
    
    # Parse the flight_date to get just the date part for comparison
    try:
        # Fix timezone format: convert -0400 to -04:00 for ISO format
        flight_date_fixed = flight_date
        if flight_date and not flight_date.endswith('Z'):
            timezone_pattern = r'([+-])(\d{2})(\d{2})$'
            match = re.search(timezone_pattern, flight_date)
            if match:
                sign, hours, minutes = match.groups()
                flight_date_fixed = flight_date[:match.start()] + f"{sign}{hours}:{minutes}"
        
        # Parse ISO format: "2025-10-28T08:00:00-04:00"
        date_obj = datetime.fromisoformat(flight_date_fixed.replace('Z', '+00:00'))
        date_only = date_obj.strftime("%Y-%m-%d")
        time_part = date_obj.strftime("%H:%M:%S")
    except Exception as e:
        log_warning("Could not parse flight_date", {"flight_date": flight_date, "error": str(e)})
        return None
    
    
    # Search through flight list
    for flight in flight_list:
        # Check flight date and number
        flight_date_str = flight.get("FlightDate", "")
        flight_number_str = str(flight.get("FlightNumber", ""))
        
        # Parse flight date for comparison
        try:
            # Fix timezone format if needed
            flight_date_fixed = flight_date_str
            if flight_date_str and not flight_date_str.endswith('Z'):
                timezone_pattern = r'([+-])(\d{2})(\d{2})$'
                match = re.search(timezone_pattern, flight_date_str)
                if match:
                    sign, hours, minutes = match.groups()
                    flight_date_fixed = flight_date_str[:match.start()] + f"{sign}{hours}:{minutes}"
            
            flight_date_obj = datetime.fromisoformat(flight_date_fixed.replace('Z', '+00:00'))
            flight_date_only = flight_date_obj.strftime("%Y-%m-%d")
            flight_time_part = flight_date_obj.strftime("%H:%M:%S")
        except Exception as e:
            continue
        
        # Match date and flight number
        if flight_date_only == date_only and flight_number_str == flight_number:
            flight_identifier = flight.get("FlightIdentifier") or flight.get("Identifier") or flight.get("Id")
            if flight_identifier:
                # FlightIdentifier might be a comma-separated string like "35437, 35440"
                # Extract all identifiers
                identifiers = []
                if isinstance(flight_identifier, str):
                    # Split by comma and extract all identifiers
                    identifier_strs = [s.strip() for s in flight_identifier.split(",")]
                    for identifier_str in identifier_strs:
                        try:
                            identifier_int = int(identifier_str)
                            identifiers.append(identifier_int)
                        except ValueError:
                            log_warning("Could not parse FlightIdentifier part", {"identifier_str": identifier_str, "flight_identifier": flight_identifier})
                    
                    if identifiers:
                        return identifiers
                    else:
                        log_warning("Could not parse any FlightIdentifier", {"flight_identifier": flight_identifier, "flight": flight})
                        return None
                else:
                    # Already an integer, convert to list
                    return [int(flight_identifier)]
            else:
                log_warning("Found matching flight but no identifier field", {"flight": flight})
    
    log_warning("No matching flight found", {"date": date_only, "flight_number": flight_number, "flight_list_count": len(flight_list)})
    return None

