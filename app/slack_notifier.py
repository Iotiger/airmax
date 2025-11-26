"""
Slack notification module for booking status updates
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from app.config import SLACK_WEBHOOK_URL
from app.logger import log_info, log_error, log_warning


async def send_slack_notification(
    status: str,
    message: str,
    booking_data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    order_id: Optional[str] = None,
    booking_type: Optional[str] = None
) -> bool:
    """
    Send a Slack notification for booking status
    
    Args:
        status: "success", "warning", or "error"
        message: Main message to display
        booking_data: Optional booking data for context
        error: Optional error message
        order_id: Optional order ID for round trip bookings
        booking_type: Optional booking type ("single_trip" or "round_trip")
    
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    if not SLACK_WEBHOOK_URL:
        log_warning("Slack webhook URL not configured, skipping notification")
        return False
    
    # Determine color based on status
    color_map = {
        "success": "#36a64f",  # Green
        "warning": "#ff9800",  # Orange
        "error": "#ff0000"     # Red
    }
    color = color_map.get(status.lower(), "#808080")  # Default gray

    # Extract relevant booking information
    fields = []
    
    if order_id:
        fields.append({
            "title": "Order ID",
            "value": order_id,
            "short": True
        })
    
    if booking_type:
        fields.append({
            "title": "Booking Type",
            "value": booking_type.replace("_", " ").title(),
            "short": True
        })
    
    # Extract passenger info if available
    if booking_data:
        customers = booking_data.get("customers", [])
        if customers:
            first_customer = customers[0]
            custom_fields = {
                field.get("name", ""): field.get("display_value", "")
                for field in first_customer.get("custom_field_values", [])
            }

            first_name = custom_fields.get('First Name', '')
            last_name = custom_fields.get('Last Name', '')
            passenger_name = f"{first_name} {last_name}".strip()
            if passenger_name:
                fields.append({
                    "title": "Passenger",
                    "value": passenger_name,
                    "short": True
                })
        
        # Extract flight info
        availability = booking_data.get("availability", {})
        item = availability.get("item", {})
        item_name = item.get("name", "")
        if item_name:
            fields.append({
                "title": "Flight Route",
                "value": item_name,
                "short": False
            })
        
        start_at = availability.get("start_at", "")
        if start_at:
            try:
                # Parse and format date
                date_obj = datetime.fromisoformat(
                    start_at.replace('Z', '+00:00')
                )
                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                fields.append({
                    "title": "Flight Date",
                    "value": date_str,
                    "short": True
                })
            except Exception:
                pass
    
    if error:
        fields.append({
            "title": "Error Details",
            "value": error[:500],  # Limit error message length
            "short": False
        })
    
    # Build attachment
    attachment = {
        "color": color,
        "title": f"Airmax Booking {status.upper()}",
        "text": message,
        "fields": fields,
        "footer": "Airmax Webhook Service",
        "ts": int(datetime.now().timestamp())
    }
    
    payload = {
        "attachments": [attachment]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                log_info(
                    f"Slack notification sent successfully: {status}",
                    {"status": status, "message": message}
                )
                return True
            else:
                error_msg = (
                    f"Status {response.status_code}: {response.text}"
                )
                log_error("Failed to send Slack notification", error_msg)
                return False
                
    except httpx.TimeoutException as e:
        log_error("Slack notification timeout", str(e))
        return False
    except Exception as e:
        log_error("Failed to send Slack notification", str(e))
        return False


async def notify_booking_success(
    booking_data: Dict[str, Any],
    airmax_response: Dict[str, Any],
    order_id: Optional[str] = None,
    booking_type: str = "single_trip"
):
    """
    Send success notification for booking
    """
    message = "✅ Booking successfully sent to Airmax API"

    await send_slack_notification(
        status="success",
        message=message,
        booking_data=booking_data,
        order_id=order_id,
        booking_type=booking_type
    )


async def notify_booking_error(
    booking_data: Dict[str, Any],
    error: str,
    order_id: Optional[str] = None,
    booking_type: str = "single_trip"
):
    """
    Send error notification for booking failure
    """
    message = "❌ Failed to send booking to Airmax API"

    await send_slack_notification(
        status="error",
        message=message,
        booking_data=booking_data,
        error=error,
        order_id=order_id,
        booking_type=booking_type
    )


async def notify_booking_warning(
    message: str,
    booking_data: Optional[Dict[str, Any]] = None,
    order_id: Optional[str] = None,
    booking_type: Optional[str] = None
):
    """
    Send warning notification
    """
    await send_slack_notification(
        status="warning",
        message=f"⚠️ {message}",
        booking_data=booking_data,
        order_id=order_id,
        booking_type=booking_type
    )

