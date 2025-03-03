import logging
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import uuid
import json
import os

from src.models.auction_lot import AuctionLotInput, AuctionLotResponse
from src.models.db_models import AuctionLot, Base
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create async database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    # These settings don't apply to SQLite, so only use them if not using SQLite
    **({} if 'sqlite' in settings.database_url else {
        'pool_size': settings.db_pool_size,
        'max_overflow': settings.db_max_overflow,
        'pool_timeout': settings.db_pool_timeout,
        'pool_recycle': settings.db_pool_recycle
    })
)

# Create async session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Initialize the database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

async def store_auction_data(auction_lots: List[AuctionLotInput]) -> List[AuctionLotResponse]:
    """
    Store auction data in the database
    
    Args:
        auction_lots: List of AuctionLotInput objects
        
    Returns:
        List of AuctionLotResponse objects
    """
    logger.info(f"Storing {len(auction_lots)} auction lots in database")
    stored_lots = []
    
    # Initialize database for local development if using SQLite
    if 'sqlite' in settings.database_url:
        await init_db()
    
    async with async_session() as session:
        async with session.begin():
            for lot in auction_lots:
                try:
                    # Check if this lot already exists
                    existing_lot = await get_lot_by_ref(session, lot.lot_ref)
                    
                    if existing_lot:
                        # Update existing lot
                        stored_lot = await update_lot(session, existing_lot, lot)
                    else:
                        # Create new lot
                        stored_lot = await create_lot(session, lot)
                        
                    if stored_lot:
                        stored_lots.append(stored_lot)
                        
                except Exception as e:
                    logger.error(f"Error storing auction lot {lot.lot_ref}: {str(e)}", exc_info=True)
    
    logger.info(f"Successfully stored {len(stored_lots)} auction lots")
    return stored_lots

async def get_lot_by_ref(session: AsyncSession, lot_ref: str) -> Optional[AuctionLot]:
    """
    Get an auction lot by its lot_ref
    
    Args:
        session: Database session
        lot_ref: Lot reference ID
        
    Returns:
        AuctionLot object or None if not found
    """
    query = select(AuctionLot).where(AuctionLot.lot_ref == lot_ref)
    result = await session.execute(query)
    return result.scalars().first()

