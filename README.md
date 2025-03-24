# Valuer Auction Database Processor

<<<<<<< HEAD
A robust service for processing auction lot data, handling image downloads with advanced fallback strategies, and storing structured auction information in a database.
=======
This project processes auction data from JSON files, creates images for each auction lot, and stores everything in a local database. It's designed to be a first step before uploading to Google Cloud.
>>>>>>> 2296ae64bae38ecfae3e327a8294e1749682a204

## Features

<<<<<<< HEAD
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
=======
- Parse auction data from JSON files
- Create placeholder images for auction lots
- Store data in a local SQLite database
- Process a configurable number of items (default: 5)
>>>>>>> 2296ae64bae38ecfae3e327a8294e1749682a204

## Getting Started

### Prerequisites

- Python 3.10+
- Required Python packages (install via `pip install -r requirements.txt`):
  - pydantic
  - pydantic-settings
  - sqlalchemy
  - aiosqlite
  - httpx
  - pillow
  - python-dotenv
  - tenacity

### Installation

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the necessary configuration (see `.env.example`)

### Usage

To process the first 5 items from the example JSON file:

```bash
python process_first_five.py
```

Command-line options:
- `--limit N`: Process only the first N items (default: 5)
- `--file PATH`: Path to the JSON file to process (default: example_json.json)
- `--output DIR`: Output directory for the database (default: local_data)
- `--image-dir DIR`: Directory for image storage (default: local_images)

Example:
```bash
python process_first_five.py --limit 10 --file my_data.json --output my_data --image-dir my_images
```

## Project Structure

- `process_first_five.py`: Main script to process auction data
- `src/`: Source code modules
  - `models/`: Data models
  - `services/`: Services for processing and storage
  - `config.py`: Configuration settings

## Data Flow

1. Read and parse JSON auction data
2. Create placeholder images for each auction lot
3. Store data in a local SQLite database

## Future Enhancements

<<<<<<< HEAD
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
=======
The next step would be to implement uploading to Google Cloud:
- Upload images to Cloud Storage
- Store data in Cloud SQL (PostgreSQL)
>>>>>>> 2296ae64bae38ecfae3e327a8294e1749682a204

## License

This project is licensed under the MIT License - see the LICENSE file for details. 