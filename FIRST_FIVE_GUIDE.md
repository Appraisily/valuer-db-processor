# Processing the First Five Records Guide

This guide explains how to process the first 5 records from the example JSON data, which is useful for testing and validation.

## Local Processing Steps

### 1. Ensure Local Setup

First, make sure you've completed the setup steps in [LOCAL_TESTING.md](LOCAL_TESTING.md):
- Created and activated a virtual environment
- Installed dependencies
- Set up a local SQLite database

### 2. Prepare Environment Variables

For local processing, ensure you have a `.env` file configured for local development:

```bash
# For local SQLite database and local file storage:
ENV=development
USE_GCS=false
GCS_BUCKET_NAME=valuer-auction-images
LOCAL_STORAGE_PATH=./local_images
DB_TYPE=sqlite
```

### 3. Create Database Tables

Make sure the database tables are created:

```bash
python create_tables.py
```

### 4. Run the Process First Five Script

Execute the script to process the first 5 records from the example JSON:

```bash
python process_first_five.py
```

This will:
1. Load the example JSON file
2. Extract the first 5 auction lots
3. Download the images for each lot
4. Store the images locally (in the ./local_images directory)
5. Save the data to the SQLite database

### 5. Verify the Results

Check that the processing completed successfully:

```bash
# Check local images directory
ls -la local_images

# Check SQLite database (requires sqlite3 CLI tool)
sqlite3 local_data/valuer.db "SELECT lot_ref, title, photo_path, storage_path FROM auction_lots LIMIT 5;"
```

## Cloud Processing Steps

If you want to test processing the first 5 records in the cloud environment:

### 1. Set Up Cloud Environment

Make sure you've completed the steps in [CLOUD_RUN_SETUP.md](CLOUD_RUN_SETUP.md) to:
- Set up a GCP project
- Create a GCS bucket
- Create a Cloud SQL PostgreSQL instance
- Deploy the application to Cloud Run

### 2. Update Environment Variables for Cloud

Update your Cloud Run service with the necessary environment variables:

```bash
# Set your project and other variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export INSTANCE_NAME="valuer-db"
export GCS_BUCKET="valuer-auction-images"

# Update the Cloud Run service
gcloud run services update valuer-db-processor \
  --set-env-vars="ENV=production,USE_GCS=true,GCS_BUCKET_NAME=$GCS_BUCKET,DB_TYPE=postgresql,DB_HOST=/cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME,DB_USER=valuer_app,DB_NAME=valuer_auctions,PROJECT_ID=$PROJECT_ID,INSTANCE_CONNECTION_NAME=$PROJECT_ID:$REGION:$INSTANCE_NAME"
```

### 3. Process the First Five Records

You can either:

A. Use the Cloud Run endpoint (if you've set one up):
```bash
# Get the Cloud Run URL
export SERVICE_URL=$(gcloud run services describe valuer-db-processor --format='value(status.url)')

# Send a request to process the first 5 records
curl -X POST $SERVICE_URL/process-first-five
```

B. Run the script locally but point it to cloud resources:
```bash
# Set environment variables for cloud resources
export USE_GCS=true
export GCS_BUCKET_NAME="valuer-auction-images"
export DB_TYPE="postgresql"
export DB_HOST="localhost" # If using Cloud SQL Auth Proxy locally
export DB_PORT="5432"
export DB_USER="valuer_app"
export DB_PASSWORD="your-password"
export DB_NAME="valuer_auctions"
export PROJECT_ID="your-project-id"
export INSTANCE_CONNECTION_NAME="your-project-id:us-central1:valuer-db"

# Start Cloud SQL Auth Proxy in another terminal
./cloud_sql_proxy -instances=$INSTANCE_CONNECTION_NAME=tcp:5432

# Run the script
python process_first_five.py
```

### 4. Verify Cloud Results

Check that the processing completed successfully in the cloud:

```bash
# Check images in GCS bucket
gcloud storage ls gs://$GCS_BUCKET

# Connect to Cloud SQL and check data
gcloud sql connect $INSTANCE_NAME --user=valuer_app
# Enter password when prompted
# Then run SQL query
SELECT lot_ref, title, photo_path, storage_path FROM auction_lots LIMIT 5;
```

## Troubleshooting

### Local Processing Issues

- **File Not Found Errors**: Ensure the example JSON file is in the correct location
- **Database Errors**: Check if the SQLite database was created properly
- **Image Download Errors**: Check internet connectivity and the BASE_IMAGE_URL in your .env file

### Cloud Processing Issues

- **GCS Upload Errors**: Verify service account permissions for GCS
- **Database Connection Errors**: Check Cloud SQL connection information and permissions
- **Missing Environment Variables**: Make sure all required environment variables are set in Cloud Run
- **Cloud Run Cold Start Issues**: The first request might time out if the container takes too long to start

## Command Line Options

The `process_first_five.py` script supports these command line options:

```
--limit N          Number of records to process (default: 5)
--file PATH        Path to the JSON file (default: example_json.json)
--output DIR       Directory for database output (default: local_data)
--image-dir DIR    Directory for image storage (default: local_images)
--use-gcs          Use Google Cloud Storage instead of local storage
--db-type TYPE     Database type ('sqlite' or 'postgresql')
```

Example with custom options:
```bash
python process_first_five.py --limit 10 --file custom_data.json --image-dir ./images
```