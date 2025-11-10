# FinOps AI Observability POC

> AI-powered AWS cost anomaly detection with real-time observability. Detect cost spikes in minutes, not weeks.

## 🎯 What It Does

- **Detects** cost anomalies using ML (Isolation Forest + statistical methods)
- **Alerts** with actionable insights and severity levels
- **Observes** everything with OpenTelemetry + Prometheus
- **Runs** anywhere with Docker Compose

## 🚀 Quick Start

```bash
docker-compose up -d
open http://localhost:8080
```

**That's it!** Pipeline runs, detects anomalies, generates alerts.

## � Example Results

```
🚨 FINOPS ANOMALY DETECTION REPORT
Analyzed: 181 records | Found: 6 anomalies (3.31%)
Total Cost: $30,199.52 | Anomalous: $3,274.53

Alert: EC2 cost spike
Cost: $585.62 (Avg: $166.85)
Deviation: +251.0%
Methods: Isolation Forest, IQR
```

## 🛠️ Tech Stack

- **ML**: Scikit-learn (Isolation Forest, Z-Score, IQR)
- **Observability**: OpenTelemetry + Prometheus
- **Language**: Python 3.11
- **Deployment**: Docker Compose

## 📁 Structure

```
src/
├── main.py              # Pipeline orchestrator
├── ingestion/           # Data loading
├── ml_detector/         # 4 detection methods
├── alerting/            # Alert generation
└── observability/       # Metrics & traces
```

## 🎯 Key Features

✅ **4 Detection Methods**: Isolation Forest, Z-Score, IQR, Service-level  
✅ **Full Observability**: Every operation traced and measured  
✅ **Actionable Alerts**: Severity levels + recommendations  
✅ **One-Command Deploy**: Docker Compose magic  
✅ **Production-Ready**: Tests, docs, error handling  

## 📖 Docs

- [Architecture](docs/ARCHITECTURE.md) - Technical details
- [Business Impact](docs/BUSINESS_IMPACT.md) - ROI analysis
- [Demo](docs/DEMO.md) - Step-by-step guide

## 💡 Business Impact

**Before**: Cost anomalies discovered 15-30 days late  
**After**: Detected in < 1 hour

**Projected savings**: $50K-$200K/year for mid-size deployments

## 🧪 Run Tests

```bash
make test
```

This POC showcases:
- Modern FinOps practices (proactive vs. reactive)
- Practical AI/ML application (not just theory)
- Cloud-native patterns (observability, automation)
- Engineering leadership (simplicity, portability, impact)

## 📝 License

License - feel free to use for learning and demonstration

---

**Built to demonstrate Principal Engineering Excellence**
*Simplicity • Strategy • Impact*
