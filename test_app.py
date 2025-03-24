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
                    "photoPath": "soulis/58/778358/H1081-L382842666.jpg",  # Real image path
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
    
    # Start the server in a subprocess
    import subprocess
    import time
    
    base_url = "http://localhost:8000"
    
    print("Starting the server in the background...")
    server_process = None
    
    try:
        # Start the server
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give the server time to start
        print("Waiting for server to start...")
        time.sleep(3)
        print("Server should be running at http://localhost:8000")
        
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
        print("Local image will be used from: ./local_images/soulis/58/778358/H1081-L382842666.jpg")
    
    except httpx.HTTPError as e:
        print(f"HTTP Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
    
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Clean up the server process if it was started
        if server_process:
            print("Shutting down the server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("Server shut down")

if __name__ == "__main__":
    asyncio.run(test_app())