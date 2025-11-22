"""
Storage management for round trip bookings
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import ROUND_TRIP_CLEANUP_HOURS
from app.logger import log_info

# In-memory storage for round trip bookings
# Key: order_display_id, Value: booking data
round_trip_bookings: Dict[str, Dict[str, Any]] = {}

# Locks for each order_id to prevent race conditions
_order_locks: Dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def get_order_lock(order_id: str) -> asyncio.Lock:
    """
    Get or create a lock for a specific order_id to ensure atomic operations
    """
    async with _locks_lock:
        if order_id not in _order_locks:
            _order_locks[order_id] = asyncio.Lock()
        return _order_locks[order_id]


async def cleanup_order_lock(order_id: str):
    """
    Clean up the lock for an order_id after processing is complete
    """
    async with _locks_lock:
        if order_id in _order_locks:
            del _order_locks[order_id]


def cleanup_old_bookings():
    """
    Clean up old round trip bookings (older than configured hours)
    """
    current_time = datetime.now()
    keys_to_remove = []
    
    for order_id, booking_info in round_trip_bookings.items():
        first_received_at_str = booking_info.get("first_received_at")
        if first_received_at_str:
            # Parse ISO string back to datetime for comparison
            if isinstance(first_received_at_str, str):
                first_received_at = datetime.fromisoformat(
                    first_received_at_str
                )
            else:
                # Backward compatibility: handle datetime objects
                first_received_at = first_received_at_str

            if (current_time - first_received_at >
                    timedelta(hours=ROUND_TRIP_CLEANUP_HOURS)):
                keys_to_remove.append(order_id)

    for key in keys_to_remove:
        del round_trip_bookings[key]
        log_info(
            f"Removed old round trip booking for order {key}",
            {"order_id": key}
        )


def store_round_trip_booking(
    order_id: str, booking_data: Dict[str, Any], flights: list
):
    """
    Store a round trip booking for later combination
    """
    round_trip_bookings[order_id] = {
        "booking_data": booking_data,
        "flights": flights,
        # Store as ISO string for JSON serialization
        "first_received_at": datetime.now().isoformat()
    }


def get_round_trip_booking(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a stored round trip booking by order ID
    """
    return round_trip_bookings.get(order_id)


def remove_round_trip_booking(order_id: str):
    """
    Remove a round trip booking from storage
    """
    if order_id in round_trip_bookings:
        del round_trip_bookings[order_id]


def has_round_trip_booking(order_id: str) -> bool:
    """
    Check if a round trip booking exists for the given order ID
    """
    return order_id in round_trip_bookings
