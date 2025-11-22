#!/usr/bin/env python3
"""
Simple script to test if the FastAPI server is accessible
"""
import requests
import json

def test_server(host="localhost", port=8000, use_https=False):
    """Test if the server is running and accessible"""
    protocol = "https" if use_https else "http"
    try:
        # Test the root endpoint
        response = requests.get(f"{protocol}://{host}:{port}/", verify=False)
        print(f"[OK] Server is accessible at {protocol}://{host}:{port}")
        print(f"Response: {response.json()}")
        
        # Test the webhook endpoint with sample data
        webhook_url = f"{protocol}://{host}:{port}/integrations/fareharbor/webhooks/bookings"
        sample_data = {
            "data": {
                "booking_id": "12345",
                "customer_name": "John Doe",
                "test": True
            }
        }
        
        response = requests.post(webhook_url, json=sample_data, verify=False)
        print(f"[OK] Webhook endpoint is working")
        print(f"Response: {response.json()}")
        
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to server at {protocol}://{host}:{port}")
        print("Make sure the server is running and accessible")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    print("Testing local HTTP connection...")
    test_server("localhost", 8000, use_https=False)
    
    print("\nTesting local HTTPS connection...")
    test_server("localhost", 8000, use_https=True)
    
    print("\nTesting external HTTP connection...")
    test_server("95.217.102.140", 8000, use_https=False)
    
    print("\nTesting external HTTPS connection...")
    test_server("95.217.102.140", 8000, use_https=True)
