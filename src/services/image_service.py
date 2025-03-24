import os
import logging
import aiohttp
import asyncio
import datetime
import socket
import subprocess
from typing import List, Optional, Tuple
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
BASE_DOMAIN = "image.invaluable.com"

# Define alternative CDN URLs to try if the primary URL fails
ALTERNATIVE_CDN_URLS = [
    "https://media.invaluable.com/housePhotos/",
    "https://www.invaluable.com/housePhotos/",
    "https://cdn.invaluable.com/housePhotos/"
]

# Try to find the origin IP once at module load time
try:
    ORIGIN_IP = socket.gethostbyname(BASE_DOMAIN)
    logger.info(f"Resolved {BASE_DOMAIN} to IP: {ORIGIN_IP}")
except Exception as e:
    logger.warning(f"Failed to resolve domain IP with socket: {e}")
    ORIGIN_IP = None
    
    # Try using nslookup as a fallback
    try:
        result = subprocess.run(
            ["nslookup", BASE_DOMAIN], 
            capture_output=True, 
            text=True
        )
        # Parse the output to find IP addresses
        output_lines = result.stdout.split('\n')
        ip_addresses = []
        for line in output_lines:
            if "Address:" in line and not "127.0.0.1" in line:
                ip = line.split("Address:")[1].strip()
                ip_addresses.append(ip)
        
        if ip_addresses:
            ORIGIN_IP = ip_addresses[0]  # Use the first IP
            logger.info(f"Resolved {BASE_DOMAIN} to IP using nslookup: {ORIGIN_IP}")
    except Exception as e:
        logger.warning(f"Failed to run nslookup command: {e}")
        ORIGIN_IP = None

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
    Download an image from a URL or use local sample in development mode.
    
    Args:
        photo_path: Path to the photo
    
    Returns:
        Image data, or None if download failed
    """
    # Check if we're in development mode and if a local sample exists
    if settings.env == "development":
        local_sample_path = os.path.join(settings.local_storage_path, photo_path)
        if os.path.exists(local_sample_path):
            logger.info(f"Using local sample image: {local_sample_path}")
            try:
                with open(local_sample_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading local sample image: {e}")
                # Continue to regular download if local file can't be read
    
    # Enhanced browser-like headers to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.invaluable.com/",
        "Origin": "https://www.invaluable.com",
        "Connection": "keep-alive",
        "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
    }
    
    # Try standard method first
    image_data = await try_standard_download(photo_path, headers)
    if image_data:
        return image_data
    
    # If standard method fails, try origin IP method
    if ORIGIN_IP:
        image_data = await try_origin_ip_download(photo_path, ORIGIN_IP, headers)
        if image_data:
            return image_data
    
    # If all download methods fail and we're in development, create a sample
    if settings.env == "development":
        sample_dir = os.path.dirname(os.path.join(settings.local_storage_path, photo_path))
        os.makedirs(sample_dir, exist_ok=True)
        
        # Create a sample image with information
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (800, 600), color=(245, 245, 245))
            d = ImageDraw.Draw(img)
            
            # Add text with image path
            text_y = 100
            d.text((100, text_y), "Sample Image", fill='black')
            text_y += 50
            d.text((100, text_y), f"Path: {photo_path}", fill='black')
            text_y += 50
            d.text((100, text_y), f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill='black')
            
            # Add border
            border_width = 2
            d.rectangle([(border_width, border_width), (799 - border_width, 599 - border_width)], 
                       outline=(200, 200, 200), width=border_width)
            
            # Save to local storage
            local_path = os.path.join(settings.local_storage_path, photo_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Save the image
            img.save(local_path, format="JPEG", quality=85)
            logger.info(f"Created sample image at {local_path}")
            
            # Return the image data
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to create sample image: {e}")
    
    # Last resort: create a placeholder image
    logger.error(f"All download methods failed for image {photo_path}, using placeholder")
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (800, 600), color='white')
        d = ImageDraw.Draw(img)
        d.text((100, 250), f"Image not available\n{photo_path}", fill='black')
        
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed to create placeholder image: {e}")
        return None

async def try_standard_download(photo_path: str, headers: dict) -> Optional[bytes]:
    """
    Try to download an image using standard HTTPS requests with enhanced headers.
    
    Args:
        photo_path: Path to the photo
        headers: HTTP headers to use for the request
    
    Returns:
        Image data if successful, otherwise None
    """
    # Try the main URL first
    url = f"{IMAGE_BASE_URL}{photo_path}"
    logger.info(f"Attempting to download image from {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"Successfully downloaded image from {url}")
            return response.content
    except httpx.HTTPError as primary_error:
        logger.warning(f"HTTP error with primary URL {url}: {primary_error}")
        
        # Try alternative CDN URLs if the primary URL fails
        for alt_base_url in ALTERNATIVE_CDN_URLS:
            alt_url = f"{alt_base_url}{photo_path}"
            logger.info(f"Trying alternative URL: {alt_url}")
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        alt_url, 
                        timeout=30.0, 
                        follow_redirects=True,
                        headers=headers
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully downloaded image from alternative URL {alt_url}")
                    return response.content
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error with alternative URL {alt_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error with alternative URL {alt_url}: {e}")
                continue
        
        # Try host header injection approach
        host_headers = ["cdn.invaluable.com", "media.invaluable.com", "origin-images.invaluable.com"]
        for host in host_headers:
            try:
                host_override_headers = headers.copy()
                host_override_headers["Host"] = host
                
                logger.info(f"Trying host header injection with {host}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        timeout=30.0,
                        follow_redirects=True,
                        headers=host_override_headers
                    )
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        logger.info(f"Successfully downloaded image using host header injection with {host}")
                        return response.content
                    else:
                        logger.warning(f"Host injection response with {host} is not an image")
            except Exception as e:
                logger.warning(f"Error with host header injection using {host}: {e}")
                continue
        
        return None
            
    except Exception as e:
        logger.error(f"Error downloading image {photo_path}: {e}")
        return None

async def try_origin_ip_download(photo_path: str, ip_address: str, headers: dict) -> Optional[bytes]:
    """
    Try to download an image by accessing the origin IP directly.
    
    Args:
        photo_path: Path to the photo
        ip_address: Origin IP address
        headers: HTTP headers to use for the request
    
    Returns:
        Image data if successful, otherwise None
    """
    # Try HTTP first (more likely to work with direct IP)
    url = f"http://{ip_address}/housePhotos/{photo_path}"
    logger.info(f"Attempting to download from origin IP: {url}")
    
    # Add Host header to direct IP request
    ip_headers = headers.copy()
    ip_headers["Host"] = BASE_DOMAIN  # Critical for IP-based requests
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=ip_headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                logger.info(f"Successfully downloaded image via origin IP approach")
                return response.content
            else:
                logger.warning(f"Origin IP response is not an image. Content type: {content_type}")
                
    except Exception as e:
        logger.warning(f"Failed with HTTP IP approach: {e}")
    
    # Try HTTPS as a backup
    url = f"https://{ip_address}/housePhotos/{photo_path}"
    logger.info(f"Attempting to download from origin IP over HTTPS: {url}")
    
    try:
        # Note: verify=False because we're connecting to an IP directly
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=ip_headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                logger.info(f"Successfully downloaded image via HTTPS origin IP approach")
                return response.content
            else:
                logger.warning(f"HTTPS origin IP response is not an image. Content type: {content_type}")
                return None
                
    except Exception as e:
        logger.warning(f"Failed with HTTPS IP approach: {e}")
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