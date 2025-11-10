"""
Observability Metrics Setup
Configures OpenTelemetry and Prometheus for the entire pipeline
"""
import logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from opentelemetry import trace, metrics as otel_metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus Metrics
data_ingestion_counter = Counter(
    'finops_data_ingestion_total',
    'Total number of cost records ingested'
)

anomaly_detection_counter = Counter(
    'finops_anomalies_detected_total',
    'Total number of cost anomalies detected'
)

anomaly_amount_gauge = Gauge(
    'finops_anomaly_amount_usd',
    'Dollar amount of detected anomaly'
)

processing_duration = Histogram(
    'finops_processing_duration_seconds',
    'Time spent processing cost data',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

cost_analyzed_gauge = Gauge(
    'finops_total_cost_analyzed_usd',
    'Total cost amount analyzed'
)

# OpenTelemetry Setup
def setup_observability(service_name: str = "finops-ai-detector"):
    """
    Initialize OpenTelemetry with tracing and metrics
    
    Args:
        service_name: Name of the service for identification
    """
    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "poc"
    })
    
    # Setup tracing
    trace.set_tracer_provider(TracerProvider(resource=resource))
    logger.info(f"✅ OpenTelemetry tracer initialized for {service_name}")
    
    # Setup metrics
    otel_metrics.set_meter_provider(MeterProvider(resource=resource))
    logger.info(f"✅ OpenTelemetry metrics initialized for {service_name}")
    
    return trace.get_tracer(__name__)

def start_metrics_server(port: int = 8000):
    """
    Start Prometheus metrics server
    
    Args:
        port: Port to expose metrics on
    """
    try:
        start_http_server(port)
        logger.info(f"📊 Prometheus metrics server started on port {port}")
        logger.info(f"   View metrics at: http://localhost:{port}/metrics")
    except OSError as e:
        logger.warning(f"⚠️  Metrics server port {port} already in use: {e}")

def record_ingestion(count: int):
    """Record data ingestion metrics"""
    data_ingestion_counter.inc(count)
    logger.info(f"📥 Ingested {count} cost records")

def record_anomaly(amount: float, threshold: float):
    """Record anomaly detection metrics"""
    anomaly_detection_counter.inc()
    anomaly_amount_gauge.set(amount)
    logger.warning(f"🚨 Anomaly detected! Amount: ${amount:.2f} (threshold: ${threshold:.2f})")

def record_cost_analyzed(total_cost: float):
    """Record total cost analyzed"""
    cost_analyzed_gauge.set(total_cost)
    logger.info(f"💰 Total cost analyzed: ${total_cost:,.2f}")
