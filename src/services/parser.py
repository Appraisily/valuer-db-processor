import logging
from typing import Dict, Any, List
from src.models.auction_lot import AuctionLotInput

logger = logging.getLogger(__name__)

def parse_json_data(data: Dict[str, Any]) -> List[AuctionLotInput]:
    """
    Parse the JSON data into a list of AuctionLotInput objects
    
    Args:
        data: Dict containing the JSON data structure
        
    Returns:
        List of AuctionLotInput objects
    """
    auction_lots = []
    
    try:
        # Extract the results array from the JSON
        results = data.get("results", [])
        
        # Process each result which contains hits
        for result in results:
            hits = result.get("hits", [])
            
            # Process each hit (auction lot)
            for hit in hits:
                try:
                    # Create AuctionLotInput object from hit data
                    auction_lot = AuctionLotInput(**hit)
                    auction_lots.append(auction_lot)
                except Exception as e:
                    logger.error(f"Error parsing hit: {str(e)}", exc_info=True)
                    # Continue processing other hits even if one fails
                    continue
    
    except Exception as e:
        logger.error(f"Error parsing JSON data: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to parse JSON data: {str(e)}")
    
    return auction_lots

def validate_json_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that the JSON has the expected structure
    
    Args:
        data: Dict containing the JSON data structure
        
    Returns:
        Boolean indicating if the structure is valid
    """
    # Check if required fields exist
    if "results" not in data:
        logger.error("Missing 'results' field in JSON data")
        return False
    
    # Check if results is an array
    if not isinstance(data["results"], list):
        logger.error("'results' field is not an array")
        return False
    
    # If there are no results, that's not necessarily an error
    if not data["results"]:
        logger.warning("'results' array is empty")
        return True
    
    # Check the first result to see if it has hits
    first_result = data["results"][0]
    if "hits" not in first_result:
        logger.error("Missing 'hits' field in first result")
        return False
    
    return True 