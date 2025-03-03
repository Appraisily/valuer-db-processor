import os
import logging
import aiohttp
import asyncio
from typing import List, Optional
from io import BytesIO
import hashlib
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from src.models.auction_lot import AuctionLotInput
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Define the base URL for image downloads
IMAGE_BASE_URL = "https://image.invaluable.com/housePhotos/"

# Initialize GCS client if not in local development mode
try:
    from google.cloud import storage
    if settings.use_gcs:
        storage_client = storage.Client()
        bucket = storage_client.bucket(settings.gcs_bucket)
        HAS_GCS = True
    else:
        HAS_GCS = False
except Exception as e:
    logger.warning(f"GCS initialization failed: {str(e)}. Using local storage for development.")
    HAS_GCS = False

# Create local storage directory if using local storage
if not HAS_GCS and not os.path.exists(settings.local_storage_path):
    os.makedirs(settings.local_storage_path, exist_ok=True)

async def process_images(auction_lots: List[AuctionLotInput]) -> None:
    """
    Process images from a list of auction lots.
    
    Args:
        auction_lots: List of auction lots to process
    """
    logger.info(f"Processing images for {len(auction_lots)} lots")
    
    # Process images in batches to limit concurrency
    batch_size = settings.batch_size
    batches = [auction_lots[i:i + batch_size] for i in range(0, len(auction_lots), batch_size)]
    
    for batch_index, batch in enumerate(batches):
        logger.info(f"Processing batch {batch_index + 1} of {len(batches)}")
        
        tasks = []
        for lot in batch:
            if lot.photoPath:
                tasks.append(process_single_image(lot))
        
        # Wait for batch to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Image processing completed")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, aiohttp.ClientError))
)
async def process_single_image(lot: AuctionLotInput) -> Optional[str]:
    """
    Process a single image from an auction lot.
    
    Args:
        lot: Auction lot to process
    
    Returns:
        URL of the stored image, or None if processing failed
    """
    if not lot.photoPath:
        logger.warning(f"No photo path for lot {lot.lotRef}")
        return None
    
    try:
        # Download image
        image_data = await download_image(lot.photoPath)
        if not image_data:
            logger.warning(f"Failed to download image for lot {lot.lotRef}")
            return None
        
        # Optimize image if configured
        if settings.optimize_images:
            optimized_data = optimize_image(image_data)
            if optimized_data:
                image_data = optimized_data
        
        # Upload to storage
        if HAS_GCS:
            # Generate GCS path
            image_path = generate_gcs_path(lot)
            return upload_to_gcs(image_data, image_path, lot)
        else:
            # Save to local storage
            image_path = f"{lot.houseName}/{lot.lotRef}/{os.path.basename(lot.photoPath)}"
            return save_to_local(image_data, image_path, lot)
    
    except Exception as e:
        logger.error(f"Error processing image for lot {lot.lotRef}: {str(e)}")
        return None

async def download_image(photo_path: str) -> Optional[bytes]:
    """
    Download an image from a URL.
    
    Args:
        photo_path: Path to the photo
    
    Returns:
        Image data, or None if download failed
    """
    url = f"{IMAGE_BASE_URL}{photo_path}"
    logger.info(f"Downloading image from {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as e:
        logger.error(f"HTTP error downloading image {photo_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading image {photo_path}: {e}")
        return None

def optimize_image(image_data: bytes) -> Optional[bytes]:
    """
    Optimize an image by resizing and compressing it.
    
    Args:
        image_data: Image data to optimize
    
    Returns:
        Optimized image data, or None if optimization failed
    """
    try:
        # Open image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Resize if needed
        max_dimension = settings.max_image_dimension
        if max(image.width, image.height) > max_dimension:
            # Calculate new dimensions while maintaining aspect ratio
            if image.width > image.height:
                new_width = max_dimension
                new_height = int(max_dimension * image.height / image.width)
            else:
                new_height = max_dimension
                new_width = int(max_dimension * image.width / image.height)
            
            # Resize image
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Save optimized image to bytes
        output = BytesIO()
        
        # Save with appropriate format and quality
        if image.format == "JPEG" or not image.format:
            image.save(output, format="JPEG", quality=85, optimize=True)
        elif image.format == "PNG":
            image.save(output, format="PNG", optimize=True)
        else:
            # For other formats, convert to JPEG
            if image.mode == "RGBA":
                # Convert RGBA to RGB for JPEG format
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                background.save(output, format="JPEG", quality=85, optimize=True)
            else:
                image.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
        
        # Get bytes from output
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return None

def generate_gcs_path(lot: AuctionLotInput) -> str:
    """
    Generate a GCS path for an image.
    
    Args:
        lot: Auction lot
    
    Returns:
        GCS path for the image
    """
    # Clean house name for use in path
    house_name = lot.houseName.lower().replace(" ", "_")
    
    # Get filename from path
    filename = os.path.basename(lot.photoPath)
    
    # Structure: {house_name}/{lot_ref}/{filename}
    return f"{house_name}/{lot.lotRef}/{filename}"

def upload_to_gcs(image_data: bytes, image_path: str, lot: AuctionLotInput) -> str:
    """
    Upload an image to Google Cloud Storage.
    
    Args:
        image_data: Image data to upload
        image_path: Path to store the image in GCS
        lot: Auction lot
    
    Returns:
        URL of the uploaded image
    """
    try:
        blob = bucket.blob(image_path)
        
        # Set metadata
        metadata = {
            "original_url": lot.photoPath,
            "lot_ref": lot.lotRef,
            "house_name": lot.houseName,
        }
        blob.metadata = metadata
        
        # Upload
        blob.upload_from_string(
            image_data,
            content_type=f"image/{os.path.splitext(image_path)[1][1:].lower() or 'jpeg'}"
        )
        
        # Make publicly accessible
        blob.make_public()
        
        logger.info(f"Uploaded image to GCS: {image_path}")
        return blob.public_url
    
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        return None

def save_to_local(image_data: bytes, image_path: str, lot: AuctionLotInput) -> str:
    """
    Save an image to local storage.
    
    Args:
        image_data: Image data to save
        image_path: Path to store the image locally
        lot: Auction lot
    
    Returns:
        Path to the saved image
    """
    try:
        # Create full path including directories
        full_path = os.path.join(settings.local_storage_path, image_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save file
        with open(full_path, "wb") as f:
            f.write(image_data)
        
        logger.info(f"Saved image locally: {full_path}")
        return full_path
    
    except Exception as e:
        logger.error(f"Error saving image locally: {e}")
        return None 