import os
from functools import lru_cache
from typing import Optional, Literal
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    
    These settings can be overridden with environment variables
    """
    # Environment
    env: Literal["development", "production"] = "development"
    
    # Application
    app_name: str = "valuer-db-processor"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Storage
    use_gcs: bool = False
    gcs_bucket_name: str = "valuer-auction-images"
    local_storage_path: str = "./local_images"
    
    # Database
    db_type: Literal["sqlite", "postgresql"] = "sqlite"
    database_url: str = "sqlite:///./local_data/valuer.db"
    db_host: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    sql_echo: bool = False
    
    # Image Processing
    base_image_url: str = "https://image.invaluable.com/housePhotos/"
    optimize_images: bool = True
    max_image_dimension: int = 1200
    image_processing_batch_size: int = 50
    max_workers: int = 10
    
    # Logging
    log_level: str = "INFO"
    
    # Cloud SQL Connection (for production)
    instance_connection_name: Optional[str] = None
    project_id: Optional[str] = None
    
    @field_validator('db_host', 'db_user', 'db_password')
    def validate_postgres_settings(cls, v, values):
        """Ensure PostgreSQL settings are available when needed"""
        if 'db_type' in values.data and values.data.get('db_type') == 'postgresql' and not v:
            if 'env' in values.data and values.data.get('env') == 'production':
                # In production, these should be set
                field_name = [k for k, val in values.data.items() if val == v][0]
                raise ValueError(f"{field_name} must be set when db_type is postgresql and env is production")
        return v
    
<<<<<<< HEAD
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
=======
    # Update this to use the new Pydantic V2 format for model configuration
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",  # This allows extra fields from environment variables
        "env_nested_delimiter": "__",
        "populate_by_name": True
>>>>>>> 2296ae64bae38ecfae3e327a8294e1749682a204
    }

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