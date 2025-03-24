import asyncio
import httpx
import os
from PIL import Image
from io import BytesIO

# Test image URL
TEST_IMAGE_PATH = "soulis/58/778358/H1081-L382842666.jpg"
ALTERNATIVE_URL_PREFIX = "https://media.invaluable.com/housePhotos/"

async def test_image_proxy():
    """
    Test downloading an image using an alternative URL prefix
    
    Invaluable might be using different domains for their CDN,
    so we'll try media.invaluable.com instead of image.invaluable.com
    """
    original_url = f"https://image.invaluable.com/housePhotos/{TEST_IMAGE_PATH}"
    alternative_url = f"{ALTERNATIVE_URL_PREFIX}{TEST_IMAGE_PATH}"
    
    print(f"Original URL: {original_url}")
    print(f"Alternative URL: {alternative_url}")
    
    # Set browser-like headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.invaluable.com/",
    }
    
    # Try the alternative URL
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                alternative_url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                print(f"Success! Downloaded image with Content-Type: {content_type}")
                
                # Create directory if it doesn't exist
                os.makedirs("./local_images", exist_ok=True)
                
                # Save the image locally for verification
                local_path = f"./local_images/test_image_proxy.jpg"
                with open(local_path, "wb") as f:
                    f.write(response.content)
                print(f"Saved image to {local_path}")
                
                # Verify it's a valid image
                try:
                    img = Image.open(BytesIO(response.content))
                    print(f"Valid image with size: {img.size}, format: {img.format}")
                except Exception as e:
                    print(f"Not a valid image: {e}")
                    
            else:
                print(f"Response is not an image. Content-Type: {content_type}")
                
    except httpx.HTTPError as e:
        print(f"HTTP error with alternative URL: {e}")
        
        # Try with a different approach - direct auction listing page
        try:
            print("\nTrying a different approach...")
            # Try to fetch the auction listing page that would contain this image
            lot_ref = TEST_IMAGE_PATH.split("/")[-1].split("-")[-1].split(".")[0]
            listing_url = f"https://www.invaluable.com/auction-lot/{lot_ref}"
            print(f"Fetching auction listing page: {listing_url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    listing_url, 
                    timeout=30.0, 
                    follow_redirects=True,
                    headers=headers
                )
                
                if response.status_code == 200:
                    print("Successfully fetched listing page")
                    
                    # Look for image URLs in the page
                    html = response.text
                    img_urls = extract_image_urls(html)
                    
                    if img_urls:
                        print(f"Found {len(img_urls)} image URLs in the page")
                        for i, url in enumerate(img_urls[:5]):
                            print(f"Image {i+1}: {url}")
                            
                        # Try to download the first image that looks relevant
                        relevant_images = [url for url in img_urls if 'housePhotos' in url]
                        if relevant_images:
                            print(f"\nFound {len(relevant_images)} relevant images")
                            await download_image(relevant_images[0], headers)
                    else:
                        print("No image URLs found in the page")
                else:
                    print(f"Failed to fetch listing page: {response.status_code}")
                    
        except Exception as e:
            print(f"Error with listing page approach: {e}")
    
    except Exception as e:
        print(f"General error: {e}")
        
def extract_image_urls(html):
    """Extract image URLs from HTML content"""
    # Simple regex-free extraction of image sources
    img_tags = []
    img_start = 0
    while True:
        img_start = html.find('<img', img_start)
        if img_start == -1:
            break
        
        src_start = html.find('src="', img_start)
        if src_start == -1:
            img_start += 4
            continue
        
        src_start += 5  # Length of 'src="'
        src_end = html.find('"', src_start)
        if src_end == -1:
            img_start = src_start
            continue
            
        img_url = html[src_start:src_end]
        img_tags.append(img_url)
        img_start = src_end
    
    return img_tags

async def download_image(url, headers):
    """Download and save an image"""
    print(f"Downloading image from: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                print(f"Success! Downloaded image with Content-Type: {content_type}")
                
                # Save the image
                local_path = f"./local_images/found_image.jpg"
                with open(local_path, "wb") as f:
                    f.write(response.content)
                print(f"Saved image to {local_path}")
                
                # Verify it's a valid image
                img = Image.open(BytesIO(response.content))
                print(f"Valid image with size: {img.size}, format: {img.format}")
                return True
            else:
                print(f"Response is not an image. Content-Type: {content_type}")
                return False
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_image_proxy())