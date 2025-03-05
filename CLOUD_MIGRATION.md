# Cloud Migration Guide

This guide explains how to move your locally processed auction data to Google Cloud Platform.

## Prerequisites

1. Google Cloud Platform account with the following services enabled:
   - Cloud Storage
   - Cloud SQL (PostgreSQL)

2. Local environment with:
   - Local SQLite database containing processed auction data
   - Downloaded images stored locally
   - Python 3.8+ with required dependencies

3. The following GCP credentials and configuration:
   - GCP service account key file with permissions for:
     - Cloud Storage Admin
     - Cloud SQL Admin
   - GCP project ID
   - Cloud SQL instance name 

## Setup Instructions

### 1. Install Required Dependencies

```bash
pip install -r requirements.txt
# Ensure google-cloud-storage is installed
pip install google-cloud-storage
```

### 2. Set Up GCP Authentication

```bash
# Set the environment variable to point to your service account key file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
```

### 3. Create Cloud Storage Bucket

If you haven't already created a storage bucket for your images:

```bash
# Using the Google Cloud CLI (gcloud)
gcloud storage buckets create gs://YOUR_BUCKET_NAME --location=YOUR_LOCATION
```

### 4. Create Cloud SQL Instance

If you haven't already created a Cloud SQL instance:

```bash
# Using the Google Cloud CLI (gcloud)
gcloud sql instances create YOUR_INSTANCE_NAME \
    --database-version=POSTGRES_13 \
    --cpu=1 \
    --memory=3840MB \
    --region=YOUR_REGION
```

Create a database and user:

```bash
gcloud sql databases create valuer_db --instance=YOUR_INSTANCE_NAME
gcloud sql users create valuer_user --instance=YOUR_INSTANCE_NAME --password=YOUR_PASSWORD
```

### 5. Run the Upload Script

```bash
python upload_to_cloud.py \
    --gcs-bucket "YOUR_BUCKET_NAME" \
    --cloud-sql "postgresql://valuer_user:YOUR_PASSWORD@/valuer_db?host=/cloudsql/YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME" \
    --local-db "./local_data/valuer.db" \
    --batch-size 10
```

For connecting to Cloud SQL from a local environment, you may need to use the Cloud SQL Auth Proxy:

```bash
# Download and run the Cloud SQL Auth Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy_x64.linux -O cloud_sql_proxy
chmod +x cloud_sql_proxy
./cloud_sql_proxy -instances=YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME=tcp:5432

# In another terminal, run the upload script with a standard PostgreSQL connection string:
python upload_to_cloud.py \
    --gcs-bucket "YOUR_BUCKET_NAME" \
    --cloud-sql "postgresql://valuer_user:YOUR_PASSWORD@localhost:5432/valuer_db" \
    --local-db "./local_data/valuer.db" \
    --batch-size 10
```

## Script Behavior

The `upload_to_cloud.py` script performs the following steps:

1. Reads auction lot data from the local SQLite database
2. For each lot with a valid local image:
   - Uploads the image to Google Cloud Storage
   - Updates the lot's `storage_path` to point to the GCS URL
3. Creates or updates the corresponding record in Cloud SQL
4. Processes lots in batches to avoid memory issues with large datasets

Progress and errors are logged to the console.

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

```
Error: Could not automatically determine credentials. Please set GOOGLE_APPLICATION_CREDENTIALS or explicitly create credentials.
```

Ensure that:
- The `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set correctly
- The service account has the necessary permissions
- The service account key file is valid

### Connection Issues

If you encounter connection errors with Cloud SQL:

```
Error: Could not connect to Cloud SQL database
```

Ensure that:
- The connection string is correct
- The Cloud SQL instance is running
- The necessary firewall rules are in place
- You're using the Cloud SQL Auth Proxy for local connections

### Image Upload Issues

If images fail to upload:

```
Error uploading image to GCS
```

Ensure that:
- The bucket exists and you have write permissions
- The local image files exist and are readable
- You have sufficient quota in your GCP project

## After Migration

After migration is complete:

1. Verify that all data has been correctly transferred
2. Update your application to use the Cloud SQL database
3. Update your image references to point to the GCS URLs

## Production Environment Configuration

For a production deployment on Cloud Run:

1. Update your `.env` file or environment variables:

```
# Database
DB_TYPE=postgresql
DATABASE_URL=postgresql://valuer_user:YOUR_PASSWORD@/valuer_db?host=/cloudsql/YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME

# Storage
USE_GCS=true
GCS_BUCKET_NAME=YOUR_BUCKET_NAME

# Cloud SQL Connection
INSTANCE_CONNECTION_NAME=YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME
PROJECT_ID=YOUR_PROJECT_ID
```

2. Update your Dockerfile to include the Cloud SQL Auth Proxy

3. Deploy to Cloud Run with the instance connection name:

```bash
gcloud run deploy valuer-db-processor \
  --image gcr.io/YOUR_PROJECT_ID/valuer-db-processor \
  --platform managed \
  --region YOUR_REGION \
  --add-cloudsql-instances YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME \
  --update-env-vars DB_TYPE=postgresql,USE_GCS=true,GCS_BUCKET_NAME=YOUR_BUCKET_NAME,INSTANCE_CONNECTION_NAME=YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME
```