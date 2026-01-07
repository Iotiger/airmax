"""
Booking data transformation functions
"""

from typing import Dict, Any, List
from datetime import datetime
import calendar
from app.helpers import get_country_iso3, clean_name, clean_phone, clean_alphanumeric


def transform_booking_data(booking_data: Dict[str, Any], depart_flights: List[int] = None, return_flights: List[int] = None) -> Dict[str, Any]:
    """
    Transform FareHarbor booking data to MakerSuite API format
    """
    try:
        # Use provided flight numbers if available (for round trip), otherwise extract from booking
        if depart_flights is None:
            depart_flights = _extract_depart_flights(booking_data)
        
        # Use provided return flights if available, otherwise empty
        if return_flights is None:
            return_flights = []
        
        # Get booking-level custom fields for address information
        booking_custom_fields = {field["name"]: field["value"] for field in booking_data.get("custom_field_values", [])}
        
        # Transform passengers data
        passengers = _transform_passengers(booking_data, booking_custom_fields)
        
        # Build the final payload
        transformed_data = {
            "DepartFlights": depart_flights,
            "ReturnFlights": return_flights,
            "Passengers": passengers,
            "IsDepartFirstClass": False,
            "IsReturnFirstClass": False
        }
        
        return transformed_data
        
    except Exception as e:
        print(f"Error transforming booking data: {str(e)}")
        raise


def _extract_depart_flights(booking_data: Dict[str, Any]) -> List[int]:
    """
    Extract depart flight numbers from booking data
    """
    depart_flights = []
    booking_custom_fields = {field["name"]: field["value"] for field in booking_data.get("custom_field_values", [])}
    
    # Look for flight number fields (they typically contain "Flight Number" in the name)
    for field_name, field_value in booking_custom_fields.items():
        if "Flight Number" in field_name:
            import re
            
            # Extract flight number from field name (e.g., "Flight Number 516" -> 516)
            numbers = re.findall(r'\d+', field_name)
            if numbers:
                depart_flights.append(int(numbers[0]))
                continue
            
            # If no number in field name, try to extract from field value if it's not empty
            if field_value.strip():
                try:
                    flight_num = int(field_value.strip())
                    depart_flights.append(flight_num)
                except ValueError:
                    pass
    
    # If no flight numbers found in custom fields, fall back to availability item pk
    if not depart_flights and booking_data.get("availability") and booking_data["availability"].get("item"):
        depart_flights.append(booking_data["availability"]["item"]["pk"])
    
    return depart_flights


def _transform_passengers(booking_data: Dict[str, Any], booking_custom_fields: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Transform passenger data from FareHarbor format to MakerSuite format
    """
    passengers = []
    for customer in booking_data.get("customers", []):
        passenger = {}
        
        # Extract passenger details from custom field values
        custom_fields = {field["name"]: field["display_value"] for field in customer.get("custom_field_values", [])}
        
        # Map FareHarbor fields to MakerSuite format
        # Clean names to remove special characters (hyphens, apostrophes, slashes, etc.)
        passenger["FirstName"] = clean_name(custom_fields.get("Passenger First Name", ""))
        passenger["LastName"] = clean_name(custom_fields.get("Passenger Last Name", ""))
        
        # Convert date format from MM/DD/YYYY to YYYY-MM-DD
        passenger["DateOfBirth"] = _convert_date_format(custom_fields.get("Date of Birth - Year", ""), custom_fields.get("Date of Birth - Month", ""), custom_fields.get("Date of Birth - Day", ""))
        
       # Map gender
        gender_display = custom_fields.get("Passenger Sex", "")
        passenger["Gender"] = "M" if "Male" in gender_display else "F"
        
        # Contact information
        passenger["Email"] = booking_data.get("contact", {}).get("email", "")
        passenger["Phone"] = clean_phone(booking_data.get("contact", {}).get("phone", ""))
        
        # Document information
        passenger["DocumentNumber"] = clean_alphanumeric(custom_fields.get("Passport Number", ""))
        passenger["DocumentType"] = "P"  # P for Passport
        passenger["DocumentExpiry"] = _convert_date_format(custom_fields.get("Passport Expiration Date - Year", ""), custom_fields.get("Passport Expiration Date - Month", ""), custom_fields.get("Passport Expiration Date - Day", ""))
        
        # Convert country name to ISO3 code
        citizenship = custom_fields.get("Citizenship", "")
        passenger["DocumentCountry"] = get_country_iso3(citizenship)
        
        # Weight
        passenger["Weight"] = 185
        passenger["BahamasStay"] = custom_fields.get("Bahamas Hotel", "BHS")  # Default value as specified
        
        # Address information from booking-level custom fields
        passenger["AddressStreet"] = booking_custom_fields.get("US Address – Street", "")
        passenger["AddressCity"] = booking_custom_fields.get("US Address – City", "")
        passenger["AddressState"] = booking_custom_fields.get("US Address – State", "")
        passenger["AddressZIPCode"] = booking_custom_fields.get("US Address – Zip Code", "")  

        passengers.append(passenger)
    
    return passengers


def _convert_date_format(year: str, month: str, day: str) -> str:
    """
    Convert date format to YYYY-MM-DD
    Handles month as either integer string or month name (e.g., "January", "February")
    """
    if not year or not month or not day:
        return ""
    
    try:
        # Convert month name to number if needed
        month_num = _parse_month(month)
        if month_num is None:
            return ""
        
        d = datetime(int(year), month_num, int(day))
        return d.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error converting date format: {str(e)}")
        return ""


def _parse_month(month: str) -> int:
    """
    Parse month string to integer (1-12)
    Handles both numeric strings and month names (e.g., "January", "February")
    """
    if not month:
        return None
    
    month = month.strip()
    
    # Try to parse as integer first
    try:
        month_num = int(month)
        if 1 <= month_num <= 12:
            return month_num
    except ValueError:
        pass
    
    # Try to match month name (case-insensitive)
    month_lower = month.lower()
    for i, month_name in enumerate(calendar.month_name[1:], start=1):
        if month_lower == month_name.lower():
            return i
    
    # Try abbreviated month names (Jan, Feb, etc.)
    for i, month_abbr in enumerate(calendar.month_abbr[1:], start=1):
        if month_lower == month_abbr.lower():
            return i
    
    return None

