from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
import datetime
import uuid
import json

Base = declarative_base()

class AuctionLot(Base):
    """
    SQLAlchemy model for the auction_lots table in the database
    """
    __tablename__ = "auction_lots"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_number = Column(String(100), nullable=False)
    lot_ref = Column(String(100), nullable=False, index=True, unique=True)
    price_result = Column(Float, nullable=False)
    original_photo_path = Column(String(500), nullable=False)
    gcs_photo_path = Column(String(500), nullable=True)
    date_time_local = Column(String(100), nullable=False)
    date_time_utc_unix = Column(Integer, nullable=False, index=True)
    currency_code = Column(String(10), nullable=False)
    currency_symbol = Column(String(10), nullable=False)
    house_name = Column(String(200), nullable=False, index=True)
    sale_type = Column(String(100), nullable=False)
    lot_title = Column(Text, nullable=False)
    object_id = Column(String(100), nullable=False, index=True)
    highlight_result = Column(Text, nullable=True)
    ranking_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
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