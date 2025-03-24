# Local Testing Guide

This guide explains how to process the first 10 items from the example JSON file locally, allowing you to test the entire pipeline before deploying to the cloud.

## Setup Environment

First, create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Process First 10 Items

We'll modify the existing `process_first_five.py` script to process 10 items instead of 5:

```bash
# Run with max-lots parameter set to 10
python process_first_five.py --max-lots 10 --input-file example_json.json --output-dir local_data --image-dir local_images
```

This command will:
1. Parse the first 10 auction items from the example JSON file
2. Create a local SQLite database in the `local_data` directory
3. Download and process images to the `local_images` directory
4. Store all metadata in the database

## Verify Results

### Check the Database

You can use SQLite tools to examine the database:

```bash
# Install sqlite3 if not already available
# apt-get install sqlite3

# Open the database
sqlite3 local_data/valuer.db

# View tables
.tables

# View first 10 items in the lots table
SELECT * FROM lots LIMIT 10;

# Exit SQLite
.quit
```

### Check Downloaded Images

The images should be stored in the `local_images` directory with a structure like:
```
local_images/
├── house_name_1/
│   └── lot_ref_1/
│       └── image_1.jpg
├── house_name_2/
│   └── lot_ref_2/
│       └── image_2.jpg
...
```

You can check the image count with:
```bash
find local_images -type f | wc -l
```

### Check Database Size

Check the size of the SQLite database:
```bash
du -h local_data/valuer.db
```

### Check Images Size

Check the total size of downloaded images:
```bash
du -h -s local_images
```

## Creating the Local Schema

If needed, you can manually create the database schema:

```bash
python create_tables.py --db-path local_data/valuer.db
```

## Next Steps

After successful local testing, you can:

1. Run the full process on all items
   ```bash
   python process_auctions.py --input-file example_json.json --output-dir local_data
   ```

2. Upload processed data to the cloud
   ```bash
   python upload_to_cloud.py --gcs-bucket "your-bucket-name" --cloud-sql "your-connection-string" --local-db "local_data/valuer.db"
   ```

3. Follow the GitHub workflow outlined in `github-publish-instructions.md` to deploy the application to GCP