#!/usr/bin/env python3
"""
Auction Data Processor

This script processes auction data from the example JSON file, downloads images,
and stores data in a SQLite database.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Any

# Add the current directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.auction_lot import AuctionLotInput
from src.models.db_models import AuctionLot, Base
from src.services.parser import parse_json_data, validate_json_structure
from src.services.image_service import process_images
from src.config import get_settings

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("auction_processor")

# Get settings
settings = get_settings()

# Database setup
if 'sqlite' in settings.database_url:
    db_url = settings.database_url.replace('sqlite://', 'sqlite+aiosqlite://')
else:
    db_url = settings.database_url

engine = create_async_engine(db_url, echo=settings.sql_echo)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize the database by creating tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def store_auction_data(auction_lots: List[AuctionLotInput], storage_paths: Dict[str, str]):
    """Store auction data in the database"""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for lot in auction_lots:
                # Check if this lot already exists
                stmt = sa.select(AuctionLot).where(AuctionLot.lot_ref == lot.lotRef)
                result = await session.execute(stmt)
                existing_lot = result.scalar_one_or_none()
                
                if existing_lot:
                    logger.info(f"Updating existing lot: {lot.lotRef}")
                    
                    # Update lot
                    existing_lot.lot_number = lot.lotNumber
                    existing_lot.title = lot.lotTitle
                    existing_lot.description = getattr(lot, 'description', None)
                    
                    existing_lot.house_name = lot.houseName
                    existing_lot.sale_type = lot.saleType
                    
                    existing_lot.price_realized = lot.priceResult
                    existing_lot.currency_code = lot.currencyCode
                    existing_lot.currency_symbol = lot.currencySymbol
                    
                    existing_lot.photo_path = lot.photoPath
                    
                    # Set storage path if available
                    if lot.lotRef in storage_paths:
                        existing_lot.storage_path = storage_paths[lot.lotRef]
                else:
                    logger.info(f"Creating new lot: {lot.lotRef}")
                    
                    # Create new lot
                    storage_path = storage_paths.get(lot.lotRef, None)
                    
                    # Convert lot to dict for creating AuctionLot
                    lot_dict = {
                        "id": sa.func.uuid_generate_v4() if hasattr(sa.func, 'uuid_generate_v4') else str(uuid.uuid4()),
                        "lot_ref": lot.lotRef,
                        "lot_number": lot.lotNumber,
                        "title": lot.lotTitle,
                        "description": getattr(lot, 'description', None),
                        
                        "house_name": lot.houseName,
                        "sale_type": lot.saleType,
                        "sale_date": datetime.datetime.fromtimestamp(lot.dateTimeUTCUnix),
                        
                        "price_realized": lot.priceResult,
                        "currency_code": lot.currencyCode,
                        "currency_symbol": lot.currencySymbol,
                        
                        "photo_path": lot.photoPath,
                        "storage_path": storage_path,
                        
                        "raw_data": json.dumps({
                            key: value for key, value in lot.dict().items()
                            if key not in [
                                'lotRef', 'lotNumber', 'lotTitle', 'description',
                                'houseName', 'saleType', 'dateTimeUTCUnix',
                                'priceResult', 'currencyCode', 'currencySymbol',
                                'photoPath', 'storagePath'
                            ]
                        })
                    }
                    
                    # Create new lot
                    new_lot = AuctionLot(**lot_dict)
                    session.add(new_lot)
        
        # Commit all changes
        await session.commit()
        logger.info("All auction data committed to database")

async def process_json_file(file_path: str, limit: int = None):
    """
    Process a JSON file containing auction data
    
    Args:
        file_path: Path to the JSON file
        limit: Optional limit on number of items to process
    """
    try:
        # Read JSON data
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if not validate_json_structure(data):
            logger.error("Invalid JSON structure")
            return
        
        # Parse data
        auction_lots = parse_json_data(data)
        logger.info(f"Parsed {len(auction_lots)} auction lots from input data")
        
        if not auction_lots:
            logger.warning("No auction lots found in the data")
            return
            
        # Apply limit if specified
        if limit and limit > 0:
            auction_lots = auction_lots[:limit]
            logger.info(f"Limited processing to first {len(auction_lots)} auction lots")
        
        # Initialize database
        await init_db()
        
        # Process images
        storage_paths = await process_images(auction_lots)
        logger.info(f"Processed {len(storage_paths)} images")
        
        # Store data in database
        await store_auction_data(auction_lots, storage_paths)
        
        logger.info("Processing completed successfully")
    
    except Exception as e:
        logger.error(f"Error processing JSON file: {str(e)}", exc_info=True)
        raise

async def main():
    """Main function"""
    # Check if example JSON file exists
    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_json.json")
    if not os.path.exists(json_file):
        logger.error(f"Example JSON file not found: {json_file}")
        return
    
    # Process JSON file with a limit of 3 items
    await process_json_file(json_file, limit=3)

if __name__ == "__main__":
    import asyncio
    import datetime
    import uuid
    
    asyncio.run(main())