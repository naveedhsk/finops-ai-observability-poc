"""
Alert Generation System
Creates actionable alerts from detected anomalies
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import pandas as pd
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AlertGenerator:
    """
    Generates alerts for cost anomalies with full observability
    
    Output formats:
    - Console (formatted, human-readable)
    - JSON (machine-readable, for integration)
    - Summary statistics
    """
    
    def __init__(self, output_dir: str = "alerts"):
        """
        Initialize alert generator
        
        Args:
            output_dir: Directory to save alert reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"📢 Alert Generator initialized")
        logger.info(f"   Output directory: {self.output_dir}")
    
    def generate_alerts(
        self,
        data: pd.DataFrame,
        summary: Dict,
        save_to_file: bool = True
    ) -> List[Dict]:
        """
        Generate alerts from anomaly detection results
        
        Args:
            data: DataFrame with detection results
            summary: Summary statistics from detector
            save_to_file: Whether to save alerts to JSON file
            
        Returns:
            List of alert dictionaries
        """
        with tracer.start_as_current_span("generate_alerts") as span:
            try:
                logger.info(f"📢 Generating alerts...")
                
                if 'is_anomaly' not in data.columns:
                    logger.warning("⚠️  No anomaly detection results found")
                    return []
                
                anomalies = data[data['is_anomaly']].copy()
                
                if len(anomalies) == 0:
                    logger.info("✅ No anomalies detected - all costs within normal range!")
                    span.set_attribute("alerts.count", 0)
                    return []
                
                # Generate alerts
                alerts = []
                for idx, row in anomalies.iterrows():
                    alert = self._create_alert(row, data)
                    alerts.append(alert)
                
                # Sort by severity
                alerts.sort(key=lambda x: x['severity_score'], reverse=True)
                
                span.set_attribute("alerts.count", len(alerts))
                span.set_attribute("alerts.critical", sum(1 for a in alerts if a['severity'] == 'CRITICAL'))
                span.set_attribute("alerts.high", sum(1 for a in alerts if a['severity'] == 'HIGH'))
                
                # Display alerts
                self._display_alerts(alerts, summary)
                
                # Save to file
                if save_to_file:
                    self._save_alerts(alerts, summary)
                
                logger.info(f"✅ Generated {len(alerts)} alerts")
                
                return alerts
                
            except Exception as e:
                logger.error(f"❌ Alert generation failed: {e}")
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    
    def _create_alert(self, row: pd.Series, full_data: pd.DataFrame) -> Dict:
        """
        Create a structured alert from an anomaly
        
        Args:
            row: Anomaly row from detection results
            full_data: Full dataset for context
            
        Returns:
            Alert dictionary
        """
        # Calculate severity
        cost = row.get('cost_usd', 0)
        confidence = row.get('confidence', 0)
        anomaly_score = row.get('anomaly_score', 0)
        
        # Severity calculation
        severity_score = confidence * anomaly_score
        
        if severity_score >= 3.0:
            severity = "CRITICAL"
        elif severity_score >= 2.0:
            severity = "HIGH"
        elif severity_score >= 1.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # Calculate deviation from normal
        avg_cost = full_data['cost_usd'].mean() if 'cost_usd' in full_data.columns else 0
        deviation_pct = ((cost - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
        
        # Detection methods that flagged this
        methods = []
        if row.get('if_anomaly', False):
            methods.append("Isolation Forest")
        if row.get('zscore_anomaly', False):
            methods.append("Z-Score")
        if row.get('iqr_anomaly', False):
            methods.append("IQR")
        if row.get('service_anomaly', False):
            methods.append("Service-Level")
        
        alert = {
            "alert_id": f"ALERT-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{row.name}",
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "severity_score": float(severity_score),
            "date": str(row.get('date', '')),
            "service": row.get('service_name', 'Unknown'),
            "cost_usd": float(cost),
            "average_cost": float(avg_cost),
            "deviation_pct": float(deviation_pct),
            "confidence": float(confidence),
            "detection_methods": methods,
            "details": {
                "anomaly_score": int(anomaly_score),
                "zscore": float(row.get('zscore', 0)),
                "if_score": float(row.get('if_score', 0)),
                "iqr_lower": float(row.get('iqr_lower', 0)),
                "iqr_upper": float(row.get('iqr_upper', 0))
            },
            "recommendation": self._get_recommendation(severity, row)
        }
        
        return alert
    
    def _get_recommendation(self, severity: str, row: pd.Series) -> str:
        """Generate actionable recommendation based on severity"""
        service = row.get('service_name', 'Unknown')
        cost = row.get('cost_usd', 0)
        
        if severity == "CRITICAL":
            return f"⚠️  IMMEDIATE ACTION REQUIRED: Investigate {service} cost spike of ${cost:.2f}. Check for unauthorized usage, misconfigurations, or runaway processes."
        elif severity == "HIGH":
            return f"⚡ HIGH PRIORITY: Review {service} costs. Verify this usage was planned. Consider setting up cost alerts and budget limits."
        elif severity == "MEDIUM":
            return f"📊 REVIEW RECOMMENDED: Monitor {service} for continued elevated costs. Document if this is expected seasonal variation."
        else:
            return f"ℹ️  FYI: Slight variation in {service} costs detected. No immediate action required but keep monitoring."
    
    def _display_alerts(self, alerts: List[Dict], summary: Dict):
        """Display alerts in a formatted console output"""
        
        print("\n" + "="*80)
        print("🚨 FINOPS ANOMALY DETECTION ALERT REPORT 🚨")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Records Analyzed: {summary.get('total_records', 0)}")
        print(f"Anomalies Detected: {summary.get('anomaly_count', 0)}")
        print(f"Detection Rate: {summary.get('anomaly_rate', 0)*100:.2f}%")
        print(f"Total Cost Analyzed: ${summary.get('total_cost', 0):,.2f}")
        print(f"Anomalous Cost: ${summary.get('anomaly_cost', 0):,.2f}")
        print("="*80)
        
        if not alerts:
            print("\n✅ No anomalies detected - all costs within normal range!")
            print("="*80 + "\n")
            return
        
        # Group by severity
        critical = [a for a in alerts if a['severity'] == 'CRITICAL']
        high = [a for a in alerts if a['severity'] == 'HIGH']
        medium = [a for a in alerts if a['severity'] == 'MEDIUM']
        low = [a for a in alerts if a['severity'] == 'LOW']
        
        print(f"\n📊 SEVERITY BREAKDOWN:")
        print(f"   🔴 CRITICAL: {len(critical)}")
        print(f"   🟠 HIGH:     {len(high)}")
        print(f"   🟡 MEDIUM:   {len(medium)}")
        print(f"   🟢 LOW:      {len(low)}")
        
        print("\n" + "-"*80)
        print("TOP ALERTS (by severity):")
        print("-"*80)
        
        for i, alert in enumerate(alerts[:10], 1):  # Show top 10
            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }
            
            print(f"\n{severity_emoji.get(alert['severity'], '⚪')} Alert #{i}: {alert['alert_id']}")
            print(f"   Severity: {alert['severity']} (Score: {alert['severity_score']:.2f})")
            print(f"   Date: {alert['date']}")
            print(f"   Service: {alert['service']}")
            print(f"   Cost: ${alert['cost_usd']:,.2f} (Avg: ${alert['average_cost']:,.2f})")
            print(f"   Deviation: {alert['deviation_pct']:+.1f}%")
            print(f"   Confidence: {alert['confidence']*100:.0f}%")
            print(f"   Methods: {', '.join(alert['detection_methods'])}")
            print(f"   → {alert['recommendation']}")
        
        if len(alerts) > 10:
            print(f"\n... and {len(alerts) - 10} more alerts (see JSON report for full details)")
        
        print("\n" + "="*80)
        
        # Detection methods summary
        methods_used = summary.get('methods_used', {})
        if methods_used:
            print("\n🔍 DETECTION METHODS PERFORMANCE:")
            for method, count in methods_used.items():
                print(f"   - {method.replace('_', ' ').title()}: {count} detections")
        
        # Per-service breakdown
        if 'by_service' in summary:
            print("\n📦 ANOMALIES BY SERVICE:")
            for service, stats in summary['by_service'].items():
                if stats['anomaly_count'] > 0:
                    print(f"   - {service}: {stats['anomaly_count']}/{stats['total_records']} "
                          f"({stats['anomaly_rate']*100:.1f}%)")
        
        print("\n" + "="*80 + "\n")
    
    def _save_alerts(self, alerts: List[Dict], summary: Dict):
        """Save alerts to JSON file"""
        with tracer.start_as_current_span("save_alerts"):
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = self.output_dir / f"alerts_{timestamp}.json"
                
                report = {
                    "generated_at": datetime.now().isoformat(),
                    "summary": summary,
                    "alerts": alerts,
                    "alert_count": len(alerts),
                    "severity_distribution": {
                        "critical": sum(1 for a in alerts if a['severity'] == 'CRITICAL'),
                        "high": sum(1 for a in alerts if a['severity'] == 'HIGH'),
                        "medium": sum(1 for a in alerts if a['severity'] == 'MEDIUM'),
                        "low": sum(1 for a in alerts if a['severity'] == 'LOW')
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2)
                
                logger.info(f"💾 Alert report saved: {filename}")
                print(f"📄 Full report saved to: {filename}")
                
            except Exception as e:
                logger.error(f"❌ Failed to save alerts: {e}")
