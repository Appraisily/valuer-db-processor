import logging
import sys
import os
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_image_download(settings, auction_lots):
    """Test downloading a few images"""
    from src.services.image_service import download_image
    
    logger.info("Testing image download for a few lots")
    for i, lot in enumerate(auction_lots[:3]):
        try:
            # Download the image
            image_data = await download_image(lot.photoPath)
            
            if image_data:
                # Save the image to a local file
                local_path = os.path.join(settings.local_storage_path, f"test_image_{i}.jpg")
                with open(local_path, "wb") as f:
                    f.write(image_data)
                logger.info(f"Image download for lot {i} successful, saved to {local_path}")
            else:
                logger.error(f"Image download for lot {i} failed")
        except Exception as e:
            logger.error(f"Error downloading image for lot {i}: {str(e)}")

async def async_main():
    logger.info("Starting debug script")
    
    # Load environment variables
    load_dotenv()
    logger.info("Loaded environment variables")
    
    try:
        # Import application components
        logger.info("Importing application components")
        from src.config import get_settings, configure_from_environment
        
        # Load settings
        settings = get_settings()
        configure_from_environment()
        
        logger.info(f"Settings loaded: ENV={settings.env}, DB_TYPE={settings.db_type}")
        
        # Try importing the data models
        from src.models.auction_lot import AuctionLotInput, AuctionLotResponse
        from src.models.db_models import AuctionLot, Base
        
        logger.info("Data models imported successfully")
        
        # Try initializing the database
        from src.services.db_service import init_db
        
        logger.info("Starting database initialization")
        await init_db()
        logger.info("Database initialized successfully")
        
        # Try parsing the example JSON file
        from src.services.parser import validate_json_structure, parse_json_data
        
        logger.info("Loading example JSON file")
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            json_data = None
            
            for encoding in encodings:
                try:
                    with open("example_json.json", "r", encoding=encoding) as f:
                        json_data = f.read()
                    logger.info(f"Successfully read file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    logger.warning(f"Failed to read with encoding: {encoding}")
                    continue
            
            if json_data is None:
                raise ValueError("Could not read the JSON file with any of the attempted encodings")
                
            import json
            data = json.loads(json_data)
            
            is_valid = validate_json_structure(data)
            logger.info(f"JSON structure is valid: {is_valid}")
            
            if is_valid:
                auction_lots = parse_json_data(data)
                logger.info(f"Parsed {len(auction_lots)} auction lots")
                
                # Test image download
                await test_image_download(settings, auction_lots)
                
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}", exc_info=True)
        
        logger.info("Debug script completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1
    
    return 0

def main():
    return asyncio.run(async_main())

if __name__ == "__main__":
    sys.exit(main()) 