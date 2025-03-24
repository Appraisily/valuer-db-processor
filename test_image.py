import asyncio
import logging
import os
import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Import from your actual image service
from src.models.auction_lot import AuctionLotInput
from src.services.image_service import download_image, optimize_image, save_to_local
from src.config import get_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Example photo paths to test (real examples from Invaluable)
TEST_PHOTO_PATHS = [
    "stairgalleries/1/131/17879596_1.jpg",
    "lempertz/2/128/S171V0810_1.jpg", 
    "chalkwell/1/112/15566307_1.jpg",
    "aspireauctions/1/208/28732865_1.jpg",
    "boisgirard/1/85/12028873_1.jpg"
]

# Alternative CDN URLs to try if the primary URL fails
ALTERNATIVE_CDN_URLS = [
    "https://media.invaluable.com/housePhotos/",
    "https://www.invaluable.com/housePhotos/",
    "https://cdn.invaluable.com/housePhotos/"
]

async def test_direct_download(photo_path, output_prefix="test_direct"):
    """Test downloading directly with httpx without using our service layer"""
    import httpx
    
    # Browser-like headers to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.invaluable.com/",
        "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    
    # Create output directory
    os.makedirs("./local_images", exist_ok=True)
    
    # Try primary URL
    primary_url = f"https://image.invaluable.com/housePhotos/{photo_path}"
    logger.info(f"Trying primary URL: {primary_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                primary_url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                # Save the image
                image_filename = f"./local_images/{output_prefix}_primary.jpg"
                with open(image_filename, "wb") as f:
                    f.write(response.content)
                logger.info(f"✅ Downloaded image from primary URL: {image_filename}")
                return True
            else:
                logger.warning(f"❌ Primary URL response is not an image. Content type: {content_type}")
                
    except Exception as e:
        logger.warning(f"❌ Failed with primary URL: {e}")
    
    # Try alternative URLs
    for i, alt_url_base in enumerate(ALTERNATIVE_CDN_URLS):
        alt_url = f"{alt_url_base}{photo_path}"
        logger.info(f"Trying alternative URL {i+1}: {alt_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    alt_url, 
                    timeout=30.0, 
                    follow_redirects=True,
                    headers=headers
                )
                response.raise_for_status()
                
                # Check if it's an image
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    # Save the image
                    image_filename = f"./local_images/{output_prefix}_alt{i+1}.jpg"
                    with open(image_filename, "wb") as f:
                        f.write(response.content)
                    logger.info(f"✅ Downloaded image from alternative URL {i+1}: {image_filename}")
                    return True
                else:
                    logger.warning(f"❌ Alternative URL {i+1} response is not an image. Content type: {content_type}")
                    
        except Exception as e:
            logger.warning(f"❌ Failed with alternative URL {i+1}: {e}")
    
    logger.error(f"❌ All URLs failed for {photo_path}")
    return False

async def test_service_download(photo_path, output_prefix="test_service"):
    """Test using our actual service layer to download the image"""
    logger.info(f"Testing download via service layer for: {photo_path}")
    
    # Download using our service
    image_data = await download_image(photo_path)
    
    if image_data:
        logger.info(f"✅ Successfully downloaded {photo_path} ({len(image_data)} bytes)")
        
        # Save raw image for verification 
        os.makedirs("./local_images", exist_ok=True)
        raw_path = f"./local_images/{output_prefix}_raw.jpg"
        with open(raw_path, "wb") as f:
            f.write(image_data)
        
        # Optimize the image
        optimized_data = optimize_image(image_data)
        if optimized_data:
            logger.info(f"✅ Successfully optimized image from {len(image_data)} to {len(optimized_data)} bytes")
            
            # Create a mock auction lot for storage
            mock_lot = AuctionLotInput(
                lotNumber="TEST-1",
                lotRef="TEST-REF-1",
                lotTitle="Test Lot",
                description="Test description",
                houseName="TestHouse",
                saleType="test",
                dateTimeLocal="2023-01-01T12:00:00",
                dateTimeUTCUnix=1672574400,
                priceResult=1000.00,
                currencyCode="USD",
                currencySymbol="$",
                photoPath=photo_path
            )
            
            # Save to local storage using our service
            settings = get_settings()
            image_path = f"{mock_lot.houseName}/{mock_lot.lotRef}/{photo_path.split('/')[-1]}"
            local_path = save_to_local(optimized_data, image_path, mock_lot)
            
            if local_path:
                logger.info(f"✅ Successfully saved optimized image to: {local_path}")
                return True
            else:
                logger.error(f"❌ Failed to save image for {photo_path}")
        else:
            logger.error(f"❌ Failed to optimize image for {photo_path}")
    else:
        logger.error(f"❌ Failed to download image for {photo_path}")
    
    return False

async def create_placeholder_image(photo_path, output_prefix="test_placeholder"):
    """Test creating a placeholder image"""
    logger.info(f"Creating placeholder image for: {photo_path}")
    
    try:
        # Create a sample image with information
        img = Image.new('RGB', (800, 600), color=(245, 245, 245))
        d = ImageDraw.Draw(img)
        
        # Add text with image path
        text_y = 100
        d.text((100, text_y), "Sample Placeholder Image", fill='black')
        text_y += 50
        d.text((100, text_y), f"Path: {photo_path}", fill='black')
        text_y += 50
        d.text((100, text_y), f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill='black')
        
        # Add border
        border_width = 2
        d.rectangle([(border_width, border_width), (799 - border_width, 599 - border_width)], 
                   outline=(200, 200, 200), width=border_width)
        
        # Save to local storage
        os.makedirs("./local_images", exist_ok=True)
        local_path = f"./local_images/{output_prefix}.jpg"
        
        # Save the image
        img.save(local_path, format="JPEG", quality=85)
        logger.info(f"✅ Created placeholder image at {local_path}")
        
        # Return the image data
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"❌ Failed to create placeholder image: {e}")
        return None

