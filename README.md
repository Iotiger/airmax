# FareHarbor to Airmax/MakerSuite Booking Integration

A FastAPI project that receives booking webhook data from FareHarbor, resolves flight identifiers via the Airmax Flight Search API, transforms the data, and forwards it to the MakerSuite API for flight bookings. Supports both single trip and round trip bookings.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

The API will be available at:
- Local HTTP: `http://localhost:8000`
- Local HTTPS: `https://localhost:8000`
- External HTTP: `http://95.217.102.140:8000`
- External HTTPS: `https://95.217.102.140:8000` (your current IP)

## External Access

To access from other computers on the network:

1. **Find your IP address**: Run `ipconfig` in Command Prompt
2. **Access via IP**: Use `http://YOUR_IP:8000` instead of localhost
3. **Windows Firewall**: You may need to allow Python through Windows Firewall
4. **Test connection**: Run `python test_connection.py` to verify accessibility

## Project Structure

```
├── app/
│   ├── __init__.py          # App package
│   ├── models.py            # Pydantic models
│   ├── integrations.py      # Main webhook handler and integration routes
│   ├── api_client.py        # API clients for MakerSuite and Airmax APIs
│   ├── config.py            # Configuration constants
│   ├── transform.py         # Booking data transformation functions
│   ├── helpers.py           # Helper functions for flight resolution and data processing
│   └── storage.py           # In-memory storage for round trip bookings
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── test_connection.py       # Connection tester
└── test_round_trip_integration.py  # Round trip booking integration tests
```

## Endpoints

- `GET /` - API root with endpoint information
- `POST /integrations/fareharbor/webhooks/bookings` - Receives FareHarbor booking webhooks and forwards to MakerSuite API

## Booking Processing Flow

The webhook endpoint handles both single trip and round trip bookings:

### Single Trip Bookings

1. **Receives** FareHarbor booking data
2. **Searches** for flights via Airmax Flight Search API using origin, destination, and date
3. **Resolves** flight identifier by matching flight date and flight number
4. **Transforms** the data to MakerSuite API format
5. **Forwards** the transformed data to MakerSuite API
6. **Returns** success/failure status

### Round Trip Bookings

Round trip bookings require two separate webhook requests (one for depart, one for return):

1. **First Request**: Receives first booking (return flight), stores it temporarily
2. **Second Request**: Receives second booking (depart flight)
   - Retrieves stored first booking
   - Resolves flight identifiers for both flights via Airmax API
   - Determines which is depart and which is return
   - Combines both flights into a single booking
   - Transforms and sends to MakerSuite API
   - Cleans up stored booking

**Note**: Round trip bookings are automatically cleaned up after 1 hour if not completed.

### Flight Identifier Resolution

The system uses the Airmax Flight Search API to resolve flight identifiers:

1. **Extracts** origin and destination airport codes from booking item name (e.g., "FXE", "COX")
2. **Extracts** flight date from `availability.start_at`
3. **Extracts** flight number from custom field values (e.g., "Flight Number 516")
4. **Searches** flights via Airmax API with origin, destination, and date
5. **Matches** flight by date and flight number to get the correct `FlightIdentifier`
6. **Falls back** to legacy method (availability item pk) if API search fails

### Data Transformation Flow

**Input (FareHarbor):**
```json
{
  "booking": {
    "order": {"display_id": "BUJP"},  // Present for round trip bookings
    "availability": {
      "item": {
        "pk": 80038,
        "name": "Fort Lauderdale Executive (FXE) → South Andros (COX)"
      },
      "start_at": "2025-10-28T08:00:00-0400"
    },
    "customers": [{
      "custom_field_values": [
        {"name": "First Name", "display_value": "John"},
        {"name": "Last Name", "display_value": "Doe"},
        {"name": "Date of Birth", "display_value": "01/15/1990"},
        {"name": "Gender", "display_value": "Male"},
        {"name": "Passport Number", "display_value": "123456789"},
        {"name": "Passport Expiration Date", "display_value": "01/15/2030"},
        {"name": "Citizenship", "display_value": "United States"},
        {"name": "Passenger Weight", "display_value": "165"}
      ]
    }],
    "contact": {"email": "john.doe@example.com", "phone": "5551234567"},
    "custom_field_values": [
      {"name": "Address Street", "value": "123 Main St"},
      {"name": "Address City", "value": "Miami"},
      {"name": "Address State", "value": "FL"},
      {"name": "Zip Code", "value": "33101"},
      {"name": "Flight Number 516", "value": "1589997", "display_value": "516"}
    ]
  }
}
```

**Output (MakerSuite):**
```json
{
  "DepartFlights": [2001],  // Resolved flight identifier from Airmax API
  "ReturnFlights": [1001],  // For round trips, resolved from second booking
  "Passengers": [{
    "FirstName": "John",
    "LastName": "Doe",
    "DateOfBirth": "1990-01-15",
    "Gender": "M",
    "Email": "john.doe@example.com",
    "Phone": "5551234567",
    "DocumentNumber": "123456789",
    "DocumentExpiry": "2030-01-15",
    "DocumentType": "P",
    "DocumentCountry": "USA",
    "Weight": 165,
    "BahamasStay": "BSStay",
    "AddressStreet": "123 Main St",
    "AddressCity": "Miami",
    "AddressState": "FL",
    "AddressZIPCode": "33101"
  }],
  "IsDepartFirstClass": false,
  "IsReturnFirstClass": false
}
```

