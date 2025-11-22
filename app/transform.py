"""
Booking data transformation functions
"""

from typing import Dict, Any, List
from datetime import datetime
from app.helpers import get_country_iso3


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
        passenger["FirstName"] = custom_fields.get("Passenger First Name", "")
        passenger["LastName"] = custom_fields.get("Passenger Last Name", "")
        
        # Convert date format from MM/DD/YYYY to YYYY-MM-DD
        passenger["DateOfBirth"] = _convert_date_format(custom_fields.get("Date of Birth", ""))
        
        # Map gender
        gender_display = custom_fields.get("Passenger Sex", "")
        passenger["Gender"] = "M" if "Male" in gender_display else "F"
        
        # Contact information
        passenger["Email"] = booking_data.get("contact", {}).get("email", "")
        passenger["Phone"] = booking_data.get("contact", {}).get("phone", "")
        
        # Document information
        passenger["DocumentNumber"] = custom_fields.get("Passport Number", "")
        passenger["DocumentType"] = "P"  # P for Passport
        passenger["DocumentExpiry"] = _convert_date_format(custom_fields.get("Passport Expiration Date", ""))
        
        # Convert country name to ISO3 code
        citizenship = custom_fields.get("Citizenship", "")
        passenger["DocumentCountry"] = get_country_iso3(citizenship)
        
        # Weight
        passenger["Weight"] = int(custom_fields.get("Passenger Weight", 0)) if custom_fields.get("Passenger Weight", "").isdigit() else 0
        passenger["BahamasStay"] = custom_fields.get("Bahamas Hotel", "BHS")  # Default value as specified
        
        # Address information from booking-level custom fields
        passenger["AddressStreet"] = booking_custom_fields.get("US Address – Street", "")
        passenger["AddressCity"] = booking_custom_fields.get("US Address – City", "")
        passenger["AddressState"] = booking_custom_fields.get("US Address – State", "")
        passenger["AddressZIPCode"] = booking_custom_fields.get("US Address – Zip Code", "")  

        passengers.append(passenger)
    
    return passengers


def _convert_date_format(date_str: str) -> str:
    """
    Convert date format from MM/DD/YYYY to YYYY-MM-DD
    """
    if not date_str:
        return ""
    
    try:
        dob_date = datetime.strptime(date_str, "%m/%d/%Y")
        return dob_date.strftime("%Y-%m-%d")
    except:
        return date_str

