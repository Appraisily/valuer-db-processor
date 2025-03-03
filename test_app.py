import asyncio
import json
import sys
import os
from pprint import pprint

# Ensure src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import httpx
from src.config import get_settings

# Get settings
settings = get_settings()

# Sample data from example_json.json
# This will be used to test the API
SAMPLE_DATA = {
    "results": [
        {
            "hits": [
                {
                    "lotNumber": "123-TEST",
                    "lotRef": "TEST12345",
                    "priceResult": 1000.0,
                    "photoPath": "test:test_image.jpg",
                    "dateTimeLocal": "2024-03-01 00:00:00",
                    "dateTimeUTCUnix": 1709292000,
                    "currencyCode": "USD",
                    "currencySymbol": "$",
                    "houseName": "Test Auction House",
                    "saleType": "Online",
                    "lotTitle": "Test Item",
                    "objectID": "12345",
                    "_highlightResult": {
                        "moreText": {
                            "value": "Test description text",
                            "matchLevel": "partial",
                            "fullyHighlighted": False,
                            "matchedWords": ["test"]
                        },
                        "lotTitle": {
                            "value": "Test Item",
                            "matchLevel": "full",
                            "fullyHighlighted": True,
                            "matchedWords": ["test"]
                        }
                    },
                    "_rankingInfo": {
                        "nbTypos": 0,
                        "firstMatchedWord": 0,
                        "proximityDistance": 1,
                        "userScore": 100,
                        "geoDistance": 0,
                        "geoPrecision": 1,
                        "nbExactWords": 1,
                        "words": 1,
                        "filters": 1
                    }
                }
            ]
        }
    ]
}

async def test_app():
    """
    Test the application by making requests to its API endpoints
    """
    print("\n===== Testing Valuer DB Processor =====\n")
    
    # Start the test server in a separate process
    print("Please start the server in a separate terminal with:")
    print("  uvicorn src.main:app --reload")
    print("\n")
    
    base_url = "http://localhost:8000"
    
    # Wait for user to confirm the server is running
    input("Press Enter once the server is running...\n")
    
    try:
        # Test the health endpoint
        print(f"Testing health endpoint...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            health_data = response.json()
            print(f"Health Response: {health_data}")
            print("✓ Health endpoint is working\n")
        
        # Test the process endpoint
        print(f"Testing process endpoint...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/process",
                json={"data": SAMPLE_DATA}
            )
            response.raise_for_status()
            process_data = response.json()
            print("Process Response:")
            pprint(process_data)
            print("\n✓ Process endpoint is working\n")
            
        print("All tests passed!")
    
    except httpx.HTTPError as e:
        print(f"HTTP Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_app()) 