import asyncio
import logging
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Example photo paths to test
TEST_PHOTO_PATHS = [
    "stairgalleries/1/131/17879596_1.jpg",
    "lempertz/2/128/S171V0810_1.jpg", 
    "chalkwell/1/112/15566307_1.jpg",
    "aspireauctions/1/208/28732865_1.jpg",
    "boisgirard/1/85/12028873_1.jpg"
]

BASE_URL = "https://image.invaluable.com/housePhotos/"

# Store downloaded images
os.makedirs("./local_images", exist_ok=True)

# Browser-like headers
BROWSER_HEADERS = {
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

@app.get("/")
async def home():
    """Home endpoint with links to test examples"""
    html_links = []
    for path in TEST_PHOTO_PATHS:
        filename = os.path.basename(path)
        html_links.append(f'<li><a href="/proxy/{path}" target="_blank">{filename}</a></li>')
    
    return {
        "message": "Image Proxy Server",
        "test_images_html": f"""
        <html>
            <head><title>Test Image Links</title></head>
            <body>
                <h1>Test Images</h1>
                <p>Click on links to test the proxy:</p>
                <ul>{''.join(html_links)}</ul>
            </body>
        </html>
        """
    }

@app.get("/proxy/{path:path}")
async def proxy_image(path: str, request: Request):
    """Proxy endpoint that forwards requests to Invaluable with proper headers"""
    logger.info(f"Received request for: {path}")
    
    # Full URL to the image
    url = f"{BASE_URL}{path}"
    logger.info(f"Proxying request to: {url}")
    
    # Forward all client headers plus our browser headers
    combined_headers = dict(request.headers)
    for key, value in BROWSER_HEADERS.items():
        if key.lower() not in [k.lower() for k in combined_headers.keys()]:
            combined_headers[key] = value
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                headers=combined_headers,
                timeout=30.0,
                follow_redirects=True
            )
            
            # Log the response
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content type: {response.headers.get('content-type')}")
            
            # Check if the response is an image
            content_type = response.headers.get("content-type", "")
            if response.status_code == 200 and "image" in content_type:
                # Save to local storage
                local_path = f"./local_images/proxy_{os.path.basename(path)}"
                with open(local_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully saved image to {local_path}")
                
                # Return the image response
                return StreamingResponse(
                    content=iter([response.content]),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=content_type
                )
            else:
                # If not a successful image response, try alternative URLs
                for alt_base in ["https://media.invaluable.com/housePhotos/", 
                                "https://www.invaluable.com/housePhotos/",
                                "https://cdn.invaluable.com/housePhotos/"]:
                    alt_url = f"{alt_base}{path}"
                    logger.info(f"Trying alternative URL: {alt_url}")
                    
                    try:
                        alt_response = await client.get(
                            alt_url, 
                            headers=combined_headers,
                            timeout=30.0,
                            follow_redirects=True
                        )
                        
                        alt_content_type = alt_response.headers.get("content-type", "")
                        if alt_response.status_code == 200 and "image" in alt_content_type:
                            # Save to local storage
                            local_path = f"./local_images/proxy_alt_{os.path.basename(path)}"
                            with open(local_path, "wb") as f:
                                f.write(alt_response.content)
                            logger.info(f"Successfully saved image from alternative URL to {local_path}")
                            
                            # Return the image response
                            return StreamingResponse(
                                content=iter([alt_response.content]),
                                status_code=alt_response.status_code,
                                headers=dict(alt_response.headers),
                                media_type=alt_content_type
                            )
                    except Exception as e:
                        logger.error(f"Error with alternative URL {alt_url}: {e}")
                
                # If all attempts fail, generate a placeholder image
                from PIL import Image, ImageDraw
                from io import BytesIO
                
                # Create a placeholder image
                img = Image.new('RGB', (800, 600), color='white')
                d = ImageDraw.Draw(img)
                d.text((100, 250), f"Image not available\n{path}", fill='black')
                
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                buffer.seek(0)
                placeholder_data = buffer.getvalue()
                
                # Save placeholder
                local_path = f"./local_images/proxy_placeholder_{os.path.basename(path)}"
                with open(local_path, "wb") as f:
                    f.write(placeholder_data)
                logger.info(f"Returning placeholder image saved to {local_path}")
                
                # Return placeholder
                return StreamingResponse(
                    content=iter([placeholder_data]),
                    media_type="image/jpeg"
                )
    
    except Exception as e:
        logger.error(f"Error proxying request to {url}: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Starting proxy server on http://localhost:8000")
    logger.info("Open your browser to http://localhost:8000 to see test images")
    uvicorn.run(app, host="0.0.0.0", port=8000)