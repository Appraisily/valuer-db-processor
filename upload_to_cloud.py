#!/usr/bin/env python3
"""
Local to Cloud Upload Pipeline

This script transfers data from local SQLite database to Google Cloud Platform:
1. Reads auction lot data from local SQLite database
2. Uploads images to Google Cloud Storage
3. Writes data to Cloud SQL (PostgreSQL)
4. Updates references in the database to point to GCS paths
"""

import os
import sys
import logging
import asyncio
import argparse
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from google.cloud import storage
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Add the current directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.db_models import AuctionLot, Base
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cloud_uploader")

# Get settings
settings = get_settings()

class CloudUploader:
    """Handles uploading data from local to cloud"""
    
    def __init__(self, gcs_bucket_name, cloud_sql_connection, local_db_path):
        """
        Initialize the uploader with necessary configuration
        
        Args:
            gcs_bucket_name: Name of the GCS bucket to upload images to
            cloud_sql_connection: Connection string for Cloud SQL
            local_db_path: Path to the local SQLite database
        """
        self.gcs_bucket_name = gcs_bucket_name
        self.cloud_sql_connection = cloud_sql_connection
        self.local_db_path = local_db_path
        self.storage_client = None
        self.bucket = None
        self.local_engine = None
        self.cloud_engine = None
        self.LocalSession = None
        self.CloudSession = None
        
    def initialize(self):
        """Initialize connections to local and cloud resources"""
        try:
            # Initialize GCS client
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.gcs_bucket_name)
            logger.info(f"Connected to GCS bucket: {self.gcs_bucket_name}")
            
            # Initialize local SQLite connection
            self.local_engine = create_engine(f"sqlite:///{self.local_db_path}", echo=False)
            self.LocalSession = sessionmaker(bind=self.local_engine)
            logger.info(f"Connected to local database: {self.local_db_path}")
            
            # Initialize Cloud SQL connection
            if 'postgresql' in self.cloud_sql_connection:
                self.cloud_engine = create_async_engine(self.cloud_sql_connection, echo=False)
                self.CloudSession = sessionmaker(
                    bind=self.cloud_engine, 
                    class_=AsyncSession, 
                    expire_on_commit=False
                )
                logger.info(f"Connected to Cloud SQL database")
            else:
                raise ValueError("Cloud SQL connection must be a PostgreSQL connection string")
                
        except Exception as e:
            logger.error(f"Error initializing connections: {str(e)}")
            raise
    
    async def create_cloud_tables(self):
        """Create tables in Cloud SQL if they don't exist"""
        try:
            async with self.cloud_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Created tables in Cloud SQL database")
        except Exception as e:
            logger.error(f"Error creating tables in Cloud SQL: {str(e)}")
            raise
    
    async def upload_image_to_gcs(self, local_image_path, gcs_path):
        """
        Upload an image to Google Cloud Storage
        
        Args:
            local_image_path: Path to the local image file
            gcs_path: Path where the image should be stored in GCS
            
        Returns:
            Public URL of the uploaded image or None if upload failed
        """
        try:
            # Create a blob in the bucket
            blob = self.bucket.blob(gcs_path)
            
            # Read the image data
            with open(local_image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Get file extension
            file_extension = os.path.splitext(local_image_path)[1].lower()[1:] or 'jpeg'
            
            # Upload the image
            blob.upload_from_string(
                image_data,
                content_type=f"image/{file_extension}"
            )
            
            # Make the blob publicly accessible
            blob.make_public()
            
            logger.info(f"Uploaded image to GCS: {gcs_path}")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading image to GCS: {str(e)}")
            return None
    
    async def process_lot(self, lot):
        """
        Process a single auction lot
        
        Args:
            lot: AuctionLot object from local database
            
        Returns:
            Updated auction lot with GCS URLs
        """
        try:
            # Check if the lot has a local image
            if lot.storage_path and os.path.exists(lot.storage_path):
                # Generate GCS path
                house_name = lot.house_name.lower().replace(" ", "_")
                filename = os.path.basename(lot.storage_path)
                gcs_path = f"{house_name}/{lot.lot_ref}/{filename}"
                
                # Upload image to GCS
                gcs_url = await self.upload_image_to_gcs(lot.storage_path, gcs_path)
                
                if gcs_url:
                    # Update lot with GCS URL
                    lot.storage_path = gcs_url
                    logger.info(f"Updated lot {lot.lot_ref} with GCS URL: {gcs_url}")
            
            return lot
            
        except Exception as e:
            logger.error(f"Error processing lot {lot.lot_ref}: {str(e)}")
            return lot
    
    async def upload_lot_to_cloud_sql(self, lot):
        """
        Upload a lot to Cloud SQL
        
        Args:
            lot: AuctionLot object to upload
            
        Returns:
            True if upload was successful, False otherwise
        """
        try:
            async with self.CloudSession() as session:
                async with session.begin():
                    # Check if this lot already exists
                    stmt = sa.select(AuctionLot).where(AuctionLot.lot_ref == lot.lot_ref)
                    result = await session.execute(stmt)
                    existing_lot = result.scalar_one_or_none()
                    
                    if existing_lot:
                        logger.info(f"Updating existing lot in Cloud SQL: {lot.lot_ref}")
                        
                        # Update existing lot
                        existing_lot.lot_number = lot.lot_number
                        existing_lot.title = lot.title
                        existing_lot.description = lot.description
                        
                        existing_lot.house_name = lot.house_name
                        existing_lot.sale_type = lot.sale_type
                        existing_lot.sale_date = lot.sale_date
                        
                        existing_lot.price_realized = lot.price_realized
                        existing_lot.currency_code = lot.currency_code
                        existing_lot.currency_symbol = lot.currency_symbol
                        
                        existing_lot.photo_path = lot.photo_path
                        existing_lot.storage_path = lot.storage_path
                        
                        existing_lot.raw_data = lot.raw_data
                    else:
                        logger.info(f"Creating new lot in Cloud SQL: {lot.lot_ref}")
                        
                        # Create new lot with the same ID as local
                        cloud_lot = AuctionLot(
                            id=lot.id,
                            lot_ref=lot.lot_ref,
                            lot_number=lot.lot_number,
                            title=lot.title,
                            description=lot.description,
                            
                            house_name=lot.house_name,
                            sale_type=lot.sale_type,
                            sale_date=lot.sale_date,
                            
                            price_realized=lot.price_realized,
                            currency_code=lot.currency_code,
                            currency_symbol=lot.currency_symbol,
                            
                            photo_path=lot.photo_path,
                            storage_path=lot.storage_path,
                            
                            raw_data=lot.raw_data,
                            created_at=lot.created_at,
                            updated_at=lot.updated_at
                        )
                        session.add(cloud_lot)
                
                # Commit the transaction
                await session.commit()
                logger.info(f"Successfully uploaded lot {lot.lot_ref} to Cloud SQL")
                return True
                
        except Exception as e:
            logger.error(f"Error uploading lot {lot.lot_ref} to Cloud SQL: {str(e)}")
            return False
    
    async def run(self, batch_size=10):
        """
        Run the upload pipeline
        
        Args:
            batch_size: Number of lots to process in each batch
        """
        try:
            # Initialize connections
            self.initialize()
            
            # Create tables in Cloud SQL
            await self.create_cloud_tables()
            
            # Read lots from local database
            with self.LocalSession() as session:
                # Get all lots
                lots = session.query(AuctionLot).all()
                logger.info(f"Found {len(lots)} lots in local database")
                
                # Process lots in batches
                for i in range(0, len(lots), batch_size):
                    batch = lots[i:i+batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1} of {(len(lots) + batch_size - 1)//batch_size}")
                    
                    # Process each lot in the batch
                    processed_lots = []
                    for lot in batch:
                        processed_lot = await self.process_lot(lot)
                        processed_lots.append(processed_lot)
                    
                    # Upload to Cloud SQL
                    cloud_tasks = []
                    for processed_lot in processed_lots:
                        task = self.upload_lot_to_cloud_sql(processed_lot)
                        cloud_tasks.append(task)
                    
                    # Wait for cloud uploads to complete
                    results = await asyncio.gather(*cloud_tasks)
                    
                    # Check results
                    success_count = sum(1 for r in results if r is True)
                    logger.info(f"Batch {i//batch_size + 1} complete: {success_count}/{len(batch)} lots uploaded successfully")
            
            logger.info("Upload pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Error in upload pipeline: {str(e)}")
            raise

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Upload data from local to cloud")
    parser.add_argument("--gcs-bucket", type=str, default=settings.gcs_bucket_name,
                        help="Name of the GCS bucket to upload images to")
    parser.add_argument("--cloud-sql", type=str, required=True,
                        help="Connection string for Cloud SQL (PostgreSQL)")
    parser.add_argument("--local-db", type=str, default="./local_data/valuer.db",
                        help="Path to the local SQLite database")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Number of lots to process in each batch")
    
    args = parser.parse_args()
    
    # Create and run the uploader
    uploader = CloudUploader(
        gcs_bucket_name=args.gcs_bucket,
        cloud_sql_connection=args.cloud_sql,
        local_db_path=args.local_db
    )
    
    await uploader.run(batch_size=args.batch_size)

if __name__ == "__main__":
    asyncio.run(main())