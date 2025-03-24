import asyncio
import logging
import os
import subprocess
import socket
import httpx
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

# Base domain
BASE_DOMAIN = "image.invaluable.com"

def find_origin_ip():
    """Attempt to find the origin IP address behind Cloudflare"""
    logger.info(f"Attempting to find origin IP for {BASE_DOMAIN}")
    
    try:
        # First try using socket to resolve the domain
        ip_address = socket.gethostbyname(BASE_DOMAIN)
        logger.info(f"Resolved {BASE_DOMAIN} to IP: {ip_address}")
        
        # This might be a Cloudflare IP, but we'll try it anyway
        return ip_address
    except Exception as e:
        logger.error(f"Failed to resolve domain using socket: {e}")
    
    try:
        # Try using dig to find more information (works on Linux/Unix)
        result = subprocess.run(
            ["dig", BASE_DOMAIN, "+short"], 
            capture_output=True, 
            text=True
        )
        ip_addresses = result.stdout.strip().split('\n')
        if ip_addresses:
            logger.info(f"Found IPs via dig: {ip_addresses}")
            return ip_addresses[0]  # Use the first IP
    except Exception as e:
        logger.error(f"Failed to run dig command: {e}")
    
    try:
        # Try using nslookup as a fallback
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
            logger.info(f"Found IPs via nslookup: {ip_addresses}")
            return ip_addresses[0]  # Use the first IP
    except Exception as e:
        logger.error(f"Failed to run nslookup command: {e}")
    
    logger.warning("Could not determine origin IP, using domain directly")
    return BASE_DOMAIN

