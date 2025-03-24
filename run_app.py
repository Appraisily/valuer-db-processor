import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Run the FastAPI application
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True) 