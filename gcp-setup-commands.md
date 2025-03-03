# Google Cloud Setup Commands for Valuer DB Processor

## Project Configuration
```bash
# Set the project
gcloud config set project civil-forge-403609

# Verify the active project
gcloud config get-value project
```

## Create Google Cloud Storage Bucket
```bash
# Create a new GCS bucket for storing images
# Replace 'valuer-auction-images' with your preferred bucket name
gcloud storage buckets create gs://valuer-auction-images \
    --location=us-central1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Verify bucket creation
gcloud storage buckets list
```

## Create Cloud SQL PostgreSQL Instance
```bash
# Create a PostgreSQL instance
# Note: This will incur costs as long as the instance is running
gcloud sql instances create valuer-db \
    --tier=db-f1-micro \
    --region=us-central1 \
    --database-version=POSTGRES_14 \
    --storage-type=SSD \
    --storage-size=10GB \
    --availability-type=zonal \
    --root-password="REPLACE_WITH_SECURE_PASSWORD"

# Create a database
gcloud sql databases create valuer_auctions \
    --instance=valuer-db

# Create a user for the application
gcloud sql users create valuer_app \
    --instance=valuer-db \
    --password="REPLACE_WITH_SECURE_APP_PASSWORD"
```

## Create Service Account for Cloud Run
```bash
# Create a service account for the Cloud Run service
gcloud iam service-accounts create valuer-processor-sa \
    --display-name="Valuer DB Processor Service Account"

# Grant necessary permissions to the service account
# Storage Object Admin for GCS access
gcloud projects add-iam-policy-binding civil-forge-403609 \
    --member="serviceAccount:valuer-processor-sa@civil-forge-403609.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Cloud SQL Client for database access
gcloud projects add-iam-policy-binding civil-forge-403609 \
    --member="serviceAccount:valuer-processor-sa@civil-forge-403609.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

## Configure Cloud Run
```bash
# Build and deploy the Cloud Run service
# Make sure you're in the directory with your Dockerfile
gcloud builds submit --tag gcr.io/civil-forge-403609/valuer-db-processor

# Deploy to Cloud Run
gcloud run deploy valuer-db-processor \
    --image gcr.io/civil-forge-403609/valuer-db-processor \
    --platform managed \
    --region us-central1 \
    --service-account valuer-processor-sa@civil-forge-403609.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars="ENV=production,GCS_BUCKET=valuer-auction-images,DB_NAME=valuer_auctions,DB_USER=valuer_app,PROJECT_ID=civil-forge-403609,DB_INSTANCE=valuer-db" \
    --set-secrets="DB_PASSWORD=valuer-db-password:latest" \
    --add-cloudsql-instances=civil-forge-403609:us-central1:valuer-db
```

## Set up Secret Manager for Database Password
```bash
# Create a secret for the database password
gcloud secrets create valuer-db-password \
    --replication-policy="automatic"

# Add the database password to the secret
echo -n "REPLACE_WITH_SECURE_APP_PASSWORD" | \
    gcloud secrets versions add valuer-db-password --data-file=-

# Grant the service account access to the secret
gcloud secrets add-iam-policy-binding valuer-db-password \
    --member="serviceAccount:valuer-processor-sa@civil-forge-403609.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Setup Monitoring
```bash
# Create a notification channel (email)
gcloud beta monitoring channels create \
    --display-name="Valuer Processor Alerts" \
    --type=email \
    --channel-labels=email_address="your-email@example.com"

# Get the channel ID
CHANNEL_ID=$(gcloud beta monitoring channels list --format="value(name)" --filter="displayName=Valuer Processor Alerts")

# Create an alert policy for error logs
gcloud alpha monitoring policies create \
    --display-name="Valuer Processor Error Alert" \
    --condition-filter="resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"valuer-db-processor\" AND severity>=ERROR" \
    --condition-threshold-duration=0s \
    --notification-channels=$CHANNEL_ID \
    --documentation-format=text \
    --documentation-content="High error rate detected in Valuer DB Processor. Please investigate."
```

## Important Notes
1. Replace all placeholder passwords with actual secure passwords
2. The Cloud SQL instance will incur charges as long as it's running
3. Consider setting up regular backups for your database
4. You may need to adjust resource allocations (CPU, memory) based on your workload
5. Make sure the `.env` file in your application is updated to use these new GCP resources 