import os
from functools import lru_cache
from typing import Optional
from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    
    These settings can be overridden with environment variables
    """
    # Application
    app_name: str = "valuer-db-processor"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/valuer_db")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    db_pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    sql_echo: bool = os.getenv("SQL_ECHO", "False").lower() in ("true", "1", "t")
    
    # Google Cloud Storage
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "valuer-images")
    
    # Image Processing
    base_image_url: str = os.getenv("BASE_IMAGE_URL", "https://valuer-image-source.com")
    optimize_images: bool = os.getenv("OPTIMIZE_IMAGES", "True").lower() in ("true", "1", "t")
    max_image_dimension: int = int(os.getenv("MAX_IMAGE_DIMENSION", "1200"))
    image_processing_batch_size: int = int(os.getenv("IMAGE_PROCESSING_BATCH_SIZE", "10"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        from_attributes = True

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached to avoid reloading
    
    Returns:
        Settings object
    """
    return Settings()

def configure_from_environment():
    """
    Configure settings from environment variables
    
    This function is called during application startup to
    ensure all environment variables are loaded
    """
    # Get settings to trigger validation
    settings = get_settings()
    return settings 