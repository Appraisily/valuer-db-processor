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
    This represents a single hit from the JSON input
    """
    lot_number: str = Field(..., alias="lotNumber")
    lot_ref: str = Field(..., alias="lotRef")
    price_result: float = Field(..., alias="priceResult")
    photo_path: str = Field(..., alias="photoPath")
    date_time_local: str = Field(..., alias="dateTimeLocal")
    date_time_utc_unix: int = Field(..., alias="dateTimeUTCUnix")
    currency_code: str = Field(..., alias="currencyCode")
    currency_symbol: str = Field(..., alias="currencySymbol")
    house_name: str = Field(..., alias="houseName")
    sale_type: str = Field(..., alias="saleType")
    lot_title: str = Field(..., alias="lotTitle")
    object_id: str = Field(..., alias="objectID")
    highlight_result: Optional[HighlightResult] = Field(None, alias="_highlightResult")
    ranking_info: Optional[RankingInfo] = Field(None, alias="_rankingInfo")
    
    class Config:
        populate_by_name = True

class AuctionLotResponse(BaseModel):
    """
    Response model for auction lot data after processing
    This includes GCS image path and processing metadata
    """
    id: str
    lot_number: str
    lot_ref: str
    price_result: float
    original_photo_path: str
    gcs_photo_path: Optional[str] = None
    date_time_local: str
    date_time_utc_unix: int
    currency_code: str
    currency_symbol: str
    house_name: str
    sale_type: str
    lot_title: str
    object_id: str
    highlight_result: Optional[Dict[str, Any]] = None
    ranking_info: Optional[Dict[str, Any]] = None
    processed_at: datetime.datetime
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        } 