## Key Features

### Round Trip Booking Support
- Automatically detects round trip bookings by checking for `order.display_id`
- Stores first booking temporarily until second booking arrives
- Combines both flights (depart and return) into a single MakerSuite booking
- Automatic cleanup of incomplete bookings after 1 hour

### Flight Identifier Resolution
- Uses Airmax Flight Search API to find correct flight identifiers
- Matches flights by date and flight number for accuracy
- Falls back to legacy method if API search fails
- Handles timezone conversions and date parsing

### Data Transformation
- Converts date formats (MM/DD/YYYY → YYYY-MM-DD)
- Maps gender display values to codes (Male → M, Female → F)
- Converts country names to ISO3 codes (United States → USA)
- Extracts passenger information from nested custom fields
- Maps booking-level address fields to passenger data

## HTTPS Setup

The server automatically detects SSL certificates and runs with HTTPS if available:

1. **Generate SSL certificates:**
   ```bash
   python generate_ssl.py
   ```

2. **Start server with HTTPS:**
   ```bash
   python main.py
   ```

3. **Test HTTPS endpoints:**
   ```bash
   python test_connection.py
   ```

## Testing

### Test Round Trip Integration
Comprehensive test suite for round trip booking functionality:
```bash
python test_round_trip_integration.py
```

This test suite covers:
- Round trip detection
- Flight search payload building
- Flight date and number extraction
- Flight identifier matching
- Storage operations
- Flight direction determination
- Complete round trip flow with mocked API calls

### Test API Connection
Test server connectivity and endpoints:
```bash
python test_connection.py
```

## Configuration

Configuration is managed in `app/config.py`:

### MakerSuite API Settings
- **API URL**: `https://testapi.makerssuite.com/api/Book/CreateBooking`
- **API Key**: `AD3236C8-E7E8-4D81-A73A-E389F4ADE35B`
- **Headers**: `ApiKey` for authentication

### Airmax Flight Search API Settings
- **Base URL**: `https://testapi.makerssuite.com`
- **Endpoint**: `/api/FlightSearch/GetOneWayFlightsForDateRange`
- **Authentication**: Uses same API key as MakerSuite API

### Round Trip Booking Settings
- **Cleanup Hours**: 1 hour (bookings older than this are automatically removed)

### Field Mapping

| FareHarbor Field | MakerSuite Field | Transformation |
|------------------|------------------|----------------|
| `availability.item.name` | Flight search (origin/destination) | Extracts airport codes |
| `availability.start_at` | Flight search (date) | Extracts and formats date |
| `custom_field_values["Flight Number X"]` | Flight search (flight number) | Extracts flight number |
| Flight search result | `DepartFlights[]` / `ReturnFlights[]` | Matches by date and number |
| `customers[].custom_field_values` | `Passengers[]` | Complex mapping |
| `contact.email` | `Passengers[].Email` | Direct mapping |
| `contact.phone` | `Passengers[].Phone` | Direct mapping |
| Date formats | Date formats | MM/DD/YYYY → YYYY-MM-DD |
| Gender display | Gender code | "Male" → "M", "Female" → "F" |
| Country names | ISO3 codes | "United States" → "USA" |
| `custom_field_values["Address *"]` | `Passengers[].Address*` | Booking-level to passenger mapping |

## Usage

### Single Trip Booking

Send a POST request to `/integrations/fareharbor/webhooks/bookings` with FareHarbor booking data. The system will:

1. **Log** the incoming webhook data
2. **Search** for flights via Airmax API
3. **Resolve** flight identifier
4. **Transform** the data to MakerSuite format
5. **Send** to MakerSuite API
6. **Return** success/failure status

### Round Trip Booking

For round trip bookings, send two separate POST requests:

1. **First Request**: Send the first booking (typically return flight)
   - Response: `"Round trip booking received and stored for order {order_id}. Waiting for second booking."`
   
2. **Second Request**: Send the second booking (typically depart flight) with the same `order.display_id`
   - Response: `"Round trip booking processed and sent to MakerSuite successfully!"`

**Note**: Both bookings must have the same `order.display_id` to be combined.

**Endpoint URLs:**
- Local: `http://localhost:8000/integrations/fareharbor/webhooks/bookings`
- External: `http://95.217.102.140:8000/integrations/fareharbor/webhooks/bookings`
- HTTPS: `https://95.217.102.140:8000/integrations/fareharbor/webhooks/bookings` (if SSL configured)

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative docs (ReDoc): `http://localhost:8000/redoc`

## Dependencies

Key dependencies (see `requirements.txt` for full list):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client for API calls
- `pydantic` - Data validation
- `country-converter` - Country name to ISO3 code conversion

## Architecture

The application follows a modular architecture:

- **`main.py`**: FastAPI application setup and routing
- **`app/integrations.py`**: Main webhook handler with single/round trip logic
- **`app/api_client.py`**: API clients for MakerSuite and Airmax APIs
- **`app/transform.py`**: Data transformation from FareHarbor to MakerSuite format
- **`app/helpers.py`**: Flight resolution, direction determination, and utility functions
- **`app/storage.py`**: In-memory storage for round trip bookings
- **`app/config.py`**: Centralized configuration constants
