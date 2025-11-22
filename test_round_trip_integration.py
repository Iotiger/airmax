#!/usr/bin/env python3
"""
Integration test for round trip booking functionality
Tests the complete flow from webhook to API submission
"""

import json
import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.helpers import (
    is_round_trip,
    get_order_display_id,
    build_flight_search_payload,
    extract_flight_date_and_number,
    find_flight_identifier,
    determine_flight_directions
)
from app.storage import (
    round_trip_bookings,
    cleanup_old_bookings,
    store_round_trip_booking,
    get_round_trip_booking,
    has_round_trip_booking,
    remove_round_trip_booking
)
from app.transform import transform_booking_data


# Test data - First booking (return flight) - COX -> FXE
return_booking_data = {
    "pk": 914502,
    "uuid": "892a92f4-9095-4e43-b20f-43b41d4c9b09",
    "order": {
        "display_id": "BUJP"
    },
    "availability": {
        "pk": 77380815,
        "start_at": "2025-10-28T10:00:00-0400",
        "end_at": "2025-10-28T11:24:00-0400",
        "item": {
            "pk": 81645,
            "name": "South Andros (COX) → Fort Lauderdale Executive (FXE)"
        }
    },
    "customers": [
        {
            "pk": 3431937,
            "custom_field_values": [
                {
                    "name": "First Name",
                    "display_value": "Eric"
                },
                {
                    "name": "Last Name",
                    "display_value": "Mollergren"
                },
                {
                    "name": "Date of Birth",
                    "display_value": "11/11/2000"
                },
                {
                    "name": "Gender",
                    "display_value": "Male"
                },
                {
                    "name": "Passport Number",
                    "display_value": "123456"
                },
                {
                    "name": "Passport Expiration Date",
                    "display_value": "11/11/1983"
                },
                {
                    "name": "Citizenship",
                    "display_value": "United States"
                },
                {
                    "name": "Passenger Weight",
                    "display_value": "185"
                }
            ],
            "customer_type_rate": {
                "customer_type": {
                    "singular": "Adult",
                    "plural": "Adults"
                }
            }
        }
    ],
    "contact": {
        "email": "f.qvarnstrom8@gmail.com",
        "phone": "23423"
    },
    "custom_field_values": [
        {
            "name": "Address Street",
            "value": "Vardovagen"
        },
        {
            "name": "Address City",
            "value": "Haninge"
        },
        {
            "name": "Address State",
            "value": "324"
        },
        {
            "name": "Flight Number 517",
            "value": "1589996",
            "display_value": "517"
        }
    ]
}

# Test data - Second booking (depart flight) - FXE -> COX
depart_booking_data = {
    "pk": 914501,
    "uuid": "8b4aae42-20b4-4e77-8b53-494a01b2d37f",
    "order": {
        "display_id": "BUJP"
    },
    "availability": {
        "pk": 77380742,
        "start_at": "2025-10-28T08:00:00-0400",
        "end_at": "2025-10-28T09:24:00-0400",
        "item": {
            "pk": 80038,
            "name": "Fort Lauderdale Executive (FXE) → South Andros (COX)"
        }
    },
    "customers": [
        {
            "pk": 3431936,
            "custom_field_values": [
                {
                    "name": "First Name",
                    "display_value": "Eric"
                },
                {
                    "name": "Last Name",
                    "display_value": "Mollergren"
                },
                {
                    "name": "Date of Birth",
                    "display_value": "11/11/2000"
                },
                {
                    "name": "Gender",
                    "display_value": "Male"
                },
                {
                    "name": "Passport Number",
                    "display_value": "123456"
                },
                {
                    "name": "Passport Expiration Date",
                    "display_value": "11/11/1983"
                },
                {
                    "name": "Citizenship",
                    "display_value": "United States"
                },
                {
                    "name": "Passenger Weight",
                    "display_value": "185"
                }
            ],
            "customer_type_rate": {
                "customer_type": {
                    "singular": "Adult",
                    "plural": "Adults"
                }
            }
        }
    ],
    "contact": {
        "email": "f.qvarnstrom8@gmail.com",
        "phone": "23423"
    },
    "custom_field_values": [
        {
            "name": "Address Street",
            "value": "Vardovagen"
        },
        {
            "name": "Address City",
            "value": "Haninge"
        },
        {
            "name": "Address State",
            "value": "324"
        },
        {
            "name": "Zip Code",
            "value": "136 57"
        },
        {
            "name": "Flight Number 516",
            "value": "1589997",
            "display_value": "516"
        }
    ]
}

# Mock flight search response
mock_flight_search_response_517 = [
    {
        "FlightIdentifier": 1001,
        "FlightDate": "2025-10-28T10:00:00-04:00",
        "FlightNumber": "517",
        "Origin": "COX",
        "Destination": "FXE"
    },
    {
        "FlightIdentifier": 1002,
        "FlightDate": "2025-10-28T14:00:00-04:00",
        "FlightNumber": "518",
        "Origin": "COX",
        "Destination": "FXE"
    }
]

