import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import time
from flask import Flask, request, send_file, render_template_string

# Create Flask app for local proxy testing
app = Flask(__name__)

# Sample HTML for testing image loading
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Invaluable Image Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .image-container { margin-bottom: 20px; }
        img { max-width: 100%; border: 1px solid #ccc; }
        .image-info { margin-top: 5px; font-size: 12px; color: #666; }
        h2 { margin-top: 30px; }
    </style>
</head>
<body>
    <h1>Invaluable Image Test</h1>
    
    <h2>Direct CDN Links</h2>
    <div class="image-container">
        <p>Testing direct image from image.invaluable.com:</p>
        <img src="https://image.invaluable.com/housePhotos/{{image_path}}" 
             onerror="this.onerror=null; this.src='/fallback?url=' + encodeURIComponent(this.src); this.style.border='1px solid red';"
             alt="Test Image">
        <div class="image-info">URL: https://image.invaluable.com/housePhotos/{{image_path}}</div>
    </div>
    
    <div class="image-container">
        <p>Testing alternate CDN from media.invaluable.com:</p>
        <img src="https://media.invaluable.com/housePhotos/{{image_path}}" 
             onerror="this.onerror=null; this.src='/fallback?url=' + encodeURIComponent(this.src); this.style.border='1px solid red';"
             alt="Test Image">
        <div class="image-info">URL: https://media.invaluable.com/housePhotos/{{image_path}}</div>
    </div>
    
    <div class="image-container">
        <p>Testing alternate CDN from www.invaluable.com:</p>
        <img src="https://www.invaluable.com/housePhotos/{{image_path}}" 
             onerror="this.onerror=null; this.src='/fallback?url=' + encodeURIComponent(this.src); this.style.border='1px solid red';"
             alt="Test Image">
        <div class="image-info">URL: https://www.invaluable.com/housePhotos/{{image_path}}</div>
    </div>
    
    <h2>Proxied URLs (through this server)</h2>
    <div class="image-container">
        <p>Testing proxied image from image.invaluable.com:</p>
        <img src="/proxy?url=https://image.invaluable.com/housePhotos/{{image_path}}" alt="Proxied Test Image">
        <div class="image-info">URL: /proxy?url=https://image.invaluable.com/housePhotos/{{image_path}}</div>
    </div>
    
    <h2>Fallback Generated Image</h2>
    <div class="image-container">
        <p>Fallback generated image with text:</p>
        <img src="/generate?text={{image_path}}" alt="Generated Test Image">
        <div class="image-info">URL: /generate?text={{image_path}}</div>
    </div>
</body>
</html>
"""

# Current image test path
IMAGE_PATH = "soulis/58/778358/H1081-L382842666.jpg"

@app.route('/')
def index():
    """Home page with test images"""
    return render_template_string(HTML_TEMPLATE, image_path=IMAGE_PATH)

@app.route('/proxy')
def proxy():
    """Proxy image requests to bypass CORS"""
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    
    try:
        # Browser-like headers for the request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.invaluable.com/",
            "Cache-Control": "no-cache"
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        # If it's an image, forward it
        if 'image' in response.headers.get('Content-Type', ''):
            return send_file(
                BytesIO(response.content),
                mimetype=response.headers.get('Content-Type'),
                download_name=url.split('/')[-1]
            )
        else:
            return f"Response not an image: {response.headers.get('Content-Type')}", 400
    
    except Exception as e:
        return f"Error proxying image: {str(e)}", 500

@app.route('/fallback')
def fallback():
    """Fallback for failed image loads - creates a local proxy attempt"""
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    
    try:
        # Add a timestamp to avoid browser caching
        proxy_url = f"/proxy?url={url}&t={int(time.time())}"
        html = f"""
        <html>
        <body>
            <p>Original image failed to load. Trying through proxy...</p>
            <img src="{proxy_url}" style="max-width: 100%" alt="Proxy attempt">
            <p>If this fails too, the image may be protected or non-existent.</p>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"Error creating fallback: {str(e)}", 500

@app.route('/generate')
def generate_image():
    """Generate a sample image with text"""
    text = request.args.get('text', 'No text provided')
    
    try:
        # Create a blank image
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        
        # Add text
        d.text((50, 50), "Image not available", fill=(0, 0, 0))
        d.text((50, 100), text, fill=(0, 0, 0))
        d.text((50, 150), f"Generated at: {time.ctime()}", fill=(0, 0, 0))
        
        # Save to BytesIO
        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        return f"Error generating image: {str(e)}", 500

if __name__ == '__main__':
    # Make sure local_images directory exists
    os.makedirs('./local_images', exist_ok=True)
    
    # Run the Flask app
    print(f"Testing with image: {IMAGE_PATH}")
    print("Starting local test server on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)