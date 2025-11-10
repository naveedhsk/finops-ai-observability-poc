"""
End-to-End Tests for FinOps AI Observability POC
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ingestion.loader import CostDataLoader
from ml_detector.detector import AnomalyDetector
from alerting.alert_generator import AlertGenerator


class TestDataIngestion:
    """Test data ingestion module"""
    
    def test_load_data(self, tmp_path):
        """Test successful data loading"""
        # Create test CSV
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            'service_name': ['EC2'] * 10,
            'cost_usd': [100 + i for i in range(10)]
        })
        
        test_file = tmp_path / "test_costs.csv"
        test_data.to_csv(test_file, index=False)
        
        # Load data
        loader = CostDataLoader(
            data_path=str(test_file),
            date_column='date',
            cost_column='cost_usd'
        )
        
        result = loader.load_data()
        
        assert len(result) == 10
        assert 'date' in result.columns
        assert 'cost_usd' in result.columns
        assert result['cost_usd'].sum() > 0
    
    def test_load_missing_file(self):
        """Test handling of missing file"""
        loader = CostDataLoader(data_path="nonexistent.csv")
        
        with pytest.raises(FileNotFoundError):
            loader.load_data()
    
    def test_data_validation(self, tmp_path):
        """Test data validation and cleaning"""
        # Create test CSV with invalid data
        test_data = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-02', 'invalid', '2025-01-04'],
            'service_name': ['EC2', 'RDS', 'S3', 'Lambda'],
            'cost_usd': [100, 200, 'invalid', 300]
        })
        
        test_file = tmp_path / "test_invalid.csv"
        test_data.to_csv(test_file, index=False)
        
        loader = CostDataLoader(str(test_file))
        result = loader.load_data()
        
        # Should drop invalid rows
        assert len(result) < len(test_data)
        assert result['cost_usd'].dtype in [np.float64, np.int64]


class TestAnomalyDetection:
    """Test ML anomaly detection"""
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        detector = AnomalyDetector(
            contamination=0.1,
            z_score_threshold=3.0
        )
        
        assert detector.contamination == 0.1
        assert detector.z_score_threshold == 3.0
    
    def test_anomaly_detection_with_outliers(self):
        """Test detection with clear outliers"""
        # Create data with obvious anomaly
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=30),
            'service_name': ['EC2'] * 30,
            'cost_usd': [100] * 29 + [1000]  # Last value is anomaly
        })
        
        detector = AnomalyDetector(contamination=0.1)
        results = detector.detect_anomalies(data)
        
        assert 'is_anomaly' in results.columns
        assert results['is_anomaly'].sum() > 0
        
        # The high cost should be flagged
        assert results.iloc[-1]['is_anomaly'] == True
    
    def test_anomaly_detection_no_outliers(self):
        """Test detection with no outliers"""
        # Create uniform data
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=30),
            'service_name': ['EC2'] * 30,
            'cost_usd': [100 + np.random.normal(0, 2) for _ in range(30)]
        })
        
        detector = AnomalyDetector(contamination=0.05)
        results = detector.detect_anomalies(data)
        
        # Should detect few or no anomalies
        assert results['is_anomaly'].sum() <= len(data) * 0.1
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=3),
            'service_name': ['EC2'] * 3,
            'cost_usd': [100, 110, 105]
        })
        
        detector = AnomalyDetector(min_samples=7)
        results = detector.detect_anomalies(data)
        
        # Should return safely without errors
        assert len(results) == len(data)
    
    def test_service_level_detection(self):
        """Test per-service anomaly detection"""
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=20),
            'service_name': ['EC2'] * 10 + ['RDS'] * 10,
            'cost_usd': [100] * 9 + [500] + [50] * 9 + [300]
        })
        
        detector = AnomalyDetector(min_samples=5)
        results = detector.detect_anomalies(data)
        
        # Should detect anomalies in both services
        ec2_anomalies = results[results['service_name'] == 'EC2']['is_anomaly'].sum()
        rds_anomalies = results[results['service_name'] == 'RDS']['is_anomaly'].sum()
        
        assert ec2_anomalies > 0 or rds_anomalies > 0
    
    def test_anomaly_summary(self):
        """Test anomaly summary generation"""
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=20),
            'service_name': ['EC2'] * 20,
            'cost_usd': [100] * 19 + [500]
        })
        
        detector = AnomalyDetector()
        results = detector.detect_anomalies(data)
        summary = detector.get_anomaly_summary(results)
        
        assert 'total_records' in summary
        assert 'anomaly_count' in summary
        assert 'anomaly_rate' in summary
        assert summary['total_records'] == 20


class TestAlertGeneration:
    """Test alert generation"""
    
    def test_alert_generator_initialization(self, tmp_path):
        """Test alert generator initialization"""
        alert_gen = AlertGenerator(output_dir=str(tmp_path / "alerts"))
        
        assert alert_gen.output_dir.exists()
    
    def test_generate_alerts_with_anomalies(self, tmp_path):
        """Test alert generation with anomalies"""
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            'service_name': ['EC2'] * 10,
            'cost_usd': [100] * 9 + [500],
            'is_anomaly': [False] * 9 + [True],
            'confidence': [0.0] * 9 + [0.9],
            'anomaly_score': [0] * 9 + [3]
        })
        
        summary = {
            'total_records': 10,
            'anomaly_count': 1,
            'anomaly_rate': 0.1
        }
        
        alert_gen = AlertGenerator(output_dir=str(tmp_path / "alerts"))
        alerts = alert_gen.generate_alerts(data, summary, save_to_file=True)
        
        assert len(alerts) == 1
        assert alerts[0]['severity'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert 'alert_id' in alerts[0]
        assert 'recommendation' in alerts[0]
    
    def test_generate_alerts_no_anomalies(self, tmp_path):
        """Test alert generation with no anomalies"""
        data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            'service_name': ['EC2'] * 10,
            'cost_usd': [100] * 10,
            'is_anomaly': [False] * 10
        })
        
        summary = {
            'total_records': 10,
            'anomaly_count': 0,
            'anomaly_rate': 0.0
        }
        
        alert_gen = AlertGenerator(output_dir=str(tmp_path / "alerts"))
        alerts = alert_gen.generate_alerts(data, summary)
        
        assert len(alerts) == 0


class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_full_pipeline(self, tmp_path):
        """Test complete pipeline: load → detect → alert"""
        # Create test data
        test_data = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=30),
            'service_name': ['EC2'] * 15 + ['RDS'] * 15,
            'cost_usd': [100] * 14 + [500] + [50] * 14 + [300]
        })
        
        test_file = tmp_path / "test_costs.csv"
        test_data.to_csv(test_file, index=False)
        
        # Phase 1: Load
        loader = CostDataLoader(str(test_file))
        cost_data = loader.load_data()
        assert len(cost_data) == 30
        
        # Phase 2: Detect
        detector = AnomalyDetector(min_samples=10)
        results = detector.detect_anomalies(cost_data)
        assert 'is_anomaly' in results.columns
        
        # Phase 3: Alert
        summary = detector.get_anomaly_summary(results)
        alert_gen = AlertGenerator(output_dir=str(tmp_path / "alerts"))
        alerts = alert_gen.generate_alerts(results, summary, save_to_file=True)
        
        # Verify alerts were generated for anomalies
        if results['is_anomaly'].sum() > 0:
            assert len(alerts) > 0
        
        # Verify alert files were created
        alert_files = list(alert_gen.output_dir.glob("*.json"))
        assert len(alert_files) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