mock_flight_search_response_516 = [
    {
        "FlightIdentifier": 2001,
        "FlightDate": "2025-10-28T08:00:00-04:00",
        "FlightNumber": "516",
        "Origin": "FXE",
        "Destination": "COX"
    },
    {
        "FlightIdentifier": 2002,
        "FlightDate": "2025-10-28T12:00:00-04:00",
        "FlightNumber": "516",
        "Origin": "FXE",
        "Destination": "COX"
    }
]


def test_round_trip_detection():
    """Test round trip detection"""
    print("\n=== Test 1: Round Trip Detection ===")
    
    assert is_round_trip(return_booking_data) == True, "Should detect round trip"
    assert is_round_trip(depart_booking_data) == True, "Should detect round trip"
    
    order_id_return = get_order_display_id(return_booking_data)
    order_id_depart = get_order_display_id(depart_booking_data)
    
    assert order_id_return == "BUJP", f"Expected BUJP, got {order_id_return}"
    assert order_id_depart == "BUJP", f"Expected BUJP, got {order_id_depart}"
    assert order_id_return == order_id_depart, "Both bookings should have same order ID"
    
    print("SUCCESS: Round trip detection works correctly")


def test_flight_search_payload():
    """Test flight search payload building"""
    print("\n=== Test 2: Flight Search Payload ===")
    
    # Test return flight payload
    return_payload = build_flight_search_payload(return_booking_data)
    print(f"Return flight payload: {json.dumps(return_payload, indent=2)}")
    
    assert return_payload["DepartOrigin"] == "COX", "Origin should be COX"
    assert return_payload["DepartDestination"] == "FXE", "Destination should be FXE"
    assert return_payload["DepartDateStart"] == "2025-10-28", "Date should match"
    assert return_payload["AdultCount"] == 1, "Should have 1 adult"
    
    # Test depart flight payload
    depart_payload = build_flight_search_payload(depart_booking_data)
    print(f"Depart flight payload: {json.dumps(depart_payload, indent=2)}")
    
    assert depart_payload["DepartOrigin"] == "FXE", "Origin should be FXE"
    assert depart_payload["DepartDestination"] == "COX", "Destination should be COX"
    assert depart_payload["DepartDateStart"] == "2025-10-28", "Date should match"
    
    print("SUCCESS: Flight search payload building works correctly")


def test_flight_date_and_number_extraction():
    """Test flight date and number extraction"""
    print("\n=== Test 3: Flight Date and Number Extraction ===")
    
    # Test return flight
    return_date, return_number = extract_flight_date_and_number(return_booking_data)
    print(f"Return flight: Date={return_date}, Number={return_number}")
    assert return_date == "2025-10-28T10:00:00-0400", "Date should match"
    assert return_number == "517", "Flight number should be 517"
    
    # Test depart flight
    depart_date, depart_number = extract_flight_date_and_number(depart_booking_data)
    print(f"Depart flight: Date={depart_date}, Number={depart_number}")
    assert depart_date == "2025-10-28T08:00:00-0400", "Date should match"
    assert depart_number == "516", "Flight number should be 516"
    
    print("SUCCESS: Flight date and number extraction works correctly")


def test_flight_identifier_matching():
    """Test flight identifier matching from flight list"""
    print("\n=== Test 4: Flight Identifier Matching ===")
    
    # Test return flight matching
    return_date, return_number = extract_flight_date_and_number(return_booking_data)
    return_identifier = find_flight_identifier(
        mock_flight_search_response_517,
        return_date,
        return_number
    )
    print(f"Return flight identifier: {return_identifier}")
    assert return_identifier == 1001, f"Expected 1001, got {return_identifier}"
    
    # Test depart flight matching
    depart_date, depart_number = extract_flight_date_and_number(depart_booking_data)
    depart_identifier = find_flight_identifier(
        mock_flight_search_response_516,
        depart_date,
        depart_number
    )
    print(f"Depart flight identifier: {depart_identifier}")
    assert depart_identifier == 2001, f"Expected 2001, got {depart_identifier}"
    
    print("SUCCESS: Flight identifier matching works correctly")


def test_storage_operations():
    """Test storage operations for round trip bookings"""
    print("\n=== Test 5: Storage Operations ===")
    
    # Clear storage
    round_trip_bookings.clear()
    
    order_id = "BUJP"
    
    # Test storage
    assert not has_round_trip_booking(order_id), "Should not have booking initially"
    store_round_trip_booking(order_id, return_booking_data, [1001])
    assert has_round_trip_booking(order_id), "Should have booking after storage"
    
    # Test retrieval
    stored_booking = get_round_trip_booking(order_id)
    assert stored_booking is not None, "Should retrieve stored booking"
    assert stored_booking["booking_data"]["pk"] == 914502, "Booking data should match"
    assert stored_booking["flights"] == [1001], "Flights should match"
    
    # Test removal
    remove_round_trip_booking(order_id)
    assert not has_round_trip_booking(order_id), "Should not have booking after removal"
    
    print("SUCCESS: Storage operations work correctly")


