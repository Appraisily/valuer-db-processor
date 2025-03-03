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

# Initialize GCS client if not in local development mode
try:
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.gcs_bucket_name)
    HAS_GCS = True
except Exception as e:
    logger.warning(f"GCS initialization failed: {str(e)}. Using local storage for development.")
    HAS_GCS = False

# Local storage directory for development
LOCAL_STORAGE_DIR = 'local_storage'
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

async def process_images(auction_lots: List[AuctionLotInput]) -> None:
    """
    Process images for a list of auction lots.
    
    This function downloads images from their original URLs and
    uploads them to Google Cloud Storage.
    
    Args:
        auction_lots: List of AuctionLotInput objects
    """
    logger.info(f"Starting image processing for {len(auction_lots)} lots")
    
    # Process images in batches to avoid overwhelming the system
    batch_size = settings.image_processing_batch_size
    for i in range(0, len(auction_lots), batch_size):
        batch = auction_lots[i:i+batch_size]
        
        # Create tasks for each lot in the batch
        tasks = [process_single_image(lot) for lot in batch]
        
        # Execute tasks concurrently
        await asyncio.gather(*tasks)
        
        logger.info(f"Processed batch {i//batch_size + 1} of images")
    
    logger.info("Completed image processing")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, aiohttp.ClientError))
)
async def process_single_image(lot: AuctionLotInput) -> Optional[str]:
    """
    Process a single image for an auction lot
    
    Args:
        lot: AuctionLotInput object containing image information
        
    Returns:
        GCS path where the image was uploaded, or None if failed
    """
    try:
        # Ensure we have a photo path
        if not lot.photo_path:
            logger.warning(f"No photo path for lot {lot.lot_ref}")
            return None
            
        # Generate GCS path for this image
        image_path = generate_gcs_path(lot)
        
        # Check if the image already exists in storage
        if HAS_GCS:
            blob = bucket.blob(image_path)
            exists = blob.exists()
        else:
            local_path = os.path.join(LOCAL_STORAGE_DIR, image_path)
            exists = os.path.exists(local_path)
        
        if exists:
            logger.info(f"Image already exists in storage: {image_path}")
            if HAS_GCS:
                return f"gs://{settings.gcs_bucket_name}/{image_path}"
            else:
                return f"local://{LOCAL_STORAGE_DIR}/{image_path}"
        
        # Download the image
        image_data = await download_image(lot.photo_path)
        if not image_data:
            logger.error(f"Failed to download image for lot {lot.lot_ref}")
            return None
        
        # Optimize the image if needed
        optimized_data = optimize_image(image_data)
        image_data_to_upload = optimized_data if optimized_data else image_data
        
        # Upload to storage
        if HAS_GCS:
            return upload_to_gcs(image_data_to_upload, image_path, lot)
        else:
            return save_to_local(image_data_to_upload, image_path, lot)
        
    except Exception as e:
        logger.error(f"Error processing image for lot {lot.lot_ref}: {str(e)}", exc_info=True)
        return None

async def download_image(photo_path: str) -> Optional[bytes]:
    """
    Download an image from the provided URL
    
    Args:
        photo_path: Path or URL to the image
        
    Returns:
        Image data as bytes or None if download failed
    """
    # For local testing, if URL starts with 'test:', return test image data
    if photo_path.startswith('test:'):
        logger.info(f"Using test image for {photo_path}")
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color = (73, 109, 137))
        byte_io = BytesIO()
        img.save(byte_io, 'JPEG')
        return byte_io.getvalue()
    
    # Construct the full URL if it's a relative path
    if not photo_path.startswith(('http://', 'https://')):
        url = f"{settings.base_image_url}/{photo_path}"
    else:
        url = photo_path
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {str(e)}")
        # Return test image for development purposes
        if settings.debug:
            logger.info("Using fallback test image in debug mode")
            img = Image.new('RGB', (100, 100), color = (73, 109, 137))
            byte_io = BytesIO()
            img.save(byte_io, 'JPEG')
            return byte_io.getvalue()
        return None

def optimize_image(image_data: bytes) -> Optional[bytes]:
    """
    Optimize the image by resizing and compressing
    
    Args:
        image_data: Original image data
        
    Returns:
        Optimized image data or None if optimization failed
    """
    if not settings.optimize_images:
        return None
        
    try:
        img = Image.open(BytesIO(image_data))
        
        # Resize if the image is larger than the max dimensions
        max_size = settings.max_image_dimension
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        
        # Save with optimized settings
        output = BytesIO()
        
        if img.format == 'JPEG' or img.mode == 'RGB':
            img.save(output, format='JPEG', quality=85, optimize=True)
        elif img.format == 'PNG':
            img.save(output, format='PNG', optimize=True)
        else:
            # For other formats, convert to JPEG
            if img.mode == 'RGBA':
                # Convert RGBA to RGB by adding white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                background.save(output, format='JPEG', quality=85, optimize=True)
            else:
                img.convert('RGB').save(output, format='JPEG', quality=85, optimize=True)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        return None

def generate_gcs_path(lot: AuctionLotInput) -> str:
    """
    Generate a GCS path for the image based on lot attributes
    
    Args:
        lot: The auction lot
        
    Returns:
        GCS path string
    """
    # Create a clean house name for the folder structure
    house_folder = lot.house_name.lower().replace(' ', '_').replace('/', '_')
    
    # Get the original filename from the photo path
    original_filename = os.path.basename(lot.photo_path)
    
    # Return the full GCS path
    return f"{house_folder}/{lot.lot_ref}/{original_filename}"

def upload_to_gcs(image_data: bytes, image_path: str, lot: AuctionLotInput) -> str:
    """
    Upload an image to Google Cloud Storage
    
    Args:
        image_data: Image data to upload
        image_path: GCS path for the image
        lot: The auction lot for metadata
        
    Returns:
        GCS URI of the uploaded image
    """
    try:
        # Create a blob and upload the image
        blob = bucket.blob(image_path)
        
        # Set metadata for the image
        metadata = {
            'original_path': lot.photo_path,
            'lot_ref': lot.lot_ref,
            'house_name': lot.house_name
        }
        blob.metadata = metadata
        
        # Upload the image
        blob.upload_from_string(
            image_data,
            content_type='image/jpeg'  # Assuming most images are JPEG
        )
        
        logger.info(f"Successfully uploaded image to GCS: {image_path}")
        
        # Return the GCS URI
        return f"gs://{settings.gcs_bucket_name}/{image_path}"
    except Exception as e:
        logger.error(f"Error uploading image to GCS: {str(e)}", exc_info=True)
        return ""

def save_to_local(image_data: bytes, image_path: str, lot: AuctionLotInput) -> str:
    """
    Save an image to local storage for development
    
    Args:
        image_data: Image data to save
        image_path: Path for the image within local storage
        lot: The auction lot for metadata
        
    Returns:
        Local path of the saved image
    """
    try:
        # Create full path including directories
        full_path = os.path.join(LOCAL_STORAGE_DIR, image_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write the file
        with open(full_path, 'wb') as f:
            f.write(image_data)
        
        logger.info(f"Successfully saved image locally: {full_path}")
        
        # Return the local URI
        return f"local://{full_path}"
    except Exception as e:
        logger.error(f"Error saving image locally: {str(e)}", exc_info=True)
        return "" 