import requests
import json
import sys
import os

# Print Python path for debugging
print("Python executable:", sys.executable)
print("Current directory:", os.getcwd())

# Create a very simple test request
sample_data = {
    "results": [
        {
            "hits": [
                {
                    "lotNumber": "102",
                    "lotRef": "27B4D1B966",
                    "priceResult": 850,
                    "photoPath": "soulis/58/778358/H1081-L382842666.jpg",
                    "dateTimeLocal": "2024-09-21 11:00:00",
                    "dateTimeUTCUnix": 1726934400,
                    "currencyCode": "USD",
                    "currencySymbol": "$",
                    "houseName": "Dirk Soulis Auctions",
                    "saleType": "Live",
                    "lotTitle": "AN UNUSUALLY SMALL LAGUNA OR ACOMA POTTERY CANTEEN"
                }
            ]
        }
    ]
}

# Try to ping the server first
try:
    health_check = requests.get("http://localhost:8000/health", timeout=5)
    print(f"Health check status: {health_check.status_code}")
    print("Health response:", health_check.json())
except Exception as e:
    print(f"Health check error: {str(e)}")
    sys.exit(1)

# Then try the process endpoint
try:
    print("\nSending request to process endpoint...")
    response = requests.post(
        "http://localhost:8000/process", 
        json={"data": sample_data},
        timeout=10
    )
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("Success! Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("Error response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {str(e)}")