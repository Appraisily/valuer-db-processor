import asyncio
import os
import logging
from playwright.async_api import async_playwright
from PIL import Image
from io import BytesIO

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

# Base URL
BASE_URL = "https://image.invaluable.com/housePhotos/"

async def download_with_playwright(photo_path):
    """
    Use Playwright headless browser to download an image
    """
    logger.info(f"Attempting to download {photo_path} with Playwright")
    
    # Create output directory
    os.makedirs("./local_images", exist_ok=True)
    output_path = f"./local_images/headless_{os.path.basename(photo_path)}"
    
    # Full URL to the image
    url = f"{BASE_URL}{photo_path}"
    
    # Using Playwright to simulate a browser
    async with async_playwright() as p:
        # Launch a headless browser
        browser = await p.chromium.launch(headless=True)
        
        try:
            # Create a new context with specific viewport and user agent
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            
            # First visit the invaluable.com homepage to set cookies
            page = await context.new_page()
            logger.info("Visiting homepage to establish session...")
            await page.goto("https://www.invaluable.com/", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            
            # Now navigate to the image URL
            logger.info(f"Navigating to image URL: {url}")
            
            # Create a listener for response events
            image_buffer = None
            
            async def handle_response(response):
                nonlocal image_buffer
                if response.url == url and response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        logger.info(f"Detected image response: {response.status}")
                        image_buffer = await response.body()
            
            page.on("response", handle_response)
            
            try:
                # Navigate to the image URL and wait for the image response
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # If the direct navigation failed, try to load the image in an img tag
                if response.status != 200 or "image" not in response.headers.get("content-type", ""):
                    logger.info(f"Direct navigation failed with status {response.status}. Trying img tag approach...")
                    
                    # Create a new page with an img tag loading the image
                    await page.close()
                    page = await context.new_page()
                    
                    # Add referer and other headers
                    await page.set_extra_http_headers({
                        "Referer": "https://www.invaluable.com/",
                        "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8"',
                        "sec-ch-ua-mobile": "?0", 
                        "sec-ch-ua-platform": '"Windows"'
                    })
                    
                    # Create a simple HTML page with an img tag
                    await page.set_content(f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Image Loader</title>
                    </head>
                    <body>
                        <h1>Loading image...</h1>
                        <img src="{url}" id="targetImage" />
                        <script>
                            document.getElementById('targetImage').onload = function() {{
                                console.log('Image loaded successfully');
                            }};
                            document.getElementById('targetImage').onerror = function() {{
                                console.error('Image failed to load');
                            }};
                        </script>
                    </body>
                    </html>
                    """)
                    
                    # Wait for the image to load
                    try:
                        await page.wait_for_selector('#targetImage[complete="true"]', timeout=10000)
                        logger.info("Image element loaded, attempting to capture...")
                        
                        # Try to take a screenshot of just the image element
                        image_element = await page.query_selector('#targetImage')
                        if image_element:
                            screenshot = await image_element.screenshot()
                            with open(output_path, "wb") as f:
                                f.write(screenshot)
                            logger.info(f"✅ Saved image element screenshot to {output_path}")
                            return True
                    except Exception as e:
                        logger.error(f"Error waiting for image element: {e}")
                
                # If we got the image through the response handler
                if image_buffer:
                    with open(output_path, "wb") as f:
                        f.write(image_buffer)
                    logger.info(f"✅ Successfully saved image to {output_path}")
                    return True
                
                # If we get here, try taking a full page screenshot as last resort
                logger.info("Trying full page screenshot as fallback...")
                screenshot = await page.screenshot()
                with open(f"./local_images/headless_page_{os.path.basename(photo_path)}", "wb") as f:
                    f.write(screenshot)
                logger.info(f"✅ Saved page screenshot")
                return False
                
            except Exception as e:
                logger.error(f"Error navigating to image URL: {e}")
                return False
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            return False
        finally:
            await browser.close()
    
    return False

async def main():
    """Test image downloads with headless browser approach"""
    logger.info("=== Starting Headless Browser Tests ===")
    
    results = []
    for photo_path in TEST_PHOTO_PATHS:
        logger.info(f"\n=== Testing image: {photo_path} ===")
        
        success = await download_with_playwright(photo_path)
        results.append((photo_path, "HEADLESS_SUCCESS" if success else "HEADLESS_FAILED"))
    
    # Print summary
    logger.info("\n=== TEST RESULTS SUMMARY ===")
    for photo_path, status in results:
        logger.info(f"{status}: {photo_path}")
    
    # Count results
    successes = sum(1 for _, status in results if status == "HEADLESS_SUCCESS")
    failures = sum(1 for _, status in results if status == "HEADLESS_FAILED")
    
    total = len(results)
    logger.info(f"\nFINAL SUMMARY:")
    logger.info(f"Headless browser success: {successes}/{total} ({successes/total*100:.1f}%)")
    logger.info(f"Failures: {failures}/{total} ({failures/total*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())