"""
Data Ingestion Module
Loads AWS cost data with full observability instrumentation
"""
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from opentelemetry import trace
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from observability.metrics import record_ingestion, record_cost_analyzed, processing_duration

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class CostDataLoader:
    """
    Loads and validates AWS cost data from CSV files
    Fully instrumented with OpenTelemetry traces and Prometheus metrics
    """
    
    def __init__(self, data_path: str, date_column: str = 'date', cost_column: str = 'cost'):
        """
        Initialize the data loader
        
        Args:
            data_path: Path to the CSV file containing cost data
            date_column: Name of the date column
            cost_column: Name of the cost column
        """
        self.data_path = Path(data_path)
        self.date_column = date_column
        self.cost_column = cost_column
        self.data: Optional[pd.DataFrame] = None
        
    @processing_duration.time()
    def load_data(self) -> pd.DataFrame:
        """
        Load cost data from CSV with validation and instrumentation
        
        Returns:
            DataFrame with parsed dates and validated costs
        """
        with tracer.start_as_current_span("load_cost_data") as span:
            try:
                logger.info(f"📂 Loading cost data from: {self.data_path}")
                span.set_attribute("data.source", str(self.data_path))
                
                # Check file exists
                if not self.data_path.exists():
                    raise FileNotFoundError(f"Cost data file not found: {self.data_path}")
                
                # Load CSV
                self.data = pd.read_csv(self.data_path)
                span.set_attribute("data.rows.raw", len(self.data))
                
                # Validate required columns
                self._validate_columns()
                
                # Parse dates
                self.data[self.date_column] = pd.to_datetime(self.data[self.date_column])
                
                # Ensure cost is numeric
                self.data[self.cost_column] = pd.to_numeric(self.data[self.cost_column], errors='coerce')
                
                # Remove any rows with invalid data
                initial_count = len(self.data)
                self.data = self.data.dropna(subset=[self.date_column, self.cost_column])
                final_count = len(self.data)
                
                if initial_count > final_count:
                    logger.warning(f"⚠️  Dropped {initial_count - final_count} rows with invalid data")
                
                # Sort by date
                self.data = self.data.sort_values(self.date_column).reset_index(drop=True)
                
                # Calculate metrics
                total_cost = self.data[self.cost_column].sum()
                date_range = f"{self.data[self.date_column].min().date()} to {self.data[self.date_column].max().date()}"
                
                # Record observability metrics
                record_ingestion(final_count)
                record_cost_analyzed(total_cost)
                
                span.set_attribute("data.rows.valid", final_count)
                span.set_attribute("data.total_cost", total_cost)
                span.set_attribute("data.date_range", date_range)
                
                logger.info(f"✅ Loaded {final_count} cost records")
                logger.info(f"   Date range: {date_range}")
                logger.info(f"   Total cost: ${total_cost:,.2f}")
                logger.info(f"   Average daily cost: ${total_cost/final_count:,.2f}")
                
                return self.data
                
            except Exception as e:
                logger.error(f"❌ Failed to load cost data: {e}")
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    
    def _validate_columns(self):
        """Validate that required columns exist"""
        required_cols = [self.date_column, self.cost_column]
        missing_cols = [col for col in required_cols if col not in self.data.columns]
        
        if missing_cols:
            available_cols = ', '.join(self.data.columns)
            raise ValueError(
                f"Missing required columns: {missing_cols}. "
                f"Available columns: {available_cols}"
            )
    
    def get_date_range(self) -> tuple:
        """Get the date range of the loaded data"""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        return (
            self.data[self.date_column].min(),
            self.data[self.date_column].max()
        )
    
    def get_summary_stats(self) -> dict:
        """
        Get summary statistics of the cost data
        
        Returns:
            Dictionary with summary statistics
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        costs = self.data[self.cost_column]
        
        return {
            'total_records': len(self.data),
            'total_cost': costs.sum(),
            'average_cost': costs.mean(),
            'median_cost': costs.median(),
            'min_cost': costs.min(),
            'max_cost': costs.max(),
            'std_dev': costs.std(),
            'date_range_start': self.data[self.date_column].min().date(),
            'date_range_end': self.data[self.date_column].max().date()
        }
