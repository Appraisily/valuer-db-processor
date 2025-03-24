# GitHub Workflow for Auction Data Processing

This document outlines how to set up a GitHub-based workflow for processing auction data locally and deploying to Google Cloud Platform.

## Overall Workflow

1. Process auction data locally (parse JSONs, download images)
2. Create database tables locally
3. Push code and processed data to GitHub
4. Deploy to Google Cloud Platform (GCS and PostgreSQL)

## Setup Steps

### 1. Local Development and Processing

```bash
# Clone the repository
git clone https://github.com/yourusername/valuer-db-processor.git
cd valuer-db-processor

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Process auction data locally
python process_auctions.py --input-file example_json.json --output-dir local_data

# Download and process images locally
python download_images.py --input-dir local_data --output-dir local_images

# Create local database tables
python create_tables.py --db-path local_data/valuer.db
```

### 2. Preparing for Cloud Deployment

Create a `.env.example` file with the following structure (no actual secrets):

```
# Database Configuration
DB_TYPE=postgresql
DATABASE_URL=postgresql://username:password@/dbname?host=/cloudsql/project:region:instance

# Storage Configuration
USE_GCS=true
GCS_BUCKET_NAME=your-bucket-name

# Cloud SQL Connection
INSTANCE_CONNECTION_NAME=project:region:instance
PROJECT_ID=your-project-id
```

### 3. GitHub Repository Setup

1. Create a new repository on GitHub
2. Add your code and processed data (excluding large binary files)
3. Use `.gitignore` to exclude:
   - Large binary files
   - Sensitive information
   - Local environment files

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit with processed auction data"
git branch -M main
git remote add origin https://github.com/yourusername/valuer-db-processor.git
git push -u origin main
```

### 4. Setting Up GitHub Actions for Cloud Deployment

Create a GitHub Actions workflow file at `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Google Cloud

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        project_id: ${{ secrets.GCP_PROJECT_ID }}
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        export_default_credentials: true
        
    - name: Create GCS bucket if not exists
      run: |
        gsutil ls -b gs://${{ secrets.GCS_BUCKET_NAME }} || \
        gsutil mb -l us-central1 gs://${{ secrets.GCS_BUCKET_NAME }}
        
    - name: Build and push Docker image
      run: |
        gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/valuer-db-processor
        
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy valuer-db-processor \
          --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/valuer-db-processor \
          --platform managed \
          --region us-central1 \
          --add-cloudsql-instances ${{ secrets.INSTANCE_CONNECTION_NAME }} \
          --update-env-vars DB_TYPE=postgresql,USE_GCS=true,GCS_BUCKET_NAME=${{ secrets.GCS_BUCKET_NAME }},INSTANCE_CONNECTION_NAME=${{ secrets.INSTANCE_CONNECTION_NAME }}
```

### 5. Setting Up GitHub Secrets

In your GitHub repository:
1. Go to Settings > Secrets and variables > Actions
2. Add the following secrets:
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: The JSON key for your service account (base64 encoded)
   - `GCS_BUCKET_NAME`: Your GCS bucket name
   - `INSTANCE_CONNECTION_NAME`: Your Cloud SQL instance connection name

### 6. Upload Processed Data to Cloud

Create a separate workflow for uploading processed data:

```yaml
name: Upload Data to Cloud

on:
  workflow_dispatch:

jobs:
  upload:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        project_id: ${{ secrets.GCP_PROJECT_ID }}
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        export_default_credentials: true
        
    - name: Upload images to GCS
      run: |
        python upload_to_cloud.py \
          --gcs-bucket "${{ secrets.GCS_BUCKET_NAME }}" \
          --cloud-sql "${{ secrets.CLOUD_SQL_CONNECTION_STRING }}" \
          --local-db "./local_data/valuer.db" \
          --batch-size 10
```

## Benefits of This Approach

1. **Local Processing**: Compute-intensive tasks run locally
2. **Version Control**: Code and configuration tracked in Git
3. **CI/CD**: Automated deployment with GitHub Actions
4. **Secrets Management**: Secure handling of credentials
5. **Scalability**: Cloud-based hosting of processed data
6. **Separation of Concerns**: Processing separate from hosting
7. **Reproducibility**: Documented workflow for future runs
8. **Collaboration**: Multiple team members can contribute

## Next Steps

1. Develop a monitoring strategy for your Cloud Run service
2. Set up scheduled runs for processing new auction data
3. Implement backup and disaster recovery procedures
4. Consider adding unit and integration tests
5. Establish a development/staging/production workflow