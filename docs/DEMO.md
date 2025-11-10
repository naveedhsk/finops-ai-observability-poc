# Demo Walkthrough

## Quick Start Demo

This guide walks you through running the complete FinOps AI Observability POC.

### Prerequisites

- Docker & Docker Compose installed
- 5 minutes of your time
- The `aws_costs.csv` file in the `data/` directory

### Step-by-Step Demo

#### 1. Start the Stack

```bash
# One command to rule them all
docker-compose up -d
```

What happens:
- ✅ Prometheus starts (port 9090)
- ✅ Dashboard starts (port 8080)
- ✅ Application builds and starts (port 8000)

#### 2. View the Dashboard

Open your browser to: http://localhost:8080

You'll see:
- 📊 Real-time status of all components
- 🤖 ML detector configuration
- 🎯 Key features overview
- 📚 Quick links to metrics

#### 3. Watch the Logs

```bash
docker-compose logs -f app
```

You'll see:
```
🚀 FINOPS AI OBSERVABILITY POC - STARTING
================================================================================
Timestamp: 2025-11-04 10:00:00
Pipeline: Ingestion → Detection → Alerting
================================================================================

📊 Phase 1: Initializing observability stack...
✅ OpenTelemetry tracer initialized for finops-ai-detector
📊 Prometheus metrics server started on port 8000
✅ Observability initialized

📂 Phase 2: Loading cost data...
📂 Loading cost data from: data/aws_costs.csv
✅ Loaded 184 cost records
   Date range: 2025-01-01 to 2025-06-02
   Total cost: $34,567.89
   Average daily cost: $187.87

🤖 Phase 3: Running ML-based anomaly detection...
🤖 Anomaly Detector initialized
📊 Method 1: Running Isolation Forest...
   ✓ Isolation Forest: 8 anomalies
📊 Method 2: Running Z-Score analysis...
   ✓ Z-Score: 6 anomalies
📊 Method 3: Running IQR analysis...
   ✓ IQR: 7 anomalies
📊 Method 4: Running per-service analysis...
   ✓ Service-level: 5 anomalies
✅ Detection complete:
   - Anomalies found: 9
   - Anomaly cost: $4,234.56
   - Detection rate: 4.89%

📢 Phase 4: Generating alerts...
```

#### 4. View the Alert Report

The console will display a beautiful, formatted report:

```
================================================================================
🚨 FINOPS ANOMALY DETECTION ALERT REPORT 🚨
================================================================================
Generated: 2025-11-04 10:00:15
Total Records Analyzed: 184
Anomalies Detected: 9
Detection Rate: 4.89%
Total Cost Analyzed: $34,567.89
Anomalous Cost: $4,234.56
================================================================================

📊 SEVERITY BREAKDOWN:
   🔴 CRITICAL: 2
   🟠 HIGH:     3
   🟡 MEDIUM:   3
   🟢 LOW:      1

--------------------------------------------------------------------------------
TOP ALERTS (by severity):
--------------------------------------------------------------------------------

🔴 Alert #1: ALERT-20251104-100015-42
   Severity: CRITICAL (Score: 3.50)
   Date: 2025-02-15
   Service: EC2
   Cost: $1,234.56 (Avg: $187.87)
   Deviation: +557.1%
   Confidence: 95%
   Methods: Isolation Forest, Z-Score, IQR, Service-Level
   → ⚠️  IMMEDIATE ACTION REQUIRED: Investigate EC2 cost spike...
```

#### 5. View Prometheus Metrics

Open: http://localhost:9090

Try these queries:

**Total Anomalies Detected:**
```promql
finops_anomalies_detected_total
```

**Processing Time:**
```promql
finops_processing_duration_seconds_sum
```

**Total Cost Analyzed:**
```promql
finops_total_cost_analyzed_usd
```

**Anomaly Amount:**
```promql
finops_anomaly_amount_usd
```

#### 6. Explore the Metrics Endpoint

Open: http://localhost:8000/metrics

