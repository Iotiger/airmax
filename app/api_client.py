"""
API client for communicating with MakerSuite API
"""

import json
import httpx
from typing import Dict, Any, List, Optional
from app.config import (
    MAKERSUITE_API_URL, 
    MAKERSUITE_API_KEY,
    AIRMAX_API_BASE_URL,
    AIRMAX_FLIGHT_SEARCH_ENDPOINT
)
from app.logger import log_api_request, log_error, log_info


async def send_to_makersuite_api(transformed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send transformed booking data to MakerSuite API
    """
    headers = {
        "Content-Type": "application/json",
        "ApiKey": MAKERSUITE_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        log_info("Sending request to MakerSuite API", {"url": MAKERSUITE_API_URL, "payload": transformed_data})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MAKERSUITE_API_URL,
                json=transformed_data,
                headers=headers,
                timeout=30.0
            )
            
            log_info(f"MakerSuite API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                log_api_request("MakerSuite", MAKERSUITE_API_URL, transformed_data, response_data)
                return {"success": True, "response": response_data}
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                log_api_request("MakerSuite", MAKERSUITE_API_URL, transformed_data, None, error_msg)
                return {"success": False, "error": error_msg}
                
    except httpx.TimeoutException as e:
        error_msg = "Request timeout"
        log_error("MakerSuite API request timeout", str(e), {"url": MAKERSUITE_API_URL})
        return {"success": False, "error": error_msg}
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        log_error("MakerSuite API request error", str(e), {"url": MAKERSUITE_API_URL})
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        log_error("MakerSuite API unexpected error", str(e), {"url": MAKERSUITE_API_URL})
        return {"success": False, "error": error_msg}


async def search_flights(search_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for flights using Airmax Flight Search API
    """
    headers = {
        "Content-Type": "application/json",
        "ApiKey": MAKERSUITE_API_KEY,
        "Accept": "application/json"
    }
    
    url = f"{AIRMAX_API_BASE_URL}{AIRMAX_FLIGHT_SEARCH_ENDPOINT}"
    
    try:
        log_info("Sending flight search request", {"url": url, "payload": search_payload})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=search_payload,
                headers=headers,
                timeout=30.0
            )
            
            log_info(f"Flight Search API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                log_api_request("Airmax Flight Search", url, search_payload, response_data)
                return {"success": True, "response": response_data}
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                log_api_request("Airmax Flight Search", url, search_payload, None, error_msg)
                return {"success": False, "error": error_msg}
                
    except httpx.TimeoutException as e:
        error_msg = "Request timeout"
        log_error("Flight Search API request timeout", str(e), {"url": url})
        return {"success": False, "error": error_msg}
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        log_error("Flight Search API request error", str(e), {"url": url})
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        log_error("Flight Search API unexpected error", str(e), {"url": url})
        return {"success": False, "error": error_msg}

