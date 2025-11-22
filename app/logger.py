"""
JSON file logging utility
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Default log file path
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "webhook_logs.json"
WEBHOOK_DATA_FILE = LOG_DIR / "webhook_requests.json"


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
        log_entry["context"] = context
    
    if error:
        log_entry["error"] = error
    
    # Print full log entry to console
    print(f"\n[{timestamp}] [{level}] {message}")
    if context:
        print(f"Context: {json.dumps(context, indent=2, ensure_ascii=False)}")
    if error:
        print(f"Error: {error}")
    
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
    """Log debug message"""
    log_to_json("DEBUG", message, context)


def log_webhook_request(request_data: Dict[str, Any], client_ip: Optional[str] = None, url: Optional[str] = None):
    """Log webhook request"""
    context = {
        "client_ip": client_ip,
        "url": str(url) if url else None,
        "request_data": request_data
    }
    log_info("Webhook request received", context)


def log_api_request(api_name: str, url: str, payload: Dict[str, Any], response: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """Log API request/response"""
    context = {
        "api_name": api_name,
        "url": url,
        "payload": payload,
        "response": response
    }
    
    if error:
        log_error(f"API request failed: {api_name}", error, context)
    else:
        log_info(f"API request successful: {api_name}", context)


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
    
    # Print webhook entry to console
    print(f"\n[WEBHOOK REQUEST BODY] [{timestamp}]")
    print(f"Client IP: {client_ip}")
    print(f"URL: {url}")
    print(f"Webhook Data: {json.dumps(webhook_data, indent=2, ensure_ascii=False)}")
    
    # Append to JSON file (one JSON object per line - JSONL format)
    try:
        with open(WEBHOOK_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(webhook_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Fallback to print if file write fails
        print(f"ERROR: Failed to save webhook request body: {e}")
        print(f"Webhook entry: {webhook_entry}")