def test_flight_direction_determination():
    """Test flight direction determination"""
    print("\n=== Test 6: Flight Direction Determination ===")
    
    # Simulate stored return flight and new depart flight
    existing_flights = [1001]  # Return flight identifier
    current_flights = [2001]   # Depart flight identifier
    
    depart_flights, return_flights = determine_flight_directions(
        existing_flights,
        current_flights,
        return_booking_data,
        depart_booking_data
    )
    
    print(f"Depart flights: {depart_flights}")
    print(f"Return flights: {return_flights}")
    
    assert depart_flights == [2001], "Depart flights should be from second request"
    assert return_flights == [1001], "Return flights should be from first request"
    
    print("SUCCESS: Flight direction determination works correctly")


def test_final_transformation():
    """Test final transformation with combined flights"""
    print("\n=== Test 7: Final Transformation ===")
    
    # Transform with combined flights
    result = transform_booking_data(
        return_booking_data,
        depart_flights=[2001],
        return_flights=[1001]
    )
    
    print(f"Transformed data: {json.dumps(result, indent=2)}")
    
    # Verify structure
    assert "DepartFlights" in result, "Should have DepartFlights"
    assert "ReturnFlights" in result, "Should have ReturnFlights"
    assert "Passengers" in result, "Should have Passengers"
    
    # Verify flights
    assert result["DepartFlights"] == [2001], "Depart flights should match"
    assert result["ReturnFlights"] == [1001], "Return flights should match"
    
    # Verify passenger data
    assert len(result["Passengers"]) == 1, "Should have 1 passenger"
    passenger = result["Passengers"][0]
    assert passenger["FirstName"] == "Eric", "First name should match"
    assert passenger["LastName"] == "Mollergren", "Last name should match"
    assert passenger["DateOfBirth"] == "2000-11-11", "Date of birth should match"
    assert passenger["Gender"] == "M", "Gender should be M"
    assert passenger["DocumentCountry"] == "USA", "Country should be USA"
    
    print("SUCCESS: Final transformation works correctly")


async def test_complete_round_trip_flow():
    """Test complete round trip flow with mocked API calls"""
    print("\n=== Test 8: Complete Round Trip Flow ===")
    
    from app.integrations import _process_round_trip_booking
    from app.api_client import search_flights, send_to_makersuite_api
    
    # Clear storage
    round_trip_bookings.clear()
    
    # Mock the API calls
    async def mock_search_flights(payload):
        if payload["DepartOrigin"] == "COX":
            return {"success": True, "response": mock_flight_search_response_517}
        else:
            return {"success": True, "response": mock_flight_search_response_516}
    
    async def mock_send_to_makersuite_api(data):
        return {
            "success": True,
            "response": {"bookingId": "12345", "status": "confirmed"}
        }
    
    # Patch the API functions
    with patch('app.api_client.search_flights', side_effect=mock_search_flights), \
         patch('app.api_client.send_to_makersuite_api', side_effect=mock_send_to_makersuite_api):
        
        # First request (return flight)
        print("\n--- Processing First Request (Return Flight) ---")
        result1 = await _process_round_trip_booking(return_booking_data)
        print(f"First request result: {json.dumps(result1, indent=2)}")
        
        assert "stored" in result1["message"].lower() or "waiting" in result1["message"].lower(), \
            "First request should be stored"
        assert has_round_trip_booking("BUJP"), "Booking should be stored"
        
        # Second request (depart flight)
        print("\n--- Processing Second Request (Depart Flight) ---")
        result2 = await _process_round_trip_booking(depart_booking_data)
        print(f"Second request result: {json.dumps(result2, indent=2)}")
        
        assert "successfully" in result2["message"].lower(), "Second request should succeed"
        assert not has_round_trip_booking("BUJP"), "Booking should be removed after processing"
        assert "makersuite_response" in result2, "Should have API response"
    
    print("SUCCESS: Complete round trip flow works correctly")


def main():
    """Run all tests"""
    print("=" * 80)
    print("ROUND TRIP BOOKING INTEGRATION TESTS")
    print("=" * 80)
    
    try:
        # Run synchronous tests
        test_round_trip_detection()
        test_flight_search_payload()
        test_flight_date_and_number_extraction()
        test_flight_identifier_matching()
        test_storage_operations()
        test_flight_direction_determination()
        test_final_transformation()
        
        # Run async test
        print("\n" + "=" * 80)
        asyncio.run(test_complete_round_trip_flow())
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

