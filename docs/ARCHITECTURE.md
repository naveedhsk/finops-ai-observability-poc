# Architecture Deep Dive

## System Architecture

The FinOps AI Observability POC implements a modern, observable data pipeline for detecting cost anomalies in AWS infrastructure.

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     FinOps AI Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Ingestion  │─────▶│  ML Detector │─────▶│   Alerting   │  │
│  │              │      │              │      │              │  │
│  │  CSV Parser  │      │ Isolation    │      │ Console +    │  │
│  │  Validation  │      │ Forest       │      │ JSON Output  │  │
│  │  Metrics     │      │ Z-Score      │      │ Severity     │  │
│  └──────┬───────┘      │ IQR          │      └──────┬───────┘  │
│         │              │ Service-Level│             │           │
│         │              └──────┬───────┘             │           │
│         │                     │                     │           │
│         └─────────────────────┴─────────────────────┘           │
│                               │                                  │
│                    ┌──────────▼──────────┐                      │
│                    │   Observability     │                      │
│                    │                     │                      │
│                    │ - OpenTelemetry     │                      │
│                    │ - Prometheus        │                      │
│                    │ - Structured Logs   │                      │
│                    └─────────────────────┘                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Ingestion Phase
- **Input**: CSV file with columns: `date`, `service_name`, `cost_usd`
- **Processing**: 
  - Date parsing and validation
  - Numeric type conversion
  - Missing data handling
  - Time-series sorting
- **Output**: Clean pandas DataFrame
- **Observability**: 
  - Span: `load_cost_data`
  - Metrics: `finops_data_ingestion_total`
  - Histogram: `finops_processing_duration_seconds`

### 2. Detection Phase
- **Input**: Clean cost data
- **Processing**: Four parallel detection methods
  
  #### 2a. Isolation Forest
  - **Algorithm**: Unsupervised ML (Scikit-learn)
  - **Method**: Builds random decision trees to isolate anomalies
  - **Advantage**: No training data required, handles high dimensions
  - **Output**: Anomaly flag + score
  
  #### 2b. Z-Score Statistical
  - **Algorithm**: Statistical normalization
  - **Method**: `z = (x - μ) / σ`, flag if |z| > threshold (default 3)
  - **Advantage**: Simple, interpretable, handles gaussian distributions
  - **Output**: Z-score + anomaly flag
  
  #### 2c. IQR (Interquartile Range)
  - **Algorithm**: Robust statistical method
  - **Method**: Outliers outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`
  - **Advantage**: Resistant to outliers in calculation
  - **Output**: Bounds + anomaly flag
  
  #### 2d. Service-Level Analysis
  - **Algorithm**: Per-service Z-score
  - **Method**: Analyze each AWS service independently
  - **Advantage**: Detects service-specific anomalies
  - **Output**: Service anomaly flag

- **Aggregation**: Consensus approach (2+ methods must agree)
- **Output**: Enriched DataFrame with anomaly flags and scores
- **Observability**:
  - Span: `detect_anomalies` (parent)
  - Child spans: `isolation_forest`, `zscore_detection`, `iqr_detection`, `service_level_detection`
  - Metrics: `finops_anomalies_detected_total`
  - Gauge: `finops_anomaly_amount_usd`

### 3. Alert Phase
- **Input**: Detection results + summary statistics
- **Processing**:
  - Severity calculation (CRITICAL/HIGH/MEDIUM/LOW)
  - Deviation percentage computation
  - Recommendation generation
  - Alert formatting
- **Output**: 
  - Console report (formatted, colorized)
  - JSON file (machine-readable)
- **Observability**:
  - Span: `generate_alerts`
  - Attributes: alert counts by severity

## ML Model Details

### Isolation Forest

**Why Isolation Forest?**
- Specifically designed for anomaly detection
- Unsupervised (no labeled training data needed)
- Works well with high-dimensional data
- Fast and efficient

**How it works:**
1. Randomly select a feature
2. Randomly select a split value between min/max
3. Build tree until all points isolated
4. Anomalies have shorter path lengths (easier to isolate)

**Parameters:**
- `contamination`: Expected proportion of outliers (0.05 = 5%)
- `n_estimators`: Number of trees (100 for balance of speed/accuracy)
- `random_state`: 42 (reproducibility)

**Output:**
- Score: Lower = more anomalous (typically -0.5 to +0.5)
- Prediction: -1 (anomaly) or +1 (normal)

### Statistical Methods

**Z-Score:**
- Formula: `z = (x - μ) / σ`
- Threshold: |z| > 3.0 (99.7% confidence interval)
- Best for: Normally distributed data

**IQR:**
- Formula: `IQR = Q3 - Q1`
- Bounds: `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`
- Best for: Skewed distributions, robust to outliers

## Observability Stack

### OpenTelemetry
- **Traces**: Distributed tracing across all operations
- **Context Propagation**: Parent-child span relationships
- **Attributes**: Rich metadata (record counts, costs, errors)
- **Sampling**: All traces captured (100% sampling rate)

### Prometheus
- **Metrics Types**:
  - Counter: `finops_data_ingestion_total`, `finops_anomalies_detected_total`
  - Gauge: `finops_total_cost_analyzed_usd`, `finops_anomaly_amount_usd`
  - Histogram: `finops_processing_duration_seconds`
- **Scrape Interval**: 15 seconds
- **Retention**: 15 days (default)

### Logging
- **Format**: Structured logs with timestamps
- **Levels**: INFO (default), WARNING (issues), ERROR (failures)
- **Handlers**: Console (stdout) + File (finops_pipeline.log)
- **Emojis**: Visual indicators for quick scanning

## Design Decisions

### Why Pandas?
- Industry standard for data manipulation
- Efficient for medium-sized datasets (< 1M rows)
- Rich ecosystem and documentation
- Easy integration with scikit-learn

### Why Scikit-learn?
- Battle-tested ML library
- Simple API, well-documented
- Isolation Forest implementation is robust
- No deep learning complexity needed

### Why OpenTelemetry?
- Vendor-neutral observability standard
- Future-proof (CNCF project)
- Flexible backends (Jaeger, Zipkin, etc.)
- Industry momentum

### Why Docker Compose?
- Single-command deployment
- Reproducible environments
- Easy service orchestration
- Perfect for POCs and demos

## Scalability Considerations

**Current Implementation:**
- In-memory processing (suitable for < 100K records)
- Single-machine execution
- Batch processing

**Production Evolution:**
- Replace Pandas with Spark/Dask for distributed processing
- Add streaming support (Kafka/Kinesis)
- Scale detection horizontally with Kubernetes
- Add ML model versioning (MLflow)
- Implement model retraining pipeline
- Add data lake integration (S3/Delta Lake)

## Security & Compliance

**Current State:**
- No authentication (POC only)
- Local file access

**Production Requirements:**
- API authentication (OAuth2/JWT)
- Encryption at rest and in transit
- Audit logging
- RBAC for alert management
- Secrets management (Vault/KMS)
- Compliance reporting (SOC2, GDPR)

## Performance Characteristics

**Throughput:**
- 1,000 records/second (single machine)
- O(n log n) complexity for Isolation Forest
- Linear scaling for statistical methods

**Latency:**
- End-to-end: ~1-5 seconds for 1,000 records
- Detection: ~0.5-2 seconds
- Alerting: < 100ms

**Memory:**
- ~50MB for 10,000 records
- Scales linearly with data size
