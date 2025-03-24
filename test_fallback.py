import asyncio
from src.services.image_service import download_image, optimize_image, save_to_local
from src.models.auction_lot import AuctionLotInput

async def test_image_download_with_fallback():
    """Test the image download with fallback to placeholder"""
    
    # Create a test lot
    test_lot = AuctionLotInput(
        lotNumber="102",
        lotRef="TEST-102",
        lotTitle="Test Auction Lot",
        houseName="Test Auction House",
        saleType="Live",
        dateTimeLocal="2024-09-21 11:00:00",
        dateTimeUTCUnix=1726934400,
        priceResult=850,
        currencyCode="USD",
        currencySymbol="$",
        photoPath="soulis/58/778358/H1081-L382842666.jpg"
    )
    
    # Try to download the image
    print(f"Attempting to download image: {test_lot.photoPath}")
    image_data = await download_image(test_lot.photoPath)
    
    if image_data:
        print(f"Successfully downloaded image, size: {len(image_data)} bytes")
        
        # Optimize the image
        optimized_data = optimize_image(image_data)
        if optimized_data:
            print(f"Optimized image, new size: {len(optimized_data)} bytes")
            image_data = optimized_data
        
        # Save locally
        local_path = f"{test_lot.houseName}/{test_lot.lotRef}/test_image.jpg"
        saved_path = save_to_local(image_data, local_path, test_lot)
        
        if saved_path:
            print(f"Image saved to: {saved_path}")
        else:
            print("Failed to save image")
    else:
        print("Failed to download image")

if __name__ == "__main__":
    asyncio.run(test_image_download_with_fallback())