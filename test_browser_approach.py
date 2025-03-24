import asyncio
import httpx
import os
from PIL import Image
from io import BytesIO
import json
import re

# Test image path from our examples
TEST_IMAGE_PATH = "soulis/58/778358/H1081-L382842666.jpg"
LOT_REF = "L382842666"  # Extract from the image path

async def analyze_browser_approach():
    """
    Analyze how browsers access Invaluable images by:
    1. Visiting the auction page with browser headers
    2. Extracting image URLs and authentication tokens
    3. Mimicking the exact browser request flow
    """
    print(f"Analyzing browser approach for image: {TEST_IMAGE_PATH}")
    print(f"Lot Reference: {LOT_REF}")
    
    # Setup browser-like headers
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        # Step 1: Visit the auction lot page
        auction_url = f"https://www.invaluable.com/auction-lot/{LOT_REF}"
        print(f"\n1. Visiting auction page: {auction_url}")
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(auction_url, headers=browser_headers, timeout=30.0)
            
            if response.status_code == 200:
                print(f"Successfully loaded auction page ({len(response.text)} bytes)")
                html = response.text
                
                # Save HTML for analysis
                with open("auction_page.html", "w", encoding="utf-8") as f:
                    f.write(html[:10000])  # Save first 10K to avoid huge files
                print("Saved first 10K of HTML to auction_page.html for analysis")
                
                # Step 2: Extract image URLs
                print("\n2. Extracting image URLs from page")
                image_urls = extract_image_urls(html)
                
                if image_urls:
                    print(f"Found {len(image_urls)} image URLs on the page")
                    for i, url in enumerate(image_urls[:5]):
                        print(f"  Image {i+1}: {url}")
                    
                    # Step 3: Look for relevant images
                    relevant_images = [url for url in image_urls if 'housePhotos' in url or LOT_REF.lower() in url.lower()]
                    
                    if relevant_images:
                        print(f"\nFound {len(relevant_images)} relevant images")
                        for i, url in enumerate(relevant_images[:3]):
                            print(f"  Relevant Image {i+1}: {url}")
                        
                        # Step 4: Extract any authentication tokens
                        print("\n3. Looking for authentication tokens or cookies")
                        cookies = response.cookies
                        if cookies:
                            print("Cookies found:")
                            for name, value in cookies.items():
                                print(f"  {name}: {value}")
                        
                        cf_tokens = extract_cloudflare_tokens(html)
                        if cf_tokens:
                            print("Cloudflare tokens found:")
                            for key, value in cf_tokens.items():
                                print(f"  {key}: {value}")
                        
                        # Step 5: Try to download with cookies and tokens
                        print("\n4. Attempting to download images with cookies/tokens")
                        success = False
                        
                        for img_url in relevant_images[:3]:
                            success = await try_download_with_auth(img_url, cookies, browser_headers, f"image_{relevant_images.index(img_url)+1}.jpg")
                            if success:
                                break
                        
                        if not success:
                            print("\nAll direct attempts failed. Trying advanced techniques...")
                            
                            # Step 6: Look for JavaScript image loading techniques
                            print("\n5. Analyzing JavaScript for image loading techniques")
                            js_img_urls = extract_js_image_urls(html)
                            
                            if js_img_urls:
                                print(f"Found {len(js_img_urls)} JS-loaded image URLs")
                                for i, url in enumerate(js_img_urls[:3]):
                                    print(f"  JS Image {i+1}: {url}")
                                
                                # Try downloading the JS-loaded images
                                for img_url in js_img_urls[:3]:
                                    await try_download_with_auth(img_url, cookies, browser_headers, f"js_image_{js_img_urls.index(img_url)+1}.jpg")
                    else:
                        print("No relevant images found on the page")
                else:
                    print("No image URLs found on the page")
            else:
                print(f"Failed to load auction page. Status: {response.status_code}")
                if response.status_code == 403:
                    print("Access is blocked by Cloudflare protection")
                    
                    # Step 7: Try a direct API request for the lot data
                    print("\n6. Trying a direct API request for lot data")
                    await try_api_request(LOT_REF, browser_headers)
    
    except Exception as e:
        print(f"Error in analysis: {e}")

def extract_image_urls(html):
    """Extract image URLs from HTML content"""
    img_tags = []
    img_start = 0
    
    # Extract standard img tags
    while True:
        img_start = html.find('<img', img_start)
        if img_start == -1:
            break
        
        # Look for src or data-src attributes
        for attr in ['src="', 'data-src="', 'data-original="']:
            src_start = html.find(attr, img_start)
            if src_start != -1 and (html.find('>', img_start) == -1 or src_start < html.find('>', img_start)):
                src_start += len(attr)
                src_end = html.find('"', src_start)
                if src_end != -1:
                    img_url = html[src_start:src_end]
                    if img_url and not img_url.startswith('data:'):
                        img_tags.append(img_url)
                break
        
        img_start = html.find('>', img_start) + 1
        if img_start <= 0:
            break
    
    # Also look for background images
    bg_start = 0
    while True:
        bg_start = html.find('background-image', bg_start)
        if bg_start == -1:
            break
        
        url_start = html.find('url(', bg_start)
        if url_start != -1:
            url_start += 4
            url_end = html.find(')', url_start)
            if url_end != -1:
                bg_url = html[url_start:url_end].strip('\'"')
                if bg_url and not bg_url.startswith('data:'):
                    img_tags.append(bg_url)
        
        bg_start = url_end if url_end != -1 else bg_start + 1
    
    return img_tags

