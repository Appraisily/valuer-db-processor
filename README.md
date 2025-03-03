# Valuer DB Processor

A Cloud Run service that processes auction data JSON files, extracts images and stores them in Google Cloud Storage, and persists structured data to a database.

## Overview

This service is designed to process JSON files containing auction data, including:
- Extracting and downloading images from URLs in the JSON data
- Uploading images to Google Cloud Storage (GCS)
- Storing structured auction data in a database
- Providing a scalable, serverless solution deployed on Cloud Run

## Features

- **High Performance**: Asynchronous processing for high throughput
- **Scalable**: Automatically scales with load on Cloud Run
- **Resilient**: Built-in error handling and retry mechanisms
- **Secure**: Follows GCP security best practices
- **Monitored**: Comprehensive logging and monitoring

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI for high-performance API endpoints
- **Database**: Cloud SQL (PostgreSQL) or Firestore
- **Storage**: Google Cloud Storage for image files
- **Deployment**: Google Cloud Run
- **CI/CD**: GitHub Actions

## Project Structure

```
/
├── src/                     # Source code
├── tests/                   # Test cases
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── implementation-plan.md   # Detailed implementation plan
```

## Setup and Installation

### Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Docker installed (for local development)
- Python 3.10+ installed (for local development)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/valuer-db-processor.git
   cd valuer-db-processor
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   export GCS_BUCKET_NAME=your-bucket
   export DATABASE_URL=your-database-url
   # ... other environment variables
   ```

5. Run the service locally:
   ```bash
   uvicorn src.main:app --reload
   ```

### Deployment to Cloud Run

1. Build and push the Docker image:
   ```bash
   gcloud builds submit --tag gcr.io/your-project/valuer-db-processor
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy valuer-db-processor \
     --image gcr.io/your-project/valuer-db-processor \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2
   ```

## Usage

### API Endpoints

- `POST /process`: Process a JSON file submitted in the request body
- `GET /health`: Health check endpoint
- `GET /metrics`: Service metrics

### Example Request

```bash
curl -X POST https://your-service-url/process \
  -H "Content-Type: application/json" \
  -d @path/to/your/file.json
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 