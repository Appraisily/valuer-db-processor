from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
import datetime
import uuid
import json

Base = declarative_base()

class AuctionLot(Base):
    """
    SQLAlchemy model for the auction_lots table
    """
    __tablename__ = "auction_lots"
    
    # Basic Information
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_ref = Column(String(100), nullable=False, index=True, unique=True)
    lot_number = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    # Auction Details
    house_name = Column(String(200), nullable=False, index=True)
    sale_type = Column(String(100), nullable=False)
    sale_date = Column(DateTime, nullable=False, index=True)
    
    # Price Details
    price_realized = Column(Float, nullable=False)
    currency_code = Column(String(10), nullable=False)
    currency_symbol = Column(String(10), nullable=False)
    
    # Image
    photo_path = Column(String(500), nullable=False)
    storage_path = Column(String(500), nullable=True)
    
    # Additional Data (stored as JSON)
    raw_data = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<AuctionLot(id={self.id}, lot_ref={self.lot_ref}, house_name={self.house_name})>"
        
    @property
    def highlight_result_data(self):
        if self.highlight_result:
            return json.loads(self.highlight_result)
        return None
        
    @highlight_result_data.setter
    def highlight_result_data(self, value):
        if value:
            self.highlight_result = json.dumps(value)
        else:
            self.highlight_result = None
            
    @property
    def ranking_info_data(self):
        if self.ranking_info:
            return json.loads(self.ranking_info)
        return None
        
    @ranking_info_data.setter
    def ranking_info_data(self, value):
        if value:
            self.ranking_info = json.dumps(value)
        else:
            self.ranking_info = None 