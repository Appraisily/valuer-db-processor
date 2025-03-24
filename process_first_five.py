#!/usr/bin/env python3
"""
Auction Data Processor for First Five Items

This script processes the first 5 auction data items from the example JSON file:
1. Reads JSON data
2. Parses and extracts auction lot information
3. Creates placeholder images (since real downloading is blocked)
4. Stores data in a local SQLite database
"""

import json
import logging
import os
import sys
import asyncio
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the current directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.auction_lot import AuctionLotInput
from src.services.parser import parse_json_data, validate_json_structure
from src.config import get_settings, Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("processor")

# Import SQLite-specific components to avoid PostgreSQL dependency
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.db_models import Base, AuctionLot
import sqlalchemy as sa
import json
import httpx
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Custom image service implementation with placeholder images
async def process_images(auction_lots: List[AuctionLotInput]) -> Dict[str, str]:
    """
    Create placeholder images for the auction lots since real downloading is blocked.
    
    Args:
        auction_lots: List of auction lots to process
        
    Returns:
        Dictionary mapping lot references to their storage paths
    """
    logger.info(f"Creating placeholder images for {len(auction_lots)} lots")
    
    # Get settings
    settings = get_settings()
    
    # Process images one by one
    storage_paths = {}
    
    for lot in auction_lots:
        if not lot.photoPath:
            logger.warning(f"No photo path for lot {lot.lotRef}")
            continue
            
        try:
            # Create directory structure
            house_dir = settings.local_storage_path
            lot_dir = os.path.join(house_dir, lot.houseName.lower().replace(" ", "_"), lot.lotRef)
            os.makedirs(lot_dir, exist_ok=True)
            
            # Get filename
            filename = os.path.basename(lot.photoPath)
            output_path = os.path.join(lot_dir, filename)
            
            # Create a placeholder image
            width, height = 400, 300
            img = Image.new('RGB', (width, height), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            
            # Draw border
            border_width = 5
            draw.rectangle(
                [(border_width, border_width), (width - border_width, height - border_width)],
                outline=(200, 200, 200),
                width=border_width
            )
            
            # Draw text
            text_lines = [
                f"Lot: {lot.lotRef}",
                f"Title: {lot.lotTitle[:30]}...",
                f"Auction House: {lot.houseName}",
                f"Price: {lot.currencySymbol}{lot.priceResult}",
                "Placeholder Image"
            ]
            
            # Position text in center
            y_position = 50
            for text in text_lines:
                # Draw with simple default font since we don't have access to system fonts
                draw.text((width // 2, y_position), text, fill=(0, 0, 0), anchor="mm")
                y_position += 40
            
            # Save image
            img.save(output_path, format="JPEG", quality=85)
            
            # Store path
            rel_path = os.path.join(lot.houseName.lower().replace(" ", "_"), lot.lotRef, filename)
            storage_paths[lot.lotRef] = rel_path
            logger.info(f"Created placeholder image for lot {lot.lotRef}")
            
        except Exception as e:
            logger.error(f"Error creating placeholder image for lot {lot.lotRef}: {e}")
            continue
    
    logger.info(f"Placeholder image creation completed, created {len(storage_paths)} images")
    return storage_paths

async def init_db():
    """Initialize the database by creating tables"""
    # Get settings
    settings = get_settings()
    
    # Ensure we're using SQLite
    if 'sqlite' not in settings.database_url:
        settings.database_url = "sqlite+aiosqlite:///./local_data/valuer.db"
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info(f"Database initialized: {settings.database_url}")
    
    return engine

async def store_auction_data(auction_lots: List[AuctionLotInput]):
    """Store auction data in the database"""
    # Get settings
    settings = get_settings()
    
    # Ensure we're using SQLite
    if 'sqlite' not in settings.database_url:
        settings.database_url = "sqlite+aiosqlite:///./local_data/valuer.db"
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
    
    # Create session
    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Store data
    results = []
    
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for lot_input in auction_lots:
                try:
                    # Check if lot exists
                    stmt = sa.select(AuctionLot).where(AuctionLot.lot_ref == lot_input.lotRef)
                    result = await session.execute(stmt)
                    existing_lot = result.scalar_one_or_none()
                    
                    if existing_lot:
                        # Update existing lot
                        logger.info(f"Updating existing lot: {lot_input.lotRef}")
                        
                        # Update fields
                        existing_lot.lot_number = lot_input.lotNumber
                        existing_lot.title = lot_input.lotTitle
                        existing_lot.description = getattr(lot_input, 'description', None)
                        
                        existing_lot.house_name = lot_input.houseName
                        existing_lot.sale_type = lot_input.saleType
                        existing_lot.sale_date = datetime.datetime.fromtimestamp(lot_input.dateTimeUTCUnix)
                        
                        existing_lot.price_realized = lot_input.priceResult
                        existing_lot.currency_code = lot_input.currencyCode
                        existing_lot.currency_symbol = lot_input.currencySymbol
                        
                        existing_lot.photo_path = lot_input.photoPath
                        existing_lot.storage_path = getattr(lot_input, 'storagePath', None)
                        
                        existing_lot.updated_at = datetime.datetime.now(datetime.UTC)
                        
                        # Update raw data
                        existing_raw_data = json.loads(existing_lot.raw_data) if existing_lot.raw_data else {}
                        
                        # Create dict from lot_input excluding main fields
                        new_raw_data = {}
                        lot_data = lot_input.__dict__
                        for key, value in lot_data.items():
                            if key not in [
                                'lotRef', 'lotNumber', 'lotTitle', 'description',
                                'houseName', 'saleType', 'dateTimeUTCUnix',
                                'priceResult', 'currencyCode', 'currencySymbol',
                                'photoPath', 'storagePath'
                            ]:
                                new_raw_data[key] = value
                        
                        # Merge old and new data
                        merged_data = {**existing_raw_data, **new_raw_data}
                        existing_lot.raw_data = json.dumps(merged_data)
                        
                        # No need to add to session since it's already tracked
                        results.append(existing_lot)
                    else:
                        # Create new lot
                        logger.info(f"Creating new lot: {lot_input.lotRef}")
                        
                        # Get storage path if available
                        storage_path = getattr(lot_input, 'storagePath', None)
                        
                        # Convert lot to dict for creating AuctionLot
                        lot_dict = {
                            "id": str(uuid.uuid4()),
                            "lot_ref": lot_input.lotRef,
                            "lot_number": lot_input.lotNumber,
                            "title": lot_input.lotTitle,
                            "description": getattr(lot_input, 'description', None),
                            
                            "house_name": lot_input.houseName,
                            "sale_type": lot_input.saleType,
                            "sale_date": datetime.datetime.fromtimestamp(lot_input.dateTimeUTCUnix),
                            
                            "price_realized": lot_input.priceResult,
                            "currency_code": lot_input.currencyCode,
                            "currency_symbol": lot_input.currencySymbol,
                            
                            "photo_path": lot_input.photoPath,
                            "storage_path": storage_path,
                            
                            "created_at": datetime.datetime.now(datetime.UTC),
                            "updated_at": datetime.datetime.now(datetime.UTC),
                        }
                        
                        # Create raw data
                        raw_data = {}
                        lot_data = lot_input.__dict__
                        for key, value in lot_data.items():
                            if key not in [
                                'lotRef', 'lotNumber', 'lotTitle', 'description',
                                'houseName', 'saleType', 'dateTimeUTCUnix',
                                'priceResult', 'currencyCode', 'currencySymbol',
                                'photoPath', 'storagePath'
                            ]:
                                raw_data[key] = value
                        
                        lot_dict["raw_data"] = json.dumps(raw_data)
                        
                        # Create new lot
                        new_lot = AuctionLot(**lot_dict)
                        session.add(new_lot)
                        results.append(new_lot)
                
                except Exception as e:
                    logger.error(f"Error processing lot {lot_input.lotRef}: {str(e)}")
                    # Continue with next lot
                    continue
    
    logger.info(f"Successfully stored {len(results)} auction lots")
    return results

async def process_json_file(file_path: str, limit: int = 5):
    """
    Process a JSON file containing auction data
    
    Args:
        file_path: Path to the JSON file
        limit: Number of items to process (default: 5)
    """
    try:
        # Get settings
        settings = get_settings()
        
        # Set for local development
        settings.use_gcs = False
        settings.db_type = "sqlite"
        
        # Read JSON data
        with open(file_path, 'r', encoding='utf-8') as f:
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
        
        # Apply limit - use only the first 5
        auction_lots = auction_lots[:limit]
        logger.info(f"Processing the first {len(auction_lots)} auction lots")
        
        # Initialize database
        await init_db()
        
        # Process images - create placeholders locally
        storage_paths = await process_images(auction_lots)
        logger.info(f"Processed {len(storage_paths)} images")
        
        # Update auction lots with storage paths
        for lot in auction_lots:
            if lot.lotRef in storage_paths:
                setattr(lot, 'storagePath', storage_paths[lot.lotRef])
        
        # Store data in database
        stored_lots = await store_auction_data(auction_lots)
        logger.info(f"Successfully stored {len(stored_lots)} auction lots")
        
        # Print summary of processed items
        logger.info("Processing summary:")
        for i, lot in enumerate(stored_lots):
            logger.info(f"Item {i+1}: {lot.lot_ref} - {lot.title}")
        
        logger.info("Processing completed successfully")
    
    except Exception as e:
        logger.error(f"Error processing JSON file: {str(e)}", exc_info=True)
        raise

async def main():
    """Main function"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Process first 5 auction items')
    parser.add_argument('--limit', type=int, default=5, help='Number of items to process (default: 5)')
    parser.add_argument('--file', type=str, help='Path to the JSON file', 
                       default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_json.json"))
    parser.add_argument('--output', type=str, help='Output directory for database', 
                       default="local_data")
    parser.add_argument('--image-dir', type=str, help='Directory for image storage', 
                       default="local_images")
    
    args = parser.parse_args()
    
    # Check if JSON file exists
    if not os.path.exists(args.file):
        logger.error(f"JSON file not found: {args.file}")
        return
    
    # Update settings based on arguments
    settings = get_settings()
    settings.local_storage_path = args.image_dir
    settings.database_url = f"sqlite+aiosqlite:///./local_data/valuer.db"
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(args.image_dir, exist_ok=True)
    
    # Process JSON file with specified limit
    await process_json_file(args.file, limit=args.limit)
    
    logger.info(f"Results stored in database: {settings.database_url}")
    logger.info(f"Images downloaded to: {settings.local_storage_path}")

if __name__ == "__main__":
    asyncio.run(main())