async def test_direct_ip_download(photo_path, ip_address=None):
    """Test downloading by accessing the origin IP directly"""
    if not ip_address:
        ip_address = find_origin_ip()
    
    # Create output directory
    os.makedirs("./local_images", exist_ok=True)
    
    # Construct URL with IP address but keep Host header with domain name
    url = f"http://{ip_address}/housePhotos/{photo_path}"
    logger.info(f"Attempting to download from IP: {url}")
    
    # Enhanced browser-like headers
    headers = {
        "Host": BASE_DOMAIN,  # Critical: set the Host header to the original domain
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
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                # Save the image
                image_filename = f"./local_images/ip_approach_{os.path.basename(photo_path)}"
                with open(image_filename, "wb") as f:
                    f.write(response.content)
                logger.info(f"✅ Successfully downloaded image via IP approach: {image_filename}")
                
                # Display image dimensions for verification
                try:
                    img = Image.open(BytesIO(response.content))
                    logger.info(f"Image dimensions: {img.width}x{img.height}, format: {img.format}")
                except Exception as e:
                    logger.warning(f"Could not parse image details: {e}")
                
                return True, response.content
            else:
                logger.warning(f"❌ Response is not an image. Content type: {content_type}")
                logger.info(f"Response text: {response.text[:200]}...")  # Show beginning of response
                return False, None
                
    except Exception as e:
        logger.error(f"❌ Failed with IP approach: {e}")
        return False, None

async def test_https_ip_download(photo_path, ip_address=None):
    """Test downloading using HTTPS with direct IP but Host header"""
    if not ip_address:
        ip_address = find_origin_ip()
    
    # Create output directory
    os.makedirs("./local_images", exist_ok=True)
    
    # Construct URL with IP address over HTTPS
    url = f"https://{ip_address}/housePhotos/{photo_path}"
    logger.info(f"Attempting to download from IP over HTTPS: {url}")
    
    # Enhanced browser-like headers
    headers = {
        "Host": BASE_DOMAIN,  # Critical: set the Host header to the original domain
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
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    
    try:
        async with httpx.AsyncClient(verify=False) as client:  # Disabling SSL verification since we're using IP
            response = await client.get(
                url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            response.raise_for_status()
            
            # Check if it's an image
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                # Save the image
                image_filename = f"./local_images/https_ip_approach_{os.path.basename(photo_path)}"
                with open(image_filename, "wb") as f:
                    f.write(response.content)
                logger.info(f"✅ Successfully downloaded image via HTTPS IP approach: {image_filename}")
                return True, response.content
            else:
                logger.warning(f"❌ HTTPS IP response is not an image. Content type: {content_type}")
                return False, None
                
    except Exception as e:
        logger.error(f"❌ Failed with HTTPS IP approach: {e}")
        return False, None

async def test_direct_with_host_injection(photo_path):
    """Test downloading by using the standard URL but modifying the Host header"""
    
    # Create output directory
    os.makedirs("./local_images", exist_ok=True)
    
    # Use normal URL
    url = f"https://{BASE_DOMAIN}/housePhotos/{photo_path}"
    logger.info(f"Attempting host header injection approach: {url}")
    
    # Try with multiple possible host values
    host_values = [
        "cdn.invaluable.com",
        "media.invaluable.com", 
        "origin-images.invaluable.com",
        "images.invaluable.com"
    ]
    
    for host in host_values:
        logger.info(f"Trying with Host: {host}")
        
        # Headers with different Host
        headers = {
            "Host": host,
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
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    timeout=30.0, 
                    follow_redirects=True,
                    headers=headers
                )
                response.raise_for_status()
                
                # Check if it's an image
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    # Save the image
                    image_filename = f"./local_images/host_injection_{host}_{os.path.basename(photo_path)}"
                    with open(image_filename, "wb") as f:
                        f.write(response.content)
                    logger.info(f"✅ Successfully downloaded image via host injection with {host}: {image_filename}")
                    return True, response.content
                else:
                    logger.warning(f"❌ Host injection response with {host} is not an image. Content type: {content_type}")
                    
        except Exception as e:
            logger.error(f"❌ Failed with host injection using {host}: {e}")
    
    return False, None

async def main():
    """Test all approaches with multiple examples"""
    logger.info("=== Starting Origin IP Bypass Tests ===")
    
    # Find origin IP once (might be a Cloudflare IP but worth trying)
    ip_address = find_origin_ip()
    logger.info(f"Using IP address: {ip_address}")
    
    results = []
    for photo_path in TEST_PHOTO_PATHS:
        logger.info(f"\n=== Testing image: {photo_path} ===")
        
        # Try all methods
        ip_success, ip_data = await test_direct_ip_download(photo_path, ip_address)
        if ip_success:
            results.append((photo_path, "IP_SUCCESS", ip_data))
            continue
            
        https_ip_success, https_ip_data = await test_https_ip_download(photo_path, ip_address)
        if https_ip_success:
            results.append((photo_path, "HTTPS_IP_SUCCESS", https_ip_data))
            continue
            
        host_success, host_data = await test_direct_with_host_injection(photo_path)
        if host_success:
            results.append((photo_path, "HOST_INJECTION_SUCCESS", host_data))
            continue
            
        # If all methods failed
        results.append((photo_path, "ALL_FAILED", None))
    
    # Print summary
    logger.info("\n=== TEST RESULTS SUMMARY ===")
    for photo_path, status, _ in results:
        logger.info(f"{status}: {photo_path}")
    
    # Count different types of results
    ip_successes = sum(1 for _, status, _ in results if status == "IP_SUCCESS")
    https_ip_successes = sum(1 for _, status, _ in results if status == "HTTPS_IP_SUCCESS")
    host_injection_successes = sum(1 for _, status, _ in results if status == "HOST_INJECTION_SUCCESS")
    failures = sum(1 for _, status, _ in results if status == "ALL_FAILED")
    
    total = len(results)
    logger.info(f"\nFINAL SUMMARY:")
    logger.info(f"Direct IP success: {ip_successes}/{total} ({ip_successes/total*100:.1f}%)")
    logger.info(f"HTTPS IP success: {https_ip_successes}/{total} ({https_ip_successes/total*100:.1f}%)")
    logger.info(f"Host injection success: {host_injection_successes}/{total} ({host_injection_successes/total*100:.1f}%)")
    logger.info(f"Complete failures: {failures}/{total} ({failures/total*100:.1f}%)")
    logger.info(f"Overall success rate: {(ip_successes + https_ip_successes + host_injection_successes)/total*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())