def extract_js_image_urls(html):
    """Extract image URLs from JavaScript in the HTML"""
    js_urls = []
    
    # Look for image URLs in JavaScript array assignments
    array_patterns = [
        r'images\s*[:=]\s*\[(.*?)\]',
        r'photos\s*[:=]\s*\[(.*?)\]',
        r'imageUrls\s*[:=]\s*\[(.*?)\]'
    ]
    
    for pattern in array_patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        for match in matches:
            # Extract quoted strings from the array
            urls = re.findall(r'["\']([^"\']+?(?:jpg|jpeg|png|gif))["\']', match)
            js_urls.extend(urls)
    
    # Look for URL assignments
    url_assignments = re.findall(r'(?:url|src|imgSrc)\s*[:=]\s*["\']([^"\']+?(?:jpg|jpeg|png|gif))["\']', html)
    js_urls.extend(url_assignments)
    
    # Look for API responses that might contain image URLs
    data_blocks = re.findall(r'JSON\.parse\(["\'](.+?)["\']\)', html)
    for block in data_blocks:
        try:
            # Replace escaped quotes for valid JSON
            cleaned = block.replace('\\"', '"').replace('\\\\', '\\')
            data = json.loads(cleaned)
            
            # Recursively search for image URLs in the data
            js_urls.extend(find_image_urls_in_data(data))
        except:
            pass
    
    return js_urls

def find_image_urls_in_data(data):
    """Recursively search for image URLs in nested data structures"""
    urls = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                if '/' in value and not value.startswith('data:'):
                    urls.append(value)
            elif isinstance(value, (dict, list)):
                urls.extend(find_image_urls_in_data(value))
    
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                urls.extend(find_image_urls_in_data(item))
            elif isinstance(item, str) and any(ext in item.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                if '/' in item and not item.startswith('data:'):
                    urls.append(item)
    
    return urls

def extract_cloudflare_tokens(html):
    """Extract Cloudflare protection tokens from the page"""
    tokens = {}
    
    # Look for Cloudflare token
    cf_token_match = re.search(r'<input[^>]*name="cf_clearance"[^>]*value="([^"]*)"', html)
    if cf_token_match:
        tokens['cf_clearance'] = cf_token_match.group(1)
    
    # Look for other security tokens
    for token_name in ['security', 'auth', 'token', 'csrf']:
        token_match = re.search(rf'<input[^>]*name="[^"]*{token_name}[^"]*"[^>]*value="([^"]*)"', html, re.IGNORECASE)
        if token_match:
            tokens[token_name] = token_match.group(1)
    
    return tokens

async def try_download_with_auth(url, cookies, headers, save_as):
    """Try to download an image with authentication cookies and referer"""
    if not url.startswith('http'):
        if url.startswith('//'):
            url = 'https:' + url
        else:
            url = 'https://www.invaluable.com' + url if url.startswith('/') else 'https://www.invaluable.com/' + url
    
    print(f"Attempting to download: {url}")
    
    # Create directory if it doesn't exist
    os.makedirs("./local_images", exist_ok=True)
    save_path = os.path.join('./local_images', save_as)
    
    # Add referer matching the image URL domain
    download_headers = headers.copy()
    download_headers['Referer'] = 'https://www.invaluable.com/'
    download_headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    
    try:
        async with httpx.AsyncClient(cookies=cookies, follow_redirects=True) as client:
            response = await client.get(url, headers=download_headers, timeout=30.0)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                # Save the image
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✓ Successfully downloaded {url} ({len(response.content)} bytes)")
                print(f"  Saved to: {save_path}")
                
                # Verify it's a valid image
                try:
                    img = Image.open(BytesIO(response.content))
                    print(f"  Image size: {img.size}, format: {img.format}")
                    return True
                except Exception as e:
                    print(f"  Invalid image: {e}")
                    return False
            else:
                print(f"✗ Response not an image. Content-Type: {content_type}")
                return False
    
    except Exception as e:
        print(f"✗ Error downloading {url}: {e}")
        return False

async def try_api_request(lot_ref, headers):
    """Try a direct API request to get lot data"""
    api_url = f"https://www.invaluable.com/v2/api/lot/{lot_ref}"
    print(f"Trying API request: {api_url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(api_url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("API request successful!")
                    
                    # Look for image URLs in the API response
                    with open("api_response.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print("Saved API response to api_response.json")
                    
                    image_urls = find_image_urls_in_data(data)
                    if image_urls:
                        print(f"Found {len(image_urls)} image URLs in API response:")
                        for i, url in enumerate(image_urls[:5]):
                            print(f"  API Image {i+1}: {url}")
                        
                        # Try downloading the first image
                        await try_download_with_auth(image_urls[0], {}, headers, "api_image_1.jpg")
                    else:
                        print("No image URLs found in API response")
                except:
                    print("Failed to parse API response as JSON")
            else:
                print(f"API request failed: {response.status_code}")
    
    except Exception as e:
        print(f"Error making API request: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_browser_approach())