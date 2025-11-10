"""
AI/ML Anomaly Detection Engine
Uses Isolation Forest and statistical methods to detect cost anomalies
"""
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from opentelemetry import trace

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from observability.metrics import record_anomaly, processing_duration

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AnomalyDetector:
    """
    Multi-method anomaly detection with full observability
    
    Methods:
    1. Isolation Forest (Unsupervised ML) - detects outliers in cost patterns
    2. Statistical Z-Score - identifies data points beyond threshold
    3. IQR Method - detects outliers using interquartile range
    4. Service-level Analysis - per-service anomaly detection
    """
    
    def __init__(
        self,
        contamination: float = 0.05,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_samples: int = 7
    ):
        """
        Initialize the anomaly detector
        
        Args:
            contamination: Expected proportion of outliers (for Isolation Forest)
            z_score_threshold: Number of std deviations for z-score method
            iqr_multiplier: Multiplier for IQR method (1.5 = standard)
            min_samples: Minimum samples required for detection
        """
        self.contamination = contamination
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_samples = min_samples
        
        # ML Models
        self.isolation_forest = None
        self.scaler = StandardScaler()
        
        logger.info(f"🤖 Anomaly Detector initialized")
        logger.info(f"   - Contamination: {contamination*100:.1f}%")
        logger.info(f"   - Z-score threshold: {z_score_threshold}")
        logger.info(f"   - IQR multiplier: {iqr_multiplier}")
    
    @processing_duration.time()
    def detect_anomalies(
        self,
        data: pd.DataFrame,
        date_column: str = 'date',
        cost_column: str = 'cost_usd',
        service_column: str = 'service_name'
    ) -> pd.DataFrame:
        """
        Detect anomalies using multiple methods
        
        Args:
            data: DataFrame with cost data
            date_column: Name of date column
            cost_column: Name of cost column
            service_column: Name of service column
            
        Returns:
            DataFrame with anomaly detection results
        """
        with tracer.start_as_current_span("detect_anomalies") as span:
            try:
                logger.info(f"🔍 Starting anomaly detection on {len(data)} records")
                span.set_attribute("detection.records", len(data))
                
                if len(data) < self.min_samples:
                    logger.warning(f"⚠️  Insufficient data: {len(data)} < {self.min_samples} samples")
                    return self._create_empty_results(data)
                
                # Add a copy to avoid modifying original
                results = data.copy()
                
                # Method 1: Isolation Forest (Global)
                logger.info("📊 Method 1: Running Isolation Forest...")
                results = self._isolation_forest_detection(results, cost_column)
                
                # Method 2: Statistical Z-Score
                logger.info("📊 Method 2: Running Z-Score analysis...")
                results = self._zscore_detection(results, cost_column)
                
                # Method 3: IQR Method
                logger.info("📊 Method 3: Running IQR analysis...")
                results = self._iqr_detection(results, cost_column)
                
                # Method 4: Service-level analysis (if service column exists)
                if service_column in results.columns:
                    logger.info("📊 Method 4: Running per-service analysis...")
                    results = self._service_level_detection(results, cost_column, service_column)
                
                # Aggregate anomaly flags
                results = self._aggregate_anomaly_flags(results)
                
                # Log summary
                anomaly_count = results['is_anomaly'].sum()
                anomaly_cost = results[results['is_anomaly']][cost_column].sum()
                
                span.set_attribute("detection.anomalies_found", int(anomaly_count))
                span.set_attribute("detection.anomaly_cost", float(anomaly_cost))
                
                logger.info(f"✅ Detection complete:")
                logger.info(f"   - Anomalies found: {anomaly_count}")
                logger.info(f"   - Anomaly cost: ${anomaly_cost:,.2f}")
                logger.info(f"   - Detection rate: {anomaly_count/len(data)*100:.2f}%")
                
                # Record metrics for each anomaly
                if anomaly_count > 0:
                    for _, row in results[results['is_anomaly']].iterrows():
                        record_anomaly(
                            amount=row[cost_column],
                            threshold=results[cost_column].mean()
                        )
                
                return results
                
            except Exception as e:
                logger.error(f"❌ Anomaly detection failed: {e}")
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    
    def _isolation_forest_detection(self, data: pd.DataFrame, cost_column: str) -> pd.DataFrame:
        """
        Use Isolation Forest (unsupervised ML) to detect anomalies
        
        Isolation Forest works by:
        - Building random trees that isolate observations
        - Anomalies are easier to isolate (shorter paths)
        - Perfect for high-dimensional data without labels
        """
        with tracer.start_as_current_span("isolation_forest"):
            try:
                # Prepare features
                X = data[[cost_column]].values
                
                # Scale the data
                X_scaled = self.scaler.fit_transform(X)
                
                # Train Isolation Forest
                self.isolation_forest = IsolationForest(
                    contamination=self.contamination,
                    random_state=42,
                    n_estimators=100
                )
                
                # Predict (-1 for anomalies, 1 for normal)
                predictions = self.isolation_forest.fit_predict(X_scaled)
                
                # Get anomaly scores (lower = more anomalous)
                scores = self.isolation_forest.score_samples(X_scaled)
                
                data['if_anomaly'] = predictions == -1
                data['if_score'] = scores
                
                logger.info(f"   ✓ Isolation Forest: {data['if_anomaly'].sum()} anomalies")
                
                return data
                
            except Exception as e:
                logger.warning(f"   ⚠️  Isolation Forest failed: {e}")
                data['if_anomaly'] = False
                data['if_score'] = 0.0
                return data
    
    def _zscore_detection(self, data: pd.DataFrame, cost_column: str) -> pd.DataFrame:
        """
        Statistical Z-Score method
        
        Z-score = (x - mean) / std
        Points with |z-score| > threshold are anomalies
        """
        with tracer.start_as_current_span("zscore_detection"):
            try:
                costs = data[cost_column]
                mean = costs.mean()
                std = costs.std()
                
                if std == 0:
                    logger.warning("   ⚠️  Zero standard deviation, skipping z-score")
                    data['zscore_anomaly'] = False
                    data['zscore'] = 0.0
                    return data
                
                # Calculate z-scores
                z_scores = np.abs((costs - mean) / std)
                
                data['zscore'] = z_scores
                data['zscore_anomaly'] = z_scores > self.z_score_threshold
                
                logger.info(f"   ✓ Z-Score: {data['zscore_anomaly'].sum()} anomalies")
                
                return data
                
            except Exception as e:
                logger.warning(f"   ⚠️  Z-Score failed: {e}")
                data['zscore_anomaly'] = False
                data['zscore'] = 0.0
                return data
    
    def _iqr_detection(self, data: pd.DataFrame, cost_column: str) -> pd.DataFrame:
        """
        Interquartile Range (IQR) method
        
        IQR = Q3 - Q1
        Outliers are outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
        """
        with tracer.start_as_current_span("iqr_detection"):
            try:
                costs = data[cost_column]
                
                Q1 = costs.quantile(0.25)
                Q3 = costs.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - self.iqr_multiplier * IQR
                upper_bound = Q3 + self.iqr_multiplier * IQR
                
                data['iqr_anomaly'] = (costs < lower_bound) | (costs > upper_bound)
                data['iqr_lower'] = lower_bound
                data['iqr_upper'] = upper_bound
                
                logger.info(f"   ✓ IQR: {data['iqr_anomaly'].sum()} anomalies")
                logger.info(f"      Range: [${lower_bound:.2f}, ${upper_bound:.2f}]")
                
                return data
                
            except Exception as e:
                logger.warning(f"   ⚠️  IQR failed: {e}")
                data['iqr_anomaly'] = False
                return data
    
    def _service_level_detection(
        self,
        data: pd.DataFrame,
        cost_column: str,
        service_column: str
    ) -> pd.DataFrame:
        """
        Per-service anomaly detection
        
        Detects anomalies within each service independently
        More granular than global detection
        """
        with tracer.start_as_current_span("service_level_detection"):
            try:
                data['service_anomaly'] = False
                
                for service in data[service_column].unique():
                    service_data = data[data[service_column] == service]
                    
                    if len(service_data) < self.min_samples:
                        continue
                    
                    # Calculate service-specific statistics
                    service_costs = service_data[cost_column]
                    service_mean = service_costs.mean()
                    service_std = service_costs.std()
                    
                    if service_std == 0:
                        continue
                    
                    # Z-score within service
                    service_z = np.abs((service_costs - service_mean) / service_std)
                    service_anomalies = service_z > self.z_score_threshold
                    
                    # Update main dataframe
                    data.loc[service_data.index, 'service_anomaly'] = service_anomalies.values
                
                logger.info(f"   ✓ Service-level: {data['service_anomaly'].sum()} anomalies")
                
                return data
                
            except Exception as e:
                logger.warning(f"   ⚠️  Service-level failed: {e}")
                data['service_anomaly'] = False
                return data
    
    def _aggregate_anomaly_flags(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate anomaly flags from multiple methods
        
        A point is considered an anomaly if detected by 2+ methods
        This reduces false positives while maintaining sensitivity
        """
        with tracer.start_as_current_span("aggregate_flags"):
            # Count how many methods flagged each point
            anomaly_columns = [
                col for col in data.columns
                if col.endswith('_anomaly')
            ]
            
            data['anomaly_score'] = data[anomaly_columns].sum(axis=1)
            
            # Require 2+ methods to agree (consensus approach)
            data['is_anomaly'] = data['anomaly_score'] >= 2
            
            # Add confidence level
            data['confidence'] = data['anomaly_score'] / len(anomaly_columns)
            
            return data
    
    def _create_empty_results(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create empty results when detection can't run"""
        results = data.copy()
        results['if_anomaly'] = False
        results['zscore_anomaly'] = False
        results['iqr_anomaly'] = False
        results['service_anomaly'] = False
        results['is_anomaly'] = False
        results['anomaly_score'] = 0
        results['confidence'] = 0.0
        return results
    
    def get_anomaly_summary(self, data: pd.DataFrame) -> Dict:
        """
        Generate summary statistics of detected anomalies
        
        Args:
            data: DataFrame with detection results
            
        Returns:
            Dictionary with anomaly statistics
        """
        with tracer.start_as_current_span("anomaly_summary"):
            if 'is_anomaly' not in data.columns:
                return {"error": "No anomaly detection results found"}
            
            anomalies = data[data['is_anomaly']]
            
            summary = {
                "total_records": len(data),
                "anomaly_count": len(anomalies),
                "anomaly_rate": len(anomalies) / len(data) if len(data) > 0 else 0,
                "total_cost": float(data['cost_usd'].sum()) if 'cost_usd' in data.columns else 0,
                "anomaly_cost": float(anomalies['cost_usd'].sum()) if 'cost_usd' in anomalies.columns else 0,
                "methods_used": {
                    "isolation_forest": int(data['if_anomaly'].sum()) if 'if_anomaly' in data.columns else 0,
                    "zscore": int(data['zscore_anomaly'].sum()) if 'zscore_anomaly' in data.columns else 0,
                    "iqr": int(data['iqr_anomaly'].sum()) if 'iqr_anomaly' in data.columns else 0,
                    "service_level": int(data['service_anomaly'].sum()) if 'service_anomaly' in data.columns else 0
                }
            }
            
            # Add per-service breakdown if available
            if 'service_name' in data.columns:
                service_summary = {}
                for service in data['service_name'].unique():
                    service_data = data[data['service_name'] == service]
                    service_anomalies = service_data[service_data['is_anomaly']]
                    service_summary[service] = {
                        "total_records": len(service_data),
                        "anomaly_count": len(service_anomalies),
                        "anomaly_rate": len(service_anomalies) / len(service_data) if len(service_data) > 0 else 0
                    }
                summary["by_service"] = service_summary
            
            return summary
