# Cloud Run Setup Guide

This guide walks through the process of setting up Google Cloud Platform resources and deploying the Valuer DB Processor to Cloud Run.

## Prerequisites

1. Google Cloud Platform account with billing enabled
2. `gcloud` CLI tool installed and configured
3. Docker installed (for local testing of the container)
4. Successfully tested the application locally (see [LOCAL_TESTING.md](LOCAL_TESTING.md))

## Setup Steps

### 1. Set Up GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Set the active project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable sql.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Create Cloud Resources

Run the setup script to create the required cloud resources:

```bash
python setup_cloud.py --project-id $PROJECT_ID --bucket-name "valuer-auction-images" --instance-name "valuer-db" --region "us-central1"
```

This script will:
1. Create a GCS bucket for storing images
2. Create a Cloud SQL PostgreSQL instance
3. Create a database and user in the PostgreSQL instance
4. Create a service account with necessary permissions

### 3. Configure Environment for Cloud Run

Create a `.env.cloud` file with the Cloud SQL and GCS information:

```bash
cp .env.cloud .env.cloud.local

# Edit .env.cloud.local and update the values with your actual GCP resource information
# Replace PROJECT_ID, REGION, INSTANCE_NAME, DB_PASSWORD with your actual values
```

### 4. Build and Deploy the Container

```bash
# Build the container image
gcloud builds submit --tag gcr.io/$PROJECT_ID/valuer-db-processor

# Deploy to Cloud Run
gcloud run deploy valuer-db-processor \
  --image gcr.io/$PROJECT_ID/valuer-db-processor \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars="ENV=production,GCS_BUCKET=valuer-auction-images,USE_GCS=true,DB_TYPE=postgresql,DB_USER=valuer_app,DB_NAME=valuer_auctions,PROJECT_ID=$PROJECT_ID" \
  --set-secrets="DB_PASSWORD=valuer-db-password:latest" \
  --add-cloudsql-instances=$PROJECT_ID:us-central1:valuer-db
```

### 5. Set Up Secret Manager

To securely store the database password:

```bash
# Create a secret for the database password
gcloud secrets create valuer-db-password \
  --replication-policy="automatic"

# Add the database password to the secret
echo -n "your-db-password-here" | \
  gcloud secrets versions add valuer-db-password --data-file=-

# Grant the Cloud Run service account access to the secret
gcloud secrets add-iam-policy-binding valuer-db-password \
  --member="serviceAccount:valuer-processor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 6. Process the First 5 Items in the Cloud

```bash
# Set up environment variables for the Cloud Run service
gcloud run services update valuer-db-processor \
  --set-env-vars="INSTANCE_CONNECTION_NAME=$PROJECT_ID:us-central1:valuer-db"

# Trigger processing of the first 5 items
curl -X POST https://YOUR_CLOUD_RUN_URL/process-first-five
```

Replace `YOUR_CLOUD_RUN_URL` with the URL of your deployed Cloud Run service.

### 7. Verify Cloud Deployment

Check that the data was processed successfully:

1. **Check Cloud SQL database**:
   ```bash
   # Connect to Cloud SQL instance
   gcloud sql connect valuer-db --user=valuer_app
   # Enter password when prompted
   
   # Check for data in the auction_lots table
   SELECT COUNT(*) FROM auction_lots;
   ```

2. **Check GCS bucket**:
   ```bash
   # List files in the GCS bucket
   gcloud storage ls gs://valuer-auction-images
   ```

3. **Check Cloud Run logs**:
   ```bash
   # View logs from the Cloud Run service
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=valuer-db-processor" --limit 50
   ```

## Troubleshooting

### Cloud SQL Connection Issues

If the application can't connect to Cloud SQL:
- Verify that the Cloud SQL proxy is running in the container
- Check the `INSTANCE_CONNECTION_NAME` environment variable
- Ensure the service account has the Cloud SQL Client role
- Check the DB_HOST environment variable (should be /cloudsql/PROJECT_ID:REGION:INSTANCE_NAME)

### GCS Storage Issues

If images aren't uploading properly:
- Check the `GCS_BUCKET_NAME` environment variable
- Ensure the service account has the Storage Object Admin role
- Check for permission errors in the logs

### Container Startup Issues

If the container fails to start:
- Check the Cloud Run logs for any error messages
- Verify that all required environment variables are set
- Check the Docker container locally:
  ```bash
  docker pull gcr.io/$PROJECT_ID/valuer-db-processor
  docker run -it gcr.io/$PROJECT_ID/valuer-db-processor /bin/bash
  ```

## Additional Configuration

### Set Up Monitoring

Configure Cloud Monitoring for your deployed service:

```bash
# Create a notification channel (email)
gcloud beta monitoring channels create \
  --display-name="Valuer Processor Alerts" \
  --type=email \
  --channel-labels=email_address="your-email@example.com"

# Get the channel ID
export CHANNEL_ID=$(gcloud beta monitoring channels list --format="value(name)" --filter="displayName=Valuer Processor Alerts")

# Create an alert policy for error logs
gcloud alpha monitoring policies create \
  --display-name="Valuer Processor Error Alert" \
  --condition-filter="resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"valuer-db-processor\" AND severity>=ERROR" \
  --condition-threshold-duration=0s \
  --notification-channels=$CHANNEL_ID \
  --documentation-format=text \
  --documentation-content="High error rate detected in Valuer DB Processor. Please investigate."
```

### Schedule Regular Processing

Set up a Cloud Scheduler job to regularly process new auction data:

```bash
# Create a service account for the scheduler
gcloud iam service-accounts create scheduler-sa \
  --display-name="Cloud Scheduler Service Account"

# Grant the service account permission to invoke Cloud Run
gcloud run services add-iam-policy-binding valuer-db-processor \
  --member="serviceAccount:scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create a scheduler job to run daily
gcloud scheduler jobs create http process-auctions-daily \
  --schedule="0 0 * * *" \
  --uri="https://YOUR_CLOUD_RUN_URL/process" \
  --http-method=POST \
  --oidc-service-account-email="scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience="https://YOUR_CLOUD_RUN_URL/process"
```

Replace `YOUR_CLOUD_RUN_URL` with the URL of your deployed Cloud Run service.