async def test_image_download(photo_path, index):
    """Run all tests for a single image path"""
    logger.info(f"\n=== Testing image {index}: {photo_path} ===")
    
    # Test prefix for this image's output files
    test_prefix = f"test_output_{index}"
    
    # Try using direct download first
    direct_result = await test_direct_download(photo_path, test_prefix)
    
    # Try using our service layer
    service_result = await test_service_download(photo_path, test_prefix)
    
    # Create a placeholder if both methods failed
    if not direct_result and not service_result:
        placeholder_data = await create_placeholder_image(photo_path, f"{test_prefix}_placeholder")
        if placeholder_data:
            return "PLACEHOLDER"
        else:
            return "FAILED"
    
    if service_result:
        return "SERVICE_SUCCESS"
    elif direct_result:
        return "DIRECT_SUCCESS"
    else:
        return "FAILED"

async def main():
    """Test image download process with multiple examples"""
    logger.info("=== Starting Image Download Tests ===")
    
    settings = get_settings()
    logger.info(f"Using environment: {settings.env}")
    logger.info(f"Local storage path: {settings.local_storage_path}")
    
    results = []
    for i, photo_path in enumerate(TEST_PHOTO_PATHS, 1):
        result = await test_image_download(photo_path, i)
        results.append((photo_path, result))
    
    # Print summary
    logger.info("\n=== TEST RESULTS SUMMARY ===")
    for photo_path, status in results:
        logger.info(f"{status}: {photo_path}")
    
    # Count different types of results
    service_successes = sum(1 for _, status in results if status == "SERVICE_SUCCESS")
    direct_successes = sum(1 for _, status in results if status == "DIRECT_SUCCESS")
    placeholders = sum(1 for _, status in results if status == "PLACEHOLDER")
    failures = sum(1 for _, status in results if status == "FAILED")
    
    total = len(results)
    logger.info(f"\nFINAL SUMMARY:")
    logger.info(f"Service layer success: {service_successes}/{total} ({service_successes/total*100:.1f}%)")
    logger.info(f"Direct download success: {direct_successes}/{total} ({direct_successes/total*100:.1f}%)")
    logger.info(f"Placeholder images: {placeholders}/{total} ({placeholders/total*100:.1f}%)")
    logger.info(f"Complete failures: {failures}/{total} ({failures/total*100:.1f}%)")
    logger.info(f"Overall success rate: {(service_successes + direct_successes)/total*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())