"""
JSON file logging utility
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


def convert_datetime_to_iso(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {
            key: convert_datetime_to_iso(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [convert_datetime_to_iso(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_datetime_to_iso(item) for item in obj)
    else:
        return obj


# Default log file path
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "webhook_logs.json"
WEBHOOK_DATA_FILE = LOG_DIR / "webhook_requests.json"
AIRMAX_BOOKING_REQUESTS_FILE = LOG_DIR / "airmax_booking_requests.json"


def ensure_log_dir():
    """Ensure log directory exists"""
    LOG_DIR.mkdir(exist_ok=True)


def log_to_json(
    level: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """
    Write log entry to JSON file and print to console
    
    Args:
        level: Log level (INFO, ERROR, WARNING, DEBUG)
        message: Log message
        context: Additional context data (dict)
        error: Error message if applicable
    """
    ensure_log_dir()
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    
    if context:
        # Convert datetime objects to ISO strings for JSON serialization
        log_entry["context"] = convert_datetime_to_iso(context)
    
    if error:
        log_entry["error"] = error
    
    # Print minimal log entry to console (only for ERROR and WARNING)
    if level in ["ERROR", "WARNING"]:
        print(f"[{level}] {message}")
        if error:
            print(f"  Error: {error}")
    
    # Append to JSON file (one JSON object per line - JSONL format)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Fallback to print if file write fails
        print(f"ERROR: Failed to write log: {e}")
        print(f"Log entry: {log_entry}")


def log_info(message: str, context: Optional[Dict[str, Any]] = None):
    """Log info message"""
    log_to_json("INFO", message, context)


def log_error(message: str, error: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
    """Log error message"""
    log_to_json("ERROR", message, context, error)


def log_warning(message: str, context: Optional[Dict[str, Any]] = None):
    """Log warning message"""
    log_to_json("WARNING", message, context)


def log_debug(message: str, context: Optional[Dict[str, Any]] = None):
    """Log debug message (disabled to reduce log size)"""
    # Debug logging disabled to reduce log file size
    pass


def log_webhook_request(request_data: Dict[str, Any], client_ip: Optional[str] = None, url: Optional[str] = None):
    """Log webhook request (minimal logging)"""
    # Only log minimal info to reduce log size
    booking_pk = request_data.get("booking", {}).get("pk", None)
    log_info("Webhook received", {"client_ip": client_ip, "booking_pk": booking_pk})


def log_api_request(api_name: str, url: str, payload: Dict[str, Any], response: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """Log API request/response (minimal logging)"""
    if error:
        log_error(f"API request failed: {api_name}", error, {"url": url})
    else:
        # Only log success without full payload/response to reduce log size
        log_info(f"API request successful: {api_name}", {"url": url})


def save_webhook_request_body(webhook_data: Dict[str, Any], client_ip: Optional[str] = None, url: Optional[str] = None):
    """
    Save FareHarbor webhook request body to JSON file and print to console
    
    Args:
        webhook_data: The parsed webhook request body data
        client_ip: Client IP address (optional)
        url: Request URL (optional)
    """
    ensure_log_dir()
    
    timestamp = datetime.now().isoformat()
    # Create entry with metadata and webhook data
    webhook_entry = {
        "timestamp": timestamp,
        "client_ip": client_ip,
        "url": str(url) if url else None,
        "webhook_data": webhook_data
    }
    
    # Convert datetime objects to ISO strings for JSON serialization
    webhook_entry["webhook_data"] = convert_datetime_to_iso(webhook_data)
    
    # Print minimal webhook info to console (only summary)
    booking_pk = webhook_data.get("booking", {}).get("pk", "N/A")
    print(f"[WEBHOOK] {timestamp} | IP: {client_ip} | Booking PK: {booking_pk}")
    
    # Append to JSON file (one JSON object per line - JSONL format)
    try:
        with open(WEBHOOK_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(webhook_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Fallback to print if file write fails
        print(f"ERROR: Failed to save webhook request body: {e}")
        print(f"Webhook entry: {webhook_entry}")


def save_airmax_booking_request(booking_request_data: Dict[str, Any], url: Optional[str] = None):
    """
    Save Airmax API create booking request data to JSON file
    
    Args:
        booking_request_data: The booking request payload sent to Airmax API
        url: API URL (optional)
    """
    ensure_log_dir()
    
    timestamp = datetime.now().isoformat()
    # Create entry with request data
    request_entry = {
        "timestamp": timestamp,
        "url": str(url) if url else None,
        "request_data": booking_request_data
    }
    
    # Convert datetime objects to ISO strings for JSON serialization
    request_entry["request_data"] = convert_datetime_to_iso(booking_request_data)
    
    # Append to JSON file (one JSON object per line - JSONL format)
    try:
        with open(AIRMAX_BOOKING_REQUESTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(request_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Fallback to print if file write fails
        print(f"ERROR: Failed to save Airmax booking request: {e}")
        print(f"Request entry: {request_entry}")

