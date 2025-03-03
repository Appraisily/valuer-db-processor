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

# Determine the database URL based on configuration
if settings.db_type == "sqlite":
    db_url = f"sqlite+aiosqlite:///{settings.db_name}"
    is_sqlite = True
elif settings.db_type == "postgresql":
    if settings.env == "production" and settings.instance_connection_name:
        # Cloud SQL with unix socket
        db_url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@/{settings.db_name}?host={settings.db_host}"
    else:
        # Regular PostgreSQL connection
        db_url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}/{settings.db_name}"
    is_sqlite = False
else:
    raise ValueError(f"Unsupported database type: {settings.db_type}")

logger.info(f"Using database: {settings.db_type}")

# Create async database engine
engine = create_async_engine(
    db_url,
    echo=settings.sql_echo,
    # These settings don't apply to SQLite
    **({} if is_sqlite else {
        'pool_size': settings.db_pool_size,
        'max_overflow': settings.db_max_overflow,
        'pool_timeout': settings.db_pool_timeout,
        'pool_recycle': settings.db_pool_recycle
    })
)

# Create sessionmaker
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database by creating all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def store_auction_data(auction_lots: List[AuctionLotInput]) -> List[AuctionLotResponse]:
    """
    Store auction data in the database
    
    Args:
        auction_lots: List of auction lots to store
    
    Returns:
        List of created/updated auction lots
    """
    logger.info(f"Storing {len(auction_lots)} auction lots in database")
    
    results = []
    
    # Create a session
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for lot_input in auction_lots:
                try:
                    # Check if lot already exists
                    existing_lot = await get_lot_by_ref(session, lot_input.lotRef)
                    
                    if existing_lot:
                        # Update existing lot
                        result = await update_lot(session, existing_lot, lot_input)
                        if result:
                            results.append(result)
                    else:
                        # Create new lot
                        result = await create_lot(session, lot_input)
                        if result:
                            results.append(result)
                
                except Exception as e:
                    logger.error(f"Error processing lot {lot_input.lotRef}: {str(e)}")
                    # Continue with next lot
                    continue
    
    logger.info(f"Successfully stored {len(results)} auction lots")
    return results

async def get_lot_by_ref(session: AsyncSession, lot_ref: str) -> Optional[AuctionLot]:
    """
    Get a lot by its reference
    
    Args:
        session: Database session
        lot_ref: Lot reference
    
    Returns:
        Auction lot or None if not found
    """
    stmt = select(AuctionLot).where(AuctionLot.lot_ref == lot_ref)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_lot(session: AsyncSession, lot_input: AuctionLotInput) -> Optional[AuctionLotResponse]:
    """
    Create a new auction lot
    
    Args:
        session: Database session
        lot_input: Auction lot input
    
    Returns:
        Created auction lot response or None if failed
    """
    try:
        # Create new lot
        new_lot = AuctionLot(
            # Basic info
            id=str(uuid.uuid4()),
            lot_ref=lot_input.lotRef,
            lot_number=lot_input.lotNumber,
            title=lot_input.lotTitle,
            description=lot_input.description if hasattr(lot_input, 'description') else None,
            
            # Auction details
            house_name=lot_input.houseName,
            sale_type=lot_input.saleType,
            sale_date=datetime.datetime.fromtimestamp(lot_input.dateTimeUTCUnix),
            
            # Price details
            price_realized=lot_input.priceResult,
            currency_code=lot_input.currencyCode,
            currency_symbol=lot_input.currencySymbol,
            
            # Image
            photo_path=lot_input.photoPath,
            
            # Timestamps
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            
            # Store additional data in JSON field
            raw_data=json.dumps({
                key: value for key, value in lot_input.dict().items()
                if key not in [
                    'lotRef', 'lotNumber', 'lotTitle', 'description',
                    'houseName', 'saleType', 'dateTimeUTCUnix',
                    'priceResult', 'currencyCode', 'currencySymbol',
                    'photoPath'
                ]
            })
        )
        
        # Add to session
        session.add(new_lot)
        
        # Return response
        logger.info(f"Created new lot: {new_lot.lot_ref}")
        return create_response_from_db(new_lot)
    
    except Exception as e:
        logger.error(f"Error creating lot: {str(e)}")
        return None

async def update_lot(session: AsyncSession, existing_lot: AuctionLot, lot_input: AuctionLotInput) -> Optional[AuctionLotResponse]:
    """
    Update an existing auction lot
    
    Args:
        session: Database session
        existing_lot: Existing auction lot
        lot_input: New auction lot data
    
    Returns:
        Updated auction lot response or None if failed
    """
    try:
        # Update fields
        existing_lot.lot_number = lot_input.lotNumber
        existing_lot.title = lot_input.lotTitle
        existing_lot.description = lot_input.description if hasattr(lot_input, 'description') else existing_lot.description
        
        existing_lot.house_name = lot_input.houseName
        existing_lot.sale_type = lot_input.saleType
        existing_lot.sale_date = datetime.datetime.fromtimestamp(lot_input.dateTimeUTCUnix)
        
        existing_lot.price_realized = lot_input.priceResult
        existing_lot.currency_code = lot_input.currencyCode
        existing_lot.currency_symbol = lot_input.currencySymbol
        
        existing_lot.photo_path = lot_input.photoPath
        
        existing_lot.updated_at = datetime.datetime.utcnow()
        
        # Update raw data
        existing_raw_data = json.loads(existing_lot.raw_data) if existing_lot.raw_data else {}
        new_raw_data = {
            key: value for key, value in lot_input.dict().items()
            if key not in [
                'lotRef', 'lotNumber', 'lotTitle', 'description',
                'houseName', 'saleType', 'dateTimeUTCUnix',
                'priceResult', 'currencyCode', 'currencySymbol',
                'photoPath'
            ]
        }
        
        # Merge old and new data, with new data taking precedence
        merged_data = {**existing_raw_data, **new_raw_data}
        existing_lot.raw_data = json.dumps(merged_data)
        
        # No need to add to session since it's already tracked
        
        # Return response
        logger.info(f"Updated existing lot: {existing_lot.lot_ref}")
        return create_response_from_db(existing_lot)
    
    except Exception as e:
        logger.error(f"Error updating lot: {str(e)}")
        return None

def create_response_from_db(lot_db: AuctionLot) -> AuctionLotResponse:
    """
    Create a response object from a database object
    
    Args:
        lot_db: Database auction lot
    
    Returns:
        Auction lot response
    """
    return AuctionLotResponse(
        id=lot_db.id,
        lotRef=lot_db.lot_ref,
        lotNumber=lot_db.lot_number,
        lotTitle=lot_db.title,
        description=lot_db.description,
        
        houseName=lot_db.house_name,
        saleType=lot_db.sale_type,
        saleDate=lot_db.sale_date.isoformat(),
        
        priceRealized=lot_db.price_realized,
        currencyCode=lot_db.currency_code,
        currencySymbol=lot_db.currency_symbol,
        
        photoPath=lot_db.photo_path,
        
        createdAt=lot_db.created_at.isoformat(),
        updatedAt=lot_db.updated_at.isoformat(),
        
        rawData=json.loads(lot_db.raw_data) if lot_db.raw_data else {}
    ) 