You'll see raw Prometheus metrics:
```
# HELP finops_data_ingestion_total Total number of cost records ingested
# TYPE finops_data_ingestion_total counter
finops_data_ingestion_total 184.0

# HELP finops_anomalies_detected_total Total number of cost anomalies detected
# TYPE finops_anomalies_detected_total counter
finops_anomalies_detected_total 9.0

# HELP finops_processing_duration_seconds Time spent processing cost data
# TYPE finops_processing_duration_seconds histogram
finops_processing_duration_seconds_bucket{le="0.1"} 0.0
finops_processing_duration_seconds_bucket{le="0.5"} 1.0
finops_processing_duration_seconds_bucket{le="1.0"} 2.0
```

#### 7. Review Alert JSON

Check the generated JSON report:

```bash
cat alerts/alerts_*.json
```

You'll see:
```json
{
  "generated_at": "2025-11-04T10:00:15.123456",
  "summary": {
    "total_records": 184,
    "anomaly_count": 9,
    "anomaly_rate": 0.0489,
    "total_cost": 34567.89,
    "anomaly_cost": 4234.56
  },
  "alerts": [
    {
      "alert_id": "ALERT-20251104-100015-42",
      "timestamp": "2025-11-04T10:00:15.123456",
      "severity": "CRITICAL",
      "service": "EC2",
      "cost_usd": 1234.56,
      "recommendation": "⚠️  IMMEDIATE ACTION REQUIRED..."
    }
  ]
}
```

#### 8. Run Tests

```bash
make test
```

Or with Docker:

```bash
docker-compose exec app pytest tests/ -v
```

#### 9. Stop the Stack

```bash
docker-compose down
```

## Local Development Demo

Want to run without Docker?

```bash
# Install dependencies
make setup

# Run locally
make run
```

## What to Look For

### 1. Observability in Action
- Every operation has a trace span
- Metrics are recorded in real-time
- Logs are structured and informative

### 2. ML Detection
- Isolation Forest catches unusual patterns
- Statistical methods provide confirmation
- Service-level analysis is granular

### 3. Actionable Alerts
- Severity levels are meaningful
- Recommendations are specific
- JSON format enables automation

### 4. Production-Ready Design
- Clean architecture
- Error handling
- Configuration management
- Testing

## Customization

### Adjust Detection Sensitivity

Edit `src/main.py`:

```python
detector = AnomalyDetector(
    contamination=0.10,       # Expect 10% anomalies (more sensitive)
    z_score_threshold=2.5,    # Lower threshold (more sensitive)
    iqr_multiplier=1.5,       # Standard
    min_samples=5             # Require less data
)
```

### Use Different Data

Replace `data/aws_costs.csv` with your own data:
- Required columns: `date`, `service_name`, `cost_usd`
- Date format: YYYY-MM-DD
- Service: Any string identifier

### Change Output Location

Edit `src/main.py`:

```python
alert_gen = AlertGenerator(output_dir="my_custom_alerts")
```

## Troubleshooting

### Port Already in Use

Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Changed from 8000
```

### No Anomalies Detected

- Check data has enough variation
- Lower the `contamination` parameter
- Reduce `z_score_threshold`
- Verify data has at least `min_samples` records

### Import Errors (Local Run)

```bash
# Make sure you're in the project root
cd /path/to/finops-ai-observability-poc

# Run from src directory
cd src
python main.py
```

## Next Steps

1. **Integrate with Real AWS Data**: Use boto3 to pull from Cost Explorer
2. **Add Slack/Email Alerts**: Extend AlertGenerator
3. **Deploy to Cloud**: Use Kubernetes manifests
4. **Add ML Model Persistence**: Save/load trained models
5. **Build API**: Add FastAPI for real-time queries

## Demo Script (5-minute pitch)

> "Let me show you how this works in 5 minutes..."

1. **[30s]** Show architecture diagram, explain flow
2. **[60s]** `docker-compose up -d` - "One command to deploy everything"
3. **[60s]** Open dashboard - "Real-time observability"
4. **[90s]** Show console output with alert report - "ML detects anomalies automatically"
5. **[60s]** Show Prometheus metrics - "Full instrumentation"
6. **[30s]** Show JSON alert - "Machine-readable for automation"

**Total: 5 minutes. Business value: Clear. Technical depth: Impressive.**
