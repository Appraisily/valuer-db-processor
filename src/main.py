from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import json
import time
from typing import Dict, Any, List, Optional

# Import our application components
from src.services.parser import parse_json_data, validate_json_structure
from src.services.image_service import process_images
from src.services.db_service import store_auction_data
from src.models.auction_lot import AuctionLotInput, AuctionLotResponse
from src.utils.logging import setup_logging
from src.utils.errors import configure_exception_handlers, AppException
from src.config import get_settings, configure_from_environment

# Setup logging
logger = setup_logging()
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="Valuer DB Processor",
    description="Service for processing auction data JSON files, extracting images, and storing data",
    version=settings.app_version,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure exception handlers
configure_exception_handlers(app)

class ProcessRequest(BaseModel):
    """Request model for processing JSON data"""
    data: Dict[str, Any]

class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    timestamp: float

@app.on_event("startup")
async def startup_event():
    """Execute startup tasks"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    configure_from_environment()
    
    # Log configuration information
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")
    logger.info(f"GCS bucket: {settings.gcs_bucket}")
    logger.info(f"Image processing: batch_size={settings.batch_size}, optimize={settings.optimize_images}")
    
    # Initialize database if using SQLite
    if settings.db_type == 'sqlite':
        from src.services.db_service import init_db
        await init_db()
        logger.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Execute shutdown tasks"""
    logger.info(f"Shutting down {settings.app_name}")
    # Any cleanup operations can be added here

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify service is running"""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=time.time()
    )

@app.post("/process", response_model=List[AuctionLotResponse])
async def process_data(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Process JSON data containing auction lots.
    
    Extracts information, downloads and uploads images to GCS,
    and stores data in the database.
    """
    try:
        logger.info("Received request to process data")
        
        # Validate the JSON structure
        if not validate_json_structure(request.data):
            raise AppException("Invalid JSON structure", status_code=400)
        
        # Parse the JSON data into our structured format
        auction_lots = parse_json_data(request.data)
        logger.info(f"Parsed {len(auction_lots)} auction lots from input data")
        
        if not auction_lots:
            logger.warning("No auction lots found in the data")
            return []
        
        # Process images in the background to allow for faster response
        background_tasks.add_task(process_images, auction_lots)
        
        # Store the auction data in the database
        stored_lots = await store_auction_data(auction_lots)
        
        logger.info(f"Successfully processed {len(stored_lots)} auction lots")
        return stored_lots
        
    except AppException as e:
        # This will be caught by the app exception handler
        raise
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}", exc_info=True)
        raise AppException(f"Error processing data: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """
    Returns service metrics.
    
    In a production system, this would integrate with
    Prometheus or Cloud Monitoring.
    """
    # Placeholder for metrics implementation
    metrics = {
        "total_processed": 0,
        "success_rate": 0.0,
        "average_processing_time_ms": 0,
        "image_upload_success_rate": 0.0,
    }
    return JSONResponse(content=metrics)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=settings.debug) 