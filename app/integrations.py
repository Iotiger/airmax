"""
Main webhook handler for FareHarbor bookings
"""

from fastapi import APIRouter, Request
import json
from datetime import datetime
from typing import Dict, Any

from app.helpers import (
    is_round_trip,
    get_order_display_id,
    get_flight_identifiers_from_api,
    determine_flight_directions
)
from app.storage import (
    cleanup_old_bookings,
    store_round_trip_booking,
    get_round_trip_booking,
    remove_round_trip_booking,
    has_round_trip_booking,
    get_order_lock
)
from app.transform import transform_booking_data
from app.api_client import send_to_makersuite_api
from app.logger import (
    log_info, log_error, log_warning, log_webhook_request,
    save_webhook_request_body
)
from app.slack_notifier import (
    notify_booking_success, notify_booking_error, notify_booking_warning
)

router = APIRouter()


@router.post("/bookings")
async def receive_booking_webhook(request: Request):
    """
    Receive booking webhook data from FareHarbor and forward to MakerSuite API
    """
    # Get the raw request body
    body = await request.body()
    
    # Parse JSON
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError:
        webhook_data = {"raw_body": body.decode('utf-8')}
    
    # Save webhook request body to JSON file
    save_webhook_request_body(
        webhook_data=webhook_data,
        client_ip=request.client.host if request.client else None,
        url=request.url
    )
    
    # Log webhook request
    _log_webhook_request(request, webhook_data)
    
    # Process booking data if it contains booking information
    if "booking" in webhook_data:
        try:
            
            booking_data = webhook_data["booking"]
            
            # Check if affiliate_company name contains "Airmax" - ignore these bookings
            affiliate_company = booking_data.get("affiliate_company")
            if affiliate_company:
                affiliate_name = affiliate_company.get("name", "").strip()
                if affiliate_name and "AIRMAX" in affiliate_name:
                    booking_pk = booking_data.get("pk")
                    order_id = get_order_display_id(booking_data)
                    
                    log_info(f"Ignoring booking {booking_pk} - affiliate is Airmax (affiliate: {affiliate_name})")
                    
                    # Send Slack notification
                    await notify_booking_warning(
                        message=f"Booking ignored - affiliate is Airmax (affiliate: {affiliate_name})",
                        booking_data=booking_data,
                        order_id=order_id,
                        booking_type="round_trip" if is_round_trip(booking_data) else "single_trip"
                    )
                    
                    return {
                        "message": "Booking ignored - affiliate is Airmax",
                        "timestamp": datetime.now().isoformat(),
                        "ignored": True,
                        "affiliate_name": affiliate_name
                    }
            
            # Check if this is a round trip booking
            if is_round_trip(booking_data):
                return await _process_round_trip_booking(booking_data)
            else:
                return await _process_single_trip_booking(booking_data)
                
        except Exception as e:
            log_error("Error processing booking", str(e))
            return {
                "message": "Booking received but processing failed", 
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    else:
        log_warning("No booking data found in webhook")
        return {"message": "Webhook received but no booking data found", "timestamp": datetime.now().isoformat()}


async def _process_round_trip_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a round trip booking (requires 2 webhook requests)
    """
    order_id = get_order_display_id(booking_data)
    
    if not order_id:
        log_error("Round trip booking missing order_id")
        return {
            "message": "Error: Round trip booking missing order_id",
            "timestamp": datetime.now().isoformat(),
            "error": "Missing order_id"
        }
    
    log_info(f"Processing round trip booking: {order_id}")
    
    # Get lock for this order_id to prevent race conditions
    order_lock = await get_order_lock(order_id)
    
    async with order_lock:
        # Check if we already have a booking for this order BEFORE any cleanup
        # (cleanup should only happen when storing new bookings, not when checking)
        if has_round_trip_booking(order_id):
            
            # Get the existing booking data
            existing_booking_info = get_round_trip_booking(order_id)
            if not existing_booking_info:
                log_error(f"Booking for {order_id} not found in storage")
                return {
                    "message": (
                        f"Error: Booking for order {order_id} not found"
                    ),
                    "timestamp": datetime.now().isoformat(),
                    "error": "Booking storage error"
                }
            
            existing_booking = existing_booking_info["booking_data"]
            
            # Process round trip booking - ensure cleanup happens in all cases
            try:
                # Get flight identifiers from API for both bookings
                existing_flights = await get_flight_identifiers_from_api(
                    existing_booking
                )
                current_flights = await get_flight_identifiers_from_api(
                    booking_data
                )
                
                # Determine which is depart and which is return
                depart_flights, return_flights = determine_flight_directions(
                    existing_flights, current_flights,
                    existing_booking, booking_data
                )
                
                # Use the first booking's passenger data (they should be same)
                combined_booking_data = existing_booking
                
                # Transform the combined booking data
                transformed_data = transform_booking_data(
                    combined_booking_data, depart_flights, return_flights
                )
                # Release lock before API call (lock released when exiting async with)
                # Send to MakerSuite API
                api_result = await send_to_makersuite_api(transformed_data)
                
                if api_result["success"]:
                    log_info(f"Round trip booking sent successfully: {order_id}")
                    # Send Slack success notification
                    await notify_booking_success(
                        booking_data=combined_booking_data,
                        airmax_response=api_result.get("response"),
                        order_id=order_id,
                        booking_type="round_trip"
                    )
                    return {
                        "message": (
                            "Round trip booking processed and sent to "
                            "MakerSuite successfully!"
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "makersuite_response": api_result["response"]
                    }
                else:
                    log_error(f"Failed to send round trip booking: {order_id}", api_result.get("error"))
                    # Send Slack error notification
                    await notify_booking_error(
                        booking_data=combined_booking_data,
                        error=api_result.get("error"),
                        order_id=order_id,
                        booking_type="round_trip"
                    )
                    return {
                        "message": (
                            "Round trip booking received but failed to send "
                            "to MakerSuite"  
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "error": api_result["error"]
                    }
            finally:
                # Always clean up the stored booking after processing (while holding lock)
                remove_round_trip_booking(order_id)
        else:
            # Clean up old bookings before storing new one
            cleanup_old_bookings()
            
            log_info(f"First booking for {order_id}, storing for later")
            
            # Get flight identifiers from API for this booking
            flights = await get_flight_identifiers_from_api(booking_data)
            store_round_trip_booking(order_id, booking_data, flights)
            
            # Send Slack warning notification for first booking waiting
            await notify_booking_warning(
                message=(
                    "Round trip booking received and stored. "
                    "Waiting for second booking."
                ),
                booking_data=booking_data,
                order_id=order_id,
                booking_type="round_trip"
            )
            
            # Lock is automatically released when exiting async with block
            return {
                "message": (
                    f"Round trip booking received and stored for order "
                    f"{order_id}. Waiting for second booking."
                ),
                "timestamp": datetime.now().isoformat()
            }


async def _process_single_trip_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single trip booking (sent immediately)
    """
    # Create unique identifier for this booking to prevent duplicates
    from app.storage import (
        is_single_trip_processed,
        mark_single_trip_processed
    )

    booking_pk = booking_data.get("pk")
    availability = booking_data.get("availability", {})
    start_at = availability.get("start_at", "")
    item_pk = availability.get("item", {}).get("pk")

    # Create unique booking identifier
    booking_id = None
    if booking_pk:
        booking_id = f"single_{booking_pk}_{start_at}"
    elif item_pk and start_at:
        booking_id = f"single_item_{item_pk}_{start_at}"

    # Check if already processed (idempotency check)
    if booking_id and is_single_trip_processed(booking_id):
        log_warning(f"Single trip booking {booking_id} already processed, skipping")
        return {
            "message": "Booking already processed (duplicate request)",
            "timestamp": datetime.now().isoformat(),
            "duplicate": True
        }
    
    
    # Get flight identifiers from API
    depart_flights = await get_flight_identifiers_from_api(booking_data)
    
    # Transform the booking data
    transformed_data = transform_booking_data(booking_data, depart_flights=depart_flights)
    # Send to MakerSuite API
    api_result = await send_to_makersuite_api(transformed_data)
    
    if api_result["success"]:
        # Mark as processed to prevent duplicates
        if booking_id:
            mark_single_trip_processed(booking_id)
        
        log_info("Single trip booking sent successfully")
        # Send Slack success notification
        await notify_booking_success(
            booking_data=booking_data,
            airmax_response=api_result.get("response"),
            booking_type="single_trip"
        )
        return {
            "message": "Single trip booking processed and sent to MakerSuite successfully!", 
            "timestamp": datetime.now().isoformat(),
            "makersuite_response": api_result["response"]
        }
    else:
        log_error("Failed to send single trip booking", api_result.get("error"))
        # Send Slack error notification
        await notify_booking_error(
            booking_data=booking_data,
            error=api_result.get("error"),
            booking_type="single_trip"
        )
        return {
            "message": "Single trip booking received but failed to send to MakerSuite", 
            "timestamp": datetime.now().isoformat(),
            "error": api_result["error"]
        }


def _log_webhook_request(request: Request, webhook_data: Dict[str, Any]):
    """Log webhook request details"""
    # Log to JSON file (minimal logging)
    log_webhook_request(
        request_data=webhook_data,
        client_ip=request.client.host if request.client else None,
        url=request.url
    )
