#!/usr/bin/env python
"""
Script to download auction lot images from the processed data
"""
import os
import sys
import logging
import asyncio
import aiohttp
from pathlib import Path
from PIL import Image
from io import BytesIO
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("image_downloader")

# Define constants
MAX_CONCURRENT_DOWNLOADS = 5
IMAGE_FOLDER = "downloaded_images"
RESIZE_MAX_DIMENSION = 1200  # Maximum dimension for resizing images

async def download_image(session, url, output_path, optimize=True):
    """Download a single image and save it to disk"""
    try:
        # Set browser-like headers to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.invaluable.com/"
        }
        
        # Download image with browser-like headers
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Failed to download {url}, status: {response.status}")
                return False
            
            # Read image data
            image_data = await response.read()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Optimize image if requested
            if optimize:
                # Open image with PIL
                img = Image.open(BytesIO(image_data))
                
                # Resize if needed
                width, height = img.size
                if max(width, height) > RESIZE_MAX_DIMENSION:
                    # Calculate new dimensions while maintaining aspect ratio
                    if width > height:
                        new_width = RESIZE_MAX_DIMENSION
                        new_height = int(height * (RESIZE_MAX_DIMENSION / width))
                    else:
                        new_height = RESIZE_MAX_DIMENSION
                        new_width = int(width * (RESIZE_MAX_DIMENSION / height))
                    
                    # Resize image
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Save optimized image
                img.save(output_path, optimize=True, quality=85)
            else:
                # Save raw image data
                with open(output_path, 'wb') as f:
                    f.write(image_data)
            
            logger.info(f"Downloaded and saved: {output_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

async def download_all_images(lot_data, limit=None):
    """
    Download images for the auction lots
    
    Args:
        lot_data: List of lots to process
        limit: Optional limit on number of items to process
    """
    # Create base folder for images
    base_folder = Path(IMAGE_FOLDER)
    base_folder.mkdir(exist_ok=True)
    
    # Apply limit if specified
    if limit and limit > 0:
        logger.info(f"Limiting image downloads to first {limit} items")
        lot_data = lot_data[:limit]
    
    # Set up HTTP session for downloads
    async with aiohttp.ClientSession() as session:
        # Create tasks for downloading images
        tasks = []
        for lot in lot_data:
            if not lot["imageUrl"]:
                continue
                
            # Create a folder structure: {house_name}/{lot_ref}
            folder = base_folder / lot["houseName"].lower().replace(" ", "_") / lot["lotRef"]
            filename = os.path.basename(lot["photoPath"])
            output_path = folder / filename
            
            # Add download task
            task = download_image(session, lot["imageUrl"], output_path)
            tasks.append(task)
            
            # Process in batches to limit concurrency
            if len(tasks) >= MAX_CONCURRENT_DOWNLOADS:
                await asyncio.gather(*tasks)
                tasks = []
        
        # Process any remaining tasks
        if tasks:
            await asyncio.gather(*tasks)

def read_processed_data(file_path):
    """Read the processed auction data from a file"""
    lots = []
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    # Try different encodings
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Skip header line
                next(f)
                
                # Read and parse each line
                for line in f:
                    parts = line.strip().split('|')
                    if len(parts) >= 6:
                        lot = {
                            "lotRef": parts[0],
                            "lotNumber": parts[1],
                            "lotTitle": parts[2],
                            "houseName": parts[3],
                            "photoPath": parts[4],
                            "imageUrl": parts[5]
                        }
                        lots.append(lot)
            
            # If we get here, the encoding worked
            break
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode with {encoding}, trying next encoding...")
            continue
        except Exception as e:
            logger.error(f"Error reading processed data: {e}")
            return []
    
    logger.info(f"Read {len(lots)} lots from {file_path}")
    return lots

async def main():
    """Main function"""
    # Path to the processed data file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(current_dir, "processed_lots.txt")
    
    if not os.path.exists(data_file):
        logger.error(f"Processed data file not found: {data_file}")
        return
    
    # Read processed data
    lots = read_processed_data(data_file)
    if not lots:
        logger.error("No lots found in the processed data file")
        return
    
    # Download images (limit to first 3)
    await download_all_images(lots, limit=3)
    logger.info("Image download completed")

if __name__ == "__main__":
    asyncio.run(main())