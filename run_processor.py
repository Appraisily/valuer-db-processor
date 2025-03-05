#!/usr/bin/env python
"""
Simple script to process the example JSON file
"""
import json
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("processor")

def process_json_file(file_path):
    """Process the JSON file and extract auction data"""
    try:
        # Read JSON data with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if the file has the expected structure
        if "results" not in data or not isinstance(data["results"], list):
            logger.error("Invalid JSON structure - missing 'results' array")
            return
        
        # Extract and process auction lots
        all_lots = []
        for result in data["results"]:
            if "hits" not in result or not isinstance(result["hits"], list):
                logger.warning("Result missing 'hits' array")
                continue
            
            for hit in result["hits"]:
                # Extract essential fields
                lot = {
                    "lotRef": hit.get("lotRef", ""),
                    "lotNumber": hit.get("lotNumber", ""),
                    "lotTitle": hit.get("lotTitle", ""),
                    "houseName": hit.get("houseName", ""),
                    "saleType": hit.get("saleType", ""),
                    "priceResult": hit.get("priceResult", 0),
                    "photoPath": hit.get("photoPath", ""),
                    "imageUrl": f"https://image.invaluable.com/housePhotos/{hit.get('photoPath', '')}" if hit.get("photoPath") else ""
                }
                all_lots.append(lot)
        
        # Save processed data to a CSV-like format
        output_file = Path(os.path.dirname(file_path)) / "processed_lots.txt"
        with open(output_file, "w") as f:
            # Write header
            f.write("lotRef|lotNumber|lotTitle|houseName|photoPath|imageUrl\n")
            
            # Write data
            for lot in all_lots:
                f.write(f"{lot['lotRef']}|{lot['lotNumber']}|{lot['lotTitle']}|{lot['houseName']}|{lot['photoPath']}|{lot['imageUrl']}\n")
        
        # Print summary
        logger.info(f"Processed {len(all_lots)} auction lots")
        logger.info(f"Output saved to {output_file}")
        
        # Print the first few image URLs for verification
        logger.info("Sample image URLs:")
        for i, lot in enumerate(all_lots[:5]):
            logger.info(f"  {i+1}. {lot['imageUrl']}")
        
    except Exception as e:
        logger.error(f"Error processing JSON file: {str(e)}")
        raise

def main():
    """Main function"""
    # Path to the example JSON file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(current_dir, "example_json.json")
    
    if not os.path.exists(json_file):
        logger.error(f"JSON file not found: {json_file}")
        return
    
    # Process the JSON file
    process_json_file(json_file)

if __name__ == "__main__":
    main()