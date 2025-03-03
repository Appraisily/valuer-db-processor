from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import datetime

class HighlightResult(BaseModel):
    """Model representing the highlight result data"""
    more_text: Optional[Dict[str, Any]] = None
    lot_title: Optional[Dict[str, Any]] = None
    lot_description: Optional[Dict[str, Any]] = None

class RankingInfo(BaseModel):
    """Model representing the ranking information"""
    nb_typos: Optional[int] = None
    first_matched_word: Optional[int] = None
    proximity_distance: Optional[int] = None
    user_score: Optional[int] = None
    geo_distance: Optional[int] = None
    geo_precision: Optional[int] = None
    nb_exact_words: Optional[int] = None
    words: Optional[int] = None
    filters: Optional[int] = None

class AuctionLotInput(BaseModel):
    """
    Input model for auction lot data as received from JSON
    """
    lotNumber: str
    lotRef: str
    lotTitle: str
    description: Optional[str] = None
    
    houseName: str
    saleType: str
    dateTimeLocal: str
    dateTimeUTCUnix: int
    
    priceResult: float
    currencyCode: str
    currencySymbol: str
    
    photoPath: str
    
    # Additional fields will be captured in model.__dict__
    
    class Config:
        populate_by_name = True
        extra = "allow"  # Allow extra fields that will be stored in the raw_data JSON

class AuctionLotResponse(BaseModel):
    """
    Response model for auction lot data after processing
    """
    id: str
    lotRef: str
    lotNumber: str
    lotTitle: str
    description: Optional[str] = None
    
    houseName: str
    saleType: str
    saleDate: str
    
    priceRealized: float
    currencyCode: str
    currencySymbol: str
    
    photoPath: str
    
    createdAt: str
    updatedAt: str
    
    # Store any additional data from the original input
    rawData: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        } 