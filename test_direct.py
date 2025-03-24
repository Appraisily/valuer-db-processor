import os
import shutil
from fastapi.testclient import TestClient
from src.main import app
from src.models.db_models import Base
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import get_settings

# Get settings
settings = get_settings()

# Check if database exists and remove it
db_path = settings.db_name
if os.path.exists(db_path):
    print(f"Removing existing database: {db_path}")
    os.remove(db_path)

# Make sure directory exists
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir):
    print(f"Creating directory: {db_dir}")
    os.makedirs(db_dir)

# Initialize the database asynchronously
async def init_db():
    """Initialize database with the updated schema"""
    print("Initializing database...")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine

# Run the initialization
import asyncio
asyncio.run(init_db())

# Create a test client
client = TestClient(app)

def test_health_endpoint():
    """Test the health endpoint"""
    response = client.get("/health")
    print(f"Health check status code: {response.status_code}")
    print(f"Health response: {response.json()}")
    return response.status_code == 200

def test_process_endpoint():
    """Test the process endpoint with a simple test item"""
    # Create a sample request payload
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
    
    # Send the request
    print("\nTesting process endpoint...")
    response = client.post("/process", json={"data": sample_data})
    
    # Print results
    print(f"Process status code: {response.status_code}")
    if response.status_code == 200:
        print("Success! Processed items:")
        print(response.json())
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing the API directly without starting a server...")
    
    health_ok = test_health_endpoint()
    if health_ok:
        print("✓ Health endpoint is working\n")
    else:
        print("✗ Health endpoint failed\n")
    
    process_ok = test_process_endpoint()
    if process_ok:
        print("✓ Process endpoint is working\n")
    else:
        print("✗ Process endpoint failed\n")
        
    if health_ok and process_ok:
        print("All tests passed!")
    else:
        print("Some tests failed.")