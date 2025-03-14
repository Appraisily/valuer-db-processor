# Valuer Auction Database Processor

This project processes auction data from JSON files, creates images for each auction lot, and stores everything in a local database. It's designed to be a first step before uploading to Google Cloud.

## Features

- Parse auction data from JSON files
- Create placeholder images for auction lots
- Store data in a local SQLite database
- Process a configurable number of items (default: 5)

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

The next step would be to implement uploading to Google Cloud:
- Upload images to Cloud Storage
- Store data in Cloud SQL (PostgreSQL)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 