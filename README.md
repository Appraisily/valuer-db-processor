# Valuer DB Processor

A robust service for processing auction lot data, handling image downloads with advanced fallback strategies, and storing structured auction information in a database.

## Overview

This service:
- Processes JSON files containing auction data from various auction houses
- Extracts and downloads images referenced in the data using multiple fallback approaches:
  - Standard download with browser-like headers to bypass protection
  - Alternative CDN URLs if primary URL fails
  - Host header injection to bypass Cloudflare restrictions
  - Origin IP direct access as a fallback method
  - Local image cache for development mode
- Optimizes images by resizing and compressing them for efficient storage
- Uploads images to Google Cloud Storage (or stores locally for development)
- Stores structured auction data in a database (PostgreSQL in production, SQLite for development)
- Provides RESTful API endpoints for data submission and processing status
- Handles batch processing with configurable concurrency limits
- Implements comprehensive error handling and logging

## Technology Stack

- Python 3.10+
- FastAPI for API endpoints
- AsyncIO for asynchronous processing
- PostgreSQL (production) and SQLite (development) for data storage
- Google Cloud Storage for image storage
- Docker for containerization
- Deployed on Google Cloud Run

## Project Structure

```
/
├── src/                     # Source code
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration handling
│   ├── models/              # Data models
│   │   ├── auction_lot.py   # Pydantic models for the data
│   │   └── db_models.py     # Database models
│   ├── services/            # Business logic
│   │   ├── parser.py        # JSON parsing logic
│   │   ├── image_service.py # Image handling logic
│   │   └── db_service.py    # Database operations
│   └── utils/               # Utility functions
│       ├── logging.py       # Logging utilities
│       └── errors.py        # Error handling utilities
├── tests/                   # Test cases
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
├── test_app.py              # Testing script
└── README.md                # Project documentation
```

## Local Development

1. Clone the repository
   ```bash
   git clone https://github.com/YOUR_USERNAME/valuer-db-processor.git
   cd valuer-db-processor
   ```

2. Set up virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create and configure environment variables
   ```bash
   cp .env.example .env
   # Edit .env file with your local configuration
   ```

5. Run the application
   ```bash
   uvicorn src.main:app --reload
   ```

6. Test with the test script
   ```bash
   python test_app.py
   ```

## API Endpoints

- `GET /health`: Health check endpoint to verify service status
  - Returns: Service status, version, and timestamp

- `POST /process`: Submit auction data for processing
  - Input: JSON data containing auction lot information
  - Processing: 
    - Validates JSON structure
    - Parses auction lot data
    - Stores data in database (creates new records or updates existing)
    - Asynchronously downloads, optimizes, and stores images in the background
  - Returns: List of processed auction lots with database IDs

- `GET /metrics`: Service metrics endpoint (placeholder for production monitoring)
  - Returns: Processing statistics including total processed lots, success rates, and performance metrics

## Deployment

The service is deployed on Google Cloud Run with connection to Cloud SQL and Cloud Storage.
See `gcp-setup-commands.md` for detailed deployment instructions.

### Key GCP Resources

- **Cloud Run**: Serverless container platform for the application
- **Cloud SQL**: Managed PostgreSQL database for structured data
- **Cloud Storage**: Object storage for auction images
- **Secret Manager**: Secure storage for sensitive information

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| ENV | Environment (development/production) | production |
| GCS_BUCKET | Google Cloud Storage bucket name | valuer-auction-images |
| USE_GCS | Whether to use GCS or local storage | true |
| DB_HOST | Database host | /cloudsql/project:region:instance |
| DB_NAME | Database name | valuer_auctions |
| DB_USER | Database username | valuer_app |
| DB_PASSWORD | Database password | (via Secret Manager) |
| DB_TYPE | Database type | postgresql |
| LOG_LEVEL | Logging level | INFO |
| BASE_IMAGE_URL | Base URL for image downloads | https://image.invaluable.com/housePhotos/ |
| MAX_WORKERS | Maximum number of worker threads | 10 |
| BATCH_SIZE | Batch size for processing | 50 |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 