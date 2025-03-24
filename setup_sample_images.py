import os
import json
from PIL import Image, ImageDraw, ImageFont
import random
import shutil
from datetime import datetime

def create_sample_image(width, height, text, output_path):
    """Create a sample image with the given text"""
    # Create a blank image with a random background color
    r, g, b = [random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)]
    img = Image.new('RGB', (width, height), color=(r, g, b))
    draw = ImageDraw.Draw(img)
    
    # Add a border
    border_width = 10
    draw.rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        outline=(r - 40, g - 40, b - 40),
        width=2
    )
    
    # Add text
    draw.text((width // 2, height // 3), text, fill=(0, 0, 0), anchor="mm")
    draw.text((width // 2, height // 2), "Sample Image", fill=(0, 0, 0), anchor="mm")
    draw.text((width // 2, height * 2 // 3), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fill=(0, 0, 0), anchor="mm")
    
    # Save the image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'JPEG', quality=85)
    print(f"Created sample image: {output_path}")
    return output_path

def process_example_json():
    """Process the example_json.json file and create sample images"""
    # Load the example JSON file
    try:
        with open('example_json.json', 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading example_json.json: {e}")
        return
    
    print("Processing example JSON to create sample images...")
    
    # Create the base directory for sample images
    base_dir = './local_images'
    if os.path.exists(base_dir):
        # Automatically clean up existing directory
        print(f"Directory {base_dir} already exists. Cleaning up...")
        try:
            # Instead of deleting, just ensure the directories exist
            print(f"Ensuring directories exist in {base_dir}")
        except Exception as e:
            print(f"Error with directory: {e}")
    else:
        os.makedirs(base_dir)
    
    # Process each hit in the results
    total_processed = 0
    total_hits = sum(len(result.get('hits', [])) for result in data.get('results', []))
    max_images = min(total_hits, 20)  # Limit to 20 images to avoid creating too many files
    
    print(f"Found {total_hits} items in the example JSON. Creating up to {max_images} sample images...")
    
    for result in data.get('results', []):
        for hit in result.get('hits', []):
            # Get the photo path
            photo_path = hit.get('photoPath')
            if not photo_path:
                continue
            
            # Get auction details for the image text
            house_name = hit.get('houseName', 'Unknown Auction House')
            lot_title = hit.get('lotTitle', 'Unknown Lot')
            lot_ref = hit.get('lotRef', 'Unknown Reference')
            
            # Create the directory structure
            image_dir = os.path.join(base_dir, house_name.replace(' ', '_'))
            os.makedirs(image_dir, exist_ok=True)
            
            # Create the output path - directly use the photo_path
            output_path = os.path.join(base_dir, photo_path)
            
            # Create the sample image
            text = f"{house_name}\n{lot_title}\nRef: {lot_ref}"
            create_sample_image(800, 600, text, output_path)
            
            total_processed += 1
            if total_processed >= max_images:
                break
        
        if total_processed >= max_images:
            break
    
    print(f"\nCreated {total_processed} sample images in {base_dir}")
    print("\nYou can now use these images for testing:")
    print("1. The images are organized by the original photo paths from the JSON")
    print("2. Each image contains the auction house, lot title, and reference")
    print(f"3. These images can be found in the {base_dir} directory")

if __name__ == "__main__":
    process_example_json()