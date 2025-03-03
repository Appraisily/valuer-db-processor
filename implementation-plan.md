# Valuer DB Processor Implementation Plan

## Overview
This service processes JSON files containing auction data, extracts images referenced in the data, uploads them to Google Cloud Storage (GCS), and stores the structured data in a database. The service will be deployed on Google Cloud Run for scalable, serverless execution.

## JSON Structure Analysis
Based on the example JSON file, we're processing auction data with the following structure:
- Root object contains a `results` array
- Each result contains a `hits` array
- Each hit represents an auction lot with attributes like:
  - `lotNumber`, `lotRef`, `priceResult`, `photoPath` (image URL)
  - `dateTimeLocal`, `dateTimeUTCUnix`
  - `currencyCode`, `currencySymbol`
  - `houseName`, `saleType`, `lotTitle`
  - Additional detailed information in nested objects like `_highlightResult`

## Architecture

### Component Overview
1. **Cloud Run Service** - Main processor service
2. **Cloud Storage** - For storing extracted images
3. **Database** - For storing structured data (Cloud SQL or Firestore)
4. **Secret Manager** - For storing credentials and configuration
5. **Cloud Logging** - For monitoring and debugging

### Service Flow
1. JSON files are received via HTTP endpoint or fetched from a storage location
2. Service parses the JSON and extracts data
3. Images are downloaded from URLs in the `photoPath` field
4. Images are uploaded to a GCS bucket with optimized naming
5. Structured data is saved to the database
6. Service returns success/failure response

## Implementation Details

### 1. Service Setup
- **Language/Framework**: Python with FastAPI for high-performance async processing
- **Container**: Lightweight Docker container with Python 3.10+
- **Deployment**: Cloud Run with CPU and memory allocation optimized for the workload

### 2. Image Processing
- **Download Strategy**: Asynchronous downloads for parallel processing
- **Optimization**: Resize/compress images if needed before storage
- **Storage Path**: `{bucket_name}/{house_name}/{lot_ref}/{filename}`
- **Metadata**: Store original URL as metadata on the GCS object

### 3. Database Design
- **Schema**:
  ```
  lots
    - id (generated UUID or use lotRef)
    - lot_number
    - lot_ref
    - price_result
    - date_time_local
    - date_time_utc_unix
    - currency_code
    - currency_symbol
    - house_name
    - sale_type
    - lot_title
    - object_id
    - image_original_path
    - image_gcs_path
    - highlight_data (JSON field with nested _highlightResult data)
    - ranking_info (JSON field with nested _rankingInfo data)
    - created_at
    - updated_at
  ```

- **Database Options**:
  - **Cloud SQL (PostgreSQL)**: For structured data with complex queries
  - **Firestore**: For more flexible schema and automatic scaling

### 4. Performance Optimization
- **Batch Processing**: Process multiple records in parallel
- **Connection Pooling**: Reuse database connections
- **Caching**: Cache frequently accessed data
- **Rate Limiting**: Implement to avoid hitting API limits
- **Retry Logic**: Implement exponential backoff for failed operations

### 5. Error Handling
- **Validation**: Validate JSON structure before processing
- **Transaction Management**: Use database transactions to ensure data consistency
- **Error Recovery**: Implement dead-letter queue for failed processing attempts
- **Monitoring**: Set up alerts for error thresholds

## Implementation Steps

### Phase 1: Basic Setup and Infrastructure
1. Set up GCP project and enable required APIs
2. Create GCS bucket for image storage
3. Set up database (Cloud SQL or Firestore)
4. Create initial Cloud Run service skeleton
5. Configure CI/CD pipeline for deployment

### Phase 2: Core Functionality
1. Implement JSON parsing and validation
2. Implement image download and upload to GCS
3. Implement database operations for storing auction data
4. Add basic error handling and logging

### Phase 3: Optimization and Monitoring
1. Implement performance optimizations (batching, caching)
2. Add comprehensive error handling
3. Set up monitoring and alerting
4. Implement retry mechanisms and dead-letter queue

### Phase 4: Testing and Deployment
1. Write unit and integration tests
2. Perform load testing
3. Optimize Cloud Run configuration
4. Deploy to production

## Code Structure

```
/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration handling
│   ├── models/              # Data models
│   │   ├── auction_lot.py   # Pydantic models for the data
│   │   └── db_models.py     # Database models
│   ├── services/            # Business logic
│   │   ├── parser.py        # JSON parsing logic
│   │   ├── image_service.py # Image handling logic
│   │   └── db_service.py    # Database operations
│   ├── api/                 # API endpoints
│   │   ├── router.py        # API routing
│   │   └── endpoints/       # API endpoint implementations
│   └── utils/               # Utility functions
│       ├── logging.py       # Logging utilities
│       └── errors.py        # Error handling utilities
├── tests/                   # Test cases
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

## Best Practices

1. **Security**:
   - Use service accounts with minimal permissions
   - Store secrets in Secret Manager
   - Implement input validation to prevent injection attacks

2. **Scalability**:
   - Design for horizontal scaling
   - Use connection pooling
   - Implement backoff strategies for external services

3. **Reliability**:
   - Add comprehensive logging
   - Implement circuit breakers for external dependencies
   - Use transactions for data consistency

4. **Performance**:
   - Optimize database queries
   - Use asynchronous processing where appropriate
   - Implement caching for frequently accessed data

## Monitoring and Maintenance

1. **Monitoring**:
   - Set up Cloud Monitoring dashboards
   - Configure alerts for error rates and performance thresholds
   - Track resource usage and costs

2. **Maintenance**:
   - Regular dependency updates
   - Database index optimization
   - Periodic review of GCS data retention policies

## Estimated Timeline

1. **Phase 1**: 1-2 days
2. **Phase 2**: 3-5 days
3. **Phase 3**: 2-3 days
4. **Phase 4**: 2-3 days

Total: 8-13 days depending on complexity and requirements 