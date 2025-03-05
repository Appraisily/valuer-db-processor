#!/usr/bin/env python
"""
Script to create database tables for the auction data
"""
import os
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("db_creator")

def create_db(db_path):
    """Create SQLite database with the necessary tables"""
    try:
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create auction_lots table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction_lots (
            id TEXT PRIMARY KEY,
            lot_ref TEXT UNIQUE NOT NULL,
            lot_number TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            
            house_name TEXT NOT NULL,
            sale_type TEXT NOT NULL,
            sale_date TIMESTAMP NOT NULL,
            
            price_realized REAL NOT NULL,
            currency_code TEXT NOT NULL,
            currency_symbol TEXT NOT NULL,
            
            photo_path TEXT NOT NULL,
            storage_path TEXT,
            
            raw_data TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for faster querying
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lot_ref ON auction_lots(lot_ref)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_house_name ON auction_lots(house_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sale_date ON auction_lots(sale_date)')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Database created successfully at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False

def main():
    """Main function"""
    # Path to the SQLite database
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "local_data", "valuer.db")
    
    # Create the database
    if create_db(db_path):
        logger.info("Database setup completed successfully")
    else:
        logger.error("Failed to set up database")

if __name__ == "__main__":
    main()