async def create_lot(session: AsyncSession, lot_input: AuctionLotInput) -> Optional[AuctionLotResponse]:
    """
    Create a new auction lot in the database
    
    Args:
        session: Database session
        lot_input: AuctionLotInput object
        
    Returns:
        AuctionLotResponse object or None if creation failed
    """
    try:
        # Convert highlight result and ranking info to dict if needed
        highlight_result = lot_input.highlight_result.dict() if lot_input.highlight_result else None
        ranking_info = lot_input.ranking_info.dict() if lot_input.ranking_info else None
        
        # Create DB model from input model
        lot_db = AuctionLot(
            id=str(uuid.uuid4()),
            lot_number=lot_input.lot_number,
            lot_ref=lot_input.lot_ref,
            price_result=lot_input.price_result,
            original_photo_path=lot_input.photo_path,
            date_time_local=lot_input.date_time_local,
            date_time_utc_unix=lot_input.date_time_utc_unix,
            currency_code=lot_input.currency_code,
            currency_symbol=lot_input.currency_symbol,
            house_name=lot_input.house_name,
            sale_type=lot_input.sale_type,
            lot_title=lot_input.lot_title,
            object_id=lot_input.object_id,
            processed_at=datetime.datetime.utcnow()
        )
        
        # Handle JSON fields based on database type
        if 'sqlite' in settings.database_url:
            # For SQLite, serialize to JSON string
            if highlight_result:
                lot_db.highlight_result = json.dumps(highlight_result)
            if ranking_info:
                lot_db.ranking_info = json.dumps(ranking_info)
        else:
            # For PostgreSQL, assign directly
            lot_db.highlight_result = highlight_result
            lot_db.ranking_info = ranking_info
        
        # Add to session
        session.add(lot_db)
        await session.flush()
        
        # Create response object
        return create_response_from_db(lot_db)
        
    except IntegrityError as e:
        logger.error(f"Integrity error creating auction lot {lot_input.lot_ref}: {str(e)}")
        await session.rollback()
        return None
    except Exception as e:
        logger.error(f"Error creating auction lot {lot_input.lot_ref}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

async def update_lot(session: AsyncSession, existing_lot: AuctionLot, lot_input: AuctionLotInput) -> Optional[AuctionLotResponse]:
    """
    Update an existing auction lot in the database
    
    Args:
        session: Database session
        existing_lot: Existing AuctionLot database model
        lot_input: New AuctionLotInput data
        
    Returns:
        AuctionLotResponse object or None if update failed
    """
    try:
        # Convert highlight result and ranking info to dict if needed
        highlight_result = lot_input.highlight_result.dict() if lot_input.highlight_result else None
        ranking_info = lot_input.ranking_info.dict() if lot_input.ranking_info else None
        
        # Update basic fields
        existing_lot.lot_number = lot_input.lot_number
        existing_lot.price_result = lot_input.price_result
        existing_lot.original_photo_path = lot_input.photo_path
        existing_lot.date_time_local = lot_input.date_time_local
        existing_lot.date_time_utc_unix = lot_input.date_time_utc_unix
        existing_lot.currency_code = lot_input.currency_code
        existing_lot.currency_symbol = lot_input.currency_symbol
        existing_lot.house_name = lot_input.house_name
        existing_lot.sale_type = lot_input.sale_type
        existing_lot.lot_title = lot_input.lot_title
        existing_lot.object_id = lot_input.object_id
        existing_lot.processed_at = datetime.datetime.utcnow()
        
        # Handle JSON fields based on database type
        if 'sqlite' in settings.database_url:
            # For SQLite, serialize to JSON string
            if highlight_result:
                existing_lot.highlight_result = json.dumps(highlight_result)
            else:
                existing_lot.highlight_result = None
                
            if ranking_info:
                existing_lot.ranking_info = json.dumps(ranking_info)
            else:
                existing_lot.ranking_info = None
        else:
            # For PostgreSQL, assign directly
            existing_lot.highlight_result = highlight_result
            existing_lot.ranking_info = ranking_info
        
        # No need to add to session as it's already tracked
        await session.flush()
        
        # Create response object
        return create_response_from_db(existing_lot)
        
    except Exception as e:
        logger.error(f"Error updating auction lot {lot_input.lot_ref}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

def create_response_from_db(lot_db: AuctionLot) -> AuctionLotResponse:
    """
    Create an AuctionLotResponse from a database model
    
    Args:
        lot_db: AuctionLot database model
        
    Returns:
        AuctionLotResponse object
    """
    # Handle JSON fields based on database type
    highlight_result = None
    ranking_info = None
    
    if 'sqlite' in settings.database_url:
        # For SQLite, deserialize JSON string
        if lot_db.highlight_result:
            try:
                highlight_result = json.loads(lot_db.highlight_result)
            except:
                highlight_result = None
                
        if lot_db.ranking_info:
            try:
                ranking_info = json.loads(lot_db.ranking_info)
            except:
                ranking_info = None
    else:
        # For PostgreSQL, use directly
        highlight_result = lot_db.highlight_result
        ranking_info = lot_db.ranking_info
    
    return AuctionLotResponse(
        id=lot_db.id,
        lot_number=lot_db.lot_number,
        lot_ref=lot_db.lot_ref,
        price_result=lot_db.price_result,
        original_photo_path=lot_db.original_photo_path,
        gcs_photo_path=lot_db.gcs_photo_path,
        date_time_local=lot_db.date_time_local,
        date_time_utc_unix=lot_db.date_time_utc_unix,
        currency_code=lot_db.currency_code,
        currency_symbol=lot_db.currency_symbol,
        house_name=lot_db.house_name,
        sale_type=lot_db.sale_type,
        lot_title=lot_db.lot_title,
        object_id=lot_db.object_id,
        highlight_result=highlight_result,
        ranking_info=ranking_info,
        processed_at=lot_db.processed_at
    ) 