#!/usr/bin/env python
"""
Script to create database tables for the auction data in PostgreSQL or SQLite
"""
import os
import logging
import psycopg2
import sqlite3
from pathlib import Path
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("db_creator")

def create_postgres_tables(host, dbname, user, password):
    """Create PostgreSQL tables"""
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(
            host=host,
            dbname=dbname,
            user=user,
            password=password
        )
        
        conn.autocommit = True
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
        
        logger.info(f"PostgreSQL tables created successfully at {host}/{dbname}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating PostgreSQL tables: {e}")
        return False

def create_sqlite_db(db_path):
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
        
        logger.info(f"SQLite database created successfully at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating SQLite database: {e}")
        return False

def main():
    """Main function"""
    settings = get_settings()
    
    if settings.db_type == "postgresql":
        logger.info("Setting up PostgreSQL tables...")
        if create_postgres_tables(
            host=settings.db_host,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password
        ):
            logger.info("PostgreSQL setup completed successfully")
        else:
            logger.error("Failed to set up PostgreSQL tables")
    else:
        # Path to the SQLite database
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, "local_data", "valuer.db")
        
        # Create the SQLite database
        if create_sqlite_db(db_path):
            logger.info("SQLite database setup completed successfully")
        else:
            logger.error("Failed to set up SQLite database")

if __name__ == "__main__":
    main()