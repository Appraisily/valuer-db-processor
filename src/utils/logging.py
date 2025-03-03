import logging
import sys
import os
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler
from src.config import get_settings

def setup_logging() -> logging.Logger:
    """
    Set up logging for the application
    
    Returns:
        Configured logger object
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("valuer-db-processor")
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Check if running in GCP environment
    if os.environ.get("KUBERNETES_SERVICE_HOST") or os.environ.get("K_SERVICE"):
        # Running in Google Cloud, use Cloud Logging
        client = cloud_logging.Client()
        handler = CloudLoggingHandler(client, name=settings.app_name)
    else:
        # Local development, use console logging
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Ensure we don't propagate to root logger
    logger.propagate = False
    
    return logger 