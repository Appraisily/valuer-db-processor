import asyncio
import os
import json
from src.services.image_service import download_image, process_single_image
from src.models.auction_lot import AuctionLotInput

async def test_local_image_processing():
    """Test that local images are used when available in development mode"""
    
    print("Testing local image processing...")
    
    # Load first few items from example_json.json
    with open('example_json.json', 'r') as f:
        data = json.load(f)
    
    hits = []
    for result in data.get('results', []):
        hits.extend(result.get('hits', []))
    
    # Test with the first 5 items
    test_items = hits[:5]
    
    print(f"Testing with {len(test_items)} auction lots from example_json.json")
    
    for i, item in enumerate(test_items):
        # Create an AuctionLotInput from the item data
        lot_input = AuctionLotInput(
            lotNumber=item.get('lotNumber'),
            lotRef=item.get('lotRef'),
            lotTitle=item.get('lotTitle'),
            description=item.get('_highlightResult', {}).get('lotDescription', {}).get('value') if '_highlightResult' in item else None,
            houseName=item.get('houseName'),
            saleType=item.get('saleType'),
            dateTimeLocal=item.get('dateTimeLocal'),
            dateTimeUTCUnix=item.get('dateTimeUTCUnix'),
            priceResult=item.get('priceResult'),
            currencyCode=item.get('currencyCode'),
            currencySymbol=item.get('currencySymbol'),
            photoPath=item.get('photoPath')
        )
        
        print(f"\nTesting item {i+1}: {lot_input.lotRef}")
        print(f"Photo path: {lot_input.photoPath}")
        
        # Check if local sample exists
        local_path = f"./local_images/{lot_input.photoPath}"
        if os.path.exists(local_path):
            print(f"✓ Local sample exists at: {local_path}")
        else:
            print(f"✗ Local sample does not exist at: {local_path}")
        
        # Test downloading the image
        print("Testing download_image()...")
        image_data = await download_image(lot_input.photoPath)
        
        if image_data:
            print(f"✓ Successfully downloaded image: {len(image_data)} bytes")
            
            # Save to a test location for verification
            test_output = f"./local_images/test_output_{i+1}.jpg"
            with open(test_output, 'wb') as f:
                f.write(image_data)
            print(f"  Saved to: {test_output}")
        else:
            print("✗ Failed to download image")
        
        # Test full image processing
        print("Testing process_single_image()...")
        storage_path = await process_single_image(lot_input)
        
        if storage_path:
            print(f"✓ Successfully processed image: {storage_path}")
        else:
            print("✗ Failed to process image")
        
        print("-" * 50)
    
    print("\nImage processing test completed!")

if __name__ == "__main__":
    asyncio.run(test_local_image_processing())