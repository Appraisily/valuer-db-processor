import requests

# Test the health endpoint
try:
    response = requests.get("http://localhost:8000/health")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("Success! Response:")
        print(response.json())
    else:
        print("Error response:")
        print(response.text)
except Exception as e:
    print(f"Error: {str(e)}")