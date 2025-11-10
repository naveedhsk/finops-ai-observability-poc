"""
FinOps AI Observability POC - Main Pipeline
Orchestrates the complete anomaly detection workflow
"""
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from observability.metrics import setup_observability, start_metrics_server
from ingestion.loader import CostDataLoader
from ml_detector.detector import AnomalyDetector
from alerting.alert_generator import AlertGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('finops_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """
    Main pipeline execution
    
    Flow:
    1. Initialize observability (OpenTelemetry + Prometheus)
    2. Load cost data with full instrumentation
    3. Detect anomalies using ML + statistical methods
    4. Generate and display alerts
    """
    
    print("\n" + "="*80)
    print("🚀 FINOPS AI OBSERVABILITY POC - STARTING")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pipeline: Ingestion → Detection → Alerting")
    print("="*80 + "\n")
    
    try:
        # =================================================================
        # PHASE 1: Initialize Observability
        # =================================================================
        logger.info("📊 Phase 1: Initializing observability stack...")
        tracer = setup_observability(service_name="finops-ai-detector")
        start_metrics_server(port=8000)
        logger.info("✅ Observability initialized")
        
        # =================================================================
        # PHASE 2: Data Ingestion
        # =================================================================
        logger.info("\n📂 Phase 2: Loading cost data...")
        
        # Define data path
        data_path = Path("data/aws_costs.csv")
        
        if not data_path.exists():
            logger.error(f"❌ Data file not found: {data_path}")
            logger.info("💡 Please ensure aws_costs.csv is in the data/ directory")
            sys.exit(1)
        
        # Initialize loader
        loader = CostDataLoader(
            data_path=str(data_path),
            date_column='date',
            cost_column='cost_usd'
        )
        
        # Load data
        cost_data = loader.load_data()
        logger.info(f"✅ Data ingestion complete: {len(cost_data)} records")
        
        # =================================================================
        # PHASE 3: Anomaly Detection
        # =================================================================
        logger.info("\n🤖 Phase 3: Running ML-based anomaly detection...")
        
        # Initialize detector
        detector = AnomalyDetector(
            contamination=0.05,      # Expect ~5% anomalies
            z_score_threshold=3.0,   # 3 standard deviations
            iqr_multiplier=1.5,      # Standard IQR method
            min_samples=7            # At least 1 week of data
        )
        
        # Detect anomalies
        results = detector.detect_anomalies(
            data=cost_data,
            date_column='date',
            cost_column='cost_usd',
            service_column='service_name'
        )
        
        # Get summary
        summary = detector.get_anomaly_summary(results)
        logger.info(f"✅ Anomaly detection complete")
        
        # =================================================================
        # PHASE 4: Alert Generation
        # =================================================================
        logger.info("\n📢 Phase 4: Generating alerts...")
        
        # Initialize alert generator
        alert_gen = AlertGenerator(output_dir="alerts")
        
        # Generate alerts
        alerts = alert_gen.generate_alerts(
            data=results,
            summary=summary,
            save_to_file=True
        )
        
        logger.info(f"✅ Alert generation complete")
        
        # =================================================================
        # PIPELINE COMPLETE
        # =================================================================
        print("\n" + "="*80)
        print("✅ PIPELINE EXECUTION COMPLETE")
        print("="*80)
        print(f"Total Records: {len(cost_data)}")
        print(f"Anomalies Found: {summary.get('anomaly_count', 0)}")
        print(f"Alerts Generated: {len(alerts)}")
        print(f"Metrics Available: http://localhost:8000/metrics")
        print(f"Dashboard: http://localhost:8080")
        print("="*80 + "\n")
        
        logger.info("🎉 Pipeline execution successful!")
        
        # Keep metrics server running
        logger.info("📊 Metrics server is running. Press Ctrl+C to stop.")
        print("💡 Prometheus metrics are being exposed at http://localhost:8000/metrics")
        print("   You can scrape these with Prometheus or view them directly.\n")
        
        # Keep the process alive so metrics can be scraped
        try:
            import time
            while True:
                time.sleep(60)
                logger.info("📊 Pipeline is idle, metrics server running...")
        except KeyboardInterrupt:
            logger.info("👋 Shutting down gracefully...")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        print("\n" + "="*80)
        print("❌ PIPELINE EXECUTION FAILED")
        print("="*80)
        print(f"Error: {e}")
        print("Check finops_pipeline.log for details")
        print("="*80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
