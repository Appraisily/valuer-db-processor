#!/usr/bin/env python3
"""
Cloud Setup Script for Valuer DB Processor

This script helps set up the necessary Google Cloud resources for the Valuer DB Processor:
1. Creates a Google Cloud Storage bucket for images
2. Sets up a Cloud SQL PostgreSQL instance
3. Creates the necessary database and tables
4. Configures service accounts and permissions

Run this script once to set up your cloud infrastructure.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cloud_setup")

def run_command(command: str) -> str:
    """
    Run a shell command and return the output
    
    Args:
        command: Shell command to run
        
    Returns:
        Command output as string
    """
    try:
        logger.info(f"Running command: {command}")
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")
        raise

def create_gcs_bucket(bucket_name: str, location: str = "us-central1") -> bool:
    """
    Create a Google Cloud Storage bucket for images
    
    Args:
        bucket_name: Name of the bucket to create
        location: GCS location
        
    Returns:
        True if bucket was created successfully, False otherwise
    """
    try:
        # Check if bucket already exists
        bucket_check = run_command(f"gcloud storage buckets list --filter='name={bucket_name}'")
        if bucket_name in bucket_check:
            logger.info(f"Bucket {bucket_name} already exists.")
            return True
        
        # Create the bucket
        run_command(
            f"gcloud storage buckets create gs://{bucket_name} "
            f"--location={location} "
            f"--default-storage-class=STANDARD "
            f"--uniform-bucket-level-access"
        )
        
        # Make the bucket publicly readable
        run_command(f"gcloud storage buckets add-iam-policy-binding gs://{bucket_name} --member=allUsers --role=roles/storage.objectViewer")
        
        logger.info(f"Created GCS bucket: {bucket_name}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating GCS bucket: {str(e)}")
        return False

def create_cloud_sql_instance(
    instance_name: str, 
    region: str = "us-central1",
    tier: str = "db-f1-micro",
    root_password: str = None
) -> bool:
    """
    Create a Cloud SQL PostgreSQL instance
    
    Args:
        instance_name: Name of the instance to create
        region: GCP region
        tier: Machine type for the instance
        root_password: Password for the root user
        
    Returns:
        True if instance was created successfully, False otherwise
    """
    try:
        # Check if instance already exists
        instance_check = run_command(f"gcloud sql instances list --filter='name={instance_name}'")
        if instance_name in instance_check:
            logger.info(f"SQL instance {instance_name} already exists.")
            return True
        
        # Generate a password if not provided
        if not root_password:
            import uuid
            root_password = f"Valuer-{uuid.uuid4().hex[:8]}"
            logger.info(f"Generated root password: {root_password}")
        
        # Create the instance
        run_command(
            f"gcloud sql instances create {instance_name} "
            f"--tier={tier} "
            f"--region={region} "
            f"--database-version=POSTGRES_14 "
            f"--storage-type=SSD "
            f"--storage-size=10GB "
            f"--availability-type=zonal "
            f"--root-password=\"{root_password}\""
        )
        
        logger.info(f"Created Cloud SQL instance: {instance_name}")
        
        # Create a database
        run_command(f"gcloud sql databases create valuer_auctions --instance={instance_name}")
        
        # Create a user for the application
        app_password = f"App-{uuid.uuid4().hex[:8]}"
        run_command(f"gcloud sql users create valuer_app --instance={instance_name} --password=\"{app_password}\"")
        
        logger.info(f"Created database 'valuer_auctions' and user 'valuer_app'")
        logger.info(f"App user password: {app_password}")
        
        # Output connection info
        logger.info("\nConnection Information:")
        logger.info(f"  Host: {instance_name}")
        logger.info(f"  Database: valuer_auctions")
        logger.info(f"  User: valuer_app")
        logger.info(f"  Password: {app_password}")
        logger.info(f"  Instance Connection Name: PROJECT_ID:{region}:{instance_name}")
        logger.info("\nAdd these to your .env file to connect to Cloud SQL")
        
        return True
    
    except Exception as e:
        logger.error(f"Error creating Cloud SQL instance: {str(e)}")
        return False

def create_service_account(
    project_id: str,
    name: str = "valuer-processor-sa",
    display_name: str = "Valuer DB Processor Service Account"
) -> bool:
    """
    Create a service account for the application
    
    Args:
        project_id: GCP project ID
        name: Service account name
        display_name: Display name for the service account
        
    Returns:
        True if service account was created successfully, False otherwise
    """
    try:
        # Check if service account already exists
        sa_check = run_command(f"gcloud iam service-accounts list --filter='name:{name}' --project={project_id}")
        if name in sa_check:
            logger.info(f"Service account {name} already exists.")
            return True
        
        # Create the service account
        run_command(
            f"gcloud iam service-accounts create {name} "
            f"--display-name=\"{display_name}\" "
            f"--project={project_id}"
        )
        
        # Grant necessary permissions
        email = f"{name}@{project_id}.iam.gserviceaccount.com"
        
        # Grant Storage Object Admin for GCS access
        run_command(
            f"gcloud projects add-iam-policy-binding {project_id} "
            f"--member=\"serviceAccount:{email}\" "
            f"--role=\"roles/storage.objectAdmin\""
        )
        
        # Grant Cloud SQL Client for database access
        run_command(
            f"gcloud projects add-iam-policy-binding {project_id} "
            f"--member=\"serviceAccount:{email}\" "
            f"--role=\"roles/cloudsql.client\""
        )
        
        logger.info(f"Created service account: {email}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating service account: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Set up Google Cloud resources for Valuer DB Processor")
    parser.add_argument("--project-id", type=str, required=True, help="GCP project ID")
    parser.add_argument("--bucket-name", type=str, default="valuer-auction-images", help="Name for the GCS bucket")
    parser.add_argument("--instance-name", type=str, default="valuer-db", help="Name for the Cloud SQL instance")
    parser.add_argument("--region", type=str, default="us-central1", help="GCP region")
    parser.add_argument("--root-password", type=str, help="Root password for Cloud SQL (optional)")
    
    args = parser.parse_args()
    
    logger.info("Starting cloud setup...")
    
    # Set the GCP project
    run_command(f"gcloud config set project {args.project_id}")
    logger.info(f"Set active project to: {args.project_id}")
    
    # Create GCS bucket
    if create_gcs_bucket(args.bucket_name, args.region):
        logger.info("✅ GCS bucket setup complete")
    else:
        logger.error("❌ GCS bucket setup failed")
    
    # Create Cloud SQL instance
    if create_cloud_sql_instance(args.instance_name, args.region, root_password=args.root_password):
        logger.info("✅ Cloud SQL setup complete")
    else:
        logger.error("❌ Cloud SQL setup failed")
    
    # Create service account
    if create_service_account(args.project_id):
        logger.info("✅ Service account setup complete")
    else:
        logger.error("❌ Service account setup failed")
    
    logger.info("\nCloud setup complete. Next steps:")
    logger.info("1. Update your .env file with the Cloud SQL and GCS bucket information")
    logger.info("2. Build and deploy your application to Cloud Run using the gcp-setup-commands.md file")
    logger.info("3. Test processing the first 5 records with 'python process_first_five.py'")

if __name__ == "__main__":
    import uuid
    main()