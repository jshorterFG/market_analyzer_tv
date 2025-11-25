"""
Cold tier storage implementation using Google Cloud Storage Nearline.
Archives data older than 3 months for cost-effective long-term storage.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional
from google.cloud import storage
from google.api_core import exceptions as gcp_exceptions

from config import config
from models import Bar, CacheKey, TimeRange

logger = logging.getLogger(__name__)

class GCSStorage:
    """
    Cold tier storage using GCS Nearline.
    
    Data structure:
    - Bucket: market-analyzer-cache
    - Object path: {screener}/{exchange}/{symbol}/{interval}/{year}/{month}/data.json
    - Storage class: NEARLINE
    """
    
    def __init__(self):
        """Initialize GCS client."""
        try:
            self.client = storage.Client(project=config.gcp.project_id)
            self.bucket_name = config.gcp.gcs_bucket_name
            
            # Get or create bucket
            try:
                self.bucket = self.client.get_bucket(self.bucket_name)
                logger.info(f"Using existing GCS bucket: {self.bucket_name}")
            except gcp_exceptions.NotFound:
                # Create bucket with Nearline storage class
                self.bucket = self.client.create_bucket(
                    self.bucket_name,
                    location=config.gcp.location
                )
                self.bucket.storage_class = "NEARLINE"
                self.bucket.patch()
                logger.info(f"Created GCS bucket: {self.bucket_name} with NEARLINE storage")
                
        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            self.client = None
            self.bucket = None
    
    def _get_blob_path(self, cache_key: CacheKey, year: int, month: int) -> str:
        """Generate blob path for a specific month."""
        return (f"{cache_key.screener}/{cache_key.exchange}/{cache_key.symbol}/"
                f"{cache_key.interval.value}/{year}/{month:02d}/data.json")
    
    def _get_month_from_timestamp(self, timestamp: int) -> tuple[int, int]:
        """Get year and month from timestamp."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.year, dt.month
    
    async def store(self, cache_key: CacheKey, bars: List[Bar]) -> bool:
        """
        Store bars in GCS, partitioned by month.
        
        Args:
            cache_key: Cache key identifying the data
            bars: List of bars to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bucket or not bars:
            return False
        
        try:
            # Group bars by month
            bars_by_month = {}
            for bar in bars:
                year, month = self._get_month_from_timestamp(bar.timestamp)
                month_key = (year, month)
                if month_key not in bars_by_month:
                    bars_by_month[month_key] = []
                bars_by_month[month_key].append(bar)
            
            # Store each month's bars in a separate blob
            for (year, month), month_bars in bars_by_month.items():
                blob_path = self._get_blob_path(cache_key, year, month)
                blob = self.bucket.blob(blob_path)
                
                # Check if blob already exists and merge data
                existing_bars = []
                if blob.exists():
                    try:
                        existing_data = json.loads(blob.download_as_string())
                        existing_bars = [Bar.from_dict(b) for b in existing_data.get("bars", [])]
                    except Exception as e:
                        logger.warning(f"Failed to load existing data from {blob_path}: {e}")
                
                # Merge and deduplicate bars by timestamp
                all_bars = existing_bars + month_bars
                unique_bars = {bar.timestamp: bar for bar in all_bars}.values()
                sorted_bars = sorted(unique_bars, key=lambda b: b.timestamp)
                
                # Prepare data for storage
                data = {
                    "cache_key": cache_key.to_string(),
                    "year": year,
                    "month": month,
                    "bars": [bar.to_dict() for bar in sorted_bars],
                    "cached_at": int(datetime.now().timestamp()),
                    "tier": "cold"
                }
                
                # Upload to GCS
                blob.upload_from_string(
                    json.dumps(data),
                    content_type="application/json"
                )
                
                # Set storage class to NEARLINE if not already
                if blob.storage_class != "NEARLINE":
                    blob.update_storage_class("NEARLINE")
                
                logger.info(f"Stored {len(sorted_bars)} bars to GCS: {blob_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store data in GCS: {e}")
            return False
    
    async def retrieve(self, cache_key: CacheKey, time_range: TimeRange) -> Optional[List[Bar]]:
        """
        Retrieve bars from GCS for the given time range.
        
        Args:
            cache_key: Cache key identifying the data
            time_range: Time range to retrieve
            
        Returns:
            List of bars if found, None otherwise
        """
        if not self.bucket:
            return None
        
        try:
            # Calculate month range
            start_year, start_month = self._get_month_from_timestamp(time_range.start_timestamp)
            end_year, end_month = self._get_month_from_timestamp(time_range.end_timestamp)
            
            all_bars = []
            current_year, current_month = start_year, start_month
            
            # Iterate through each month in the range
            while (current_year, current_month) <= (end_year, end_month):
                blob_path = self._get_blob_path(cache_key, current_year, current_month)
                blob = self.bucket.blob(blob_path)
                
                if blob.exists():
                    try:
                        data = json.loads(blob.download_as_string())
                        bars_data = data.get("bars", [])
                        
                        # Filter bars within the time range
                        for bar_dict in bars_data:
                            bar = Bar.from_dict(bar_dict)
                            if time_range.contains(bar.timestamp):
                                all_bars.append(bar)
                                
                    except Exception as e:
                        logger.warning(f"Failed to load data from {blob_path}: {e}")
                
                # Move to next month
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
            
            if all_bars:
                # Sort by timestamp
                all_bars.sort(key=lambda b: b.timestamp)
                logger.info(f"Retrieved {len(all_bars)} bars from GCS for {cache_key.to_string()}")
                return all_bars
            
            logger.debug(f"No data found in GCS for {cache_key.to_string()}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve data from GCS: {e}")
            return None
    
    async def migrate_from_firestore(self, cache_key: CacheKey, bars: List[Bar]) -> bool:
        """
        Migrate data from Firestore to GCS cold tier.
        
        Args:
            cache_key: Cache key identifying the data
            bars: List of bars to migrate
            
        Returns:
            True if successful, False otherwise
        """
        return await self.store(cache_key, bars)
    
    async def list_cached_months(self, cache_key: CacheKey) -> List[tuple[int, int]]:
        """
        List all months that have cached data for a given key.
        
        Args:
            cache_key: Cache key to check
            
        Returns:
            List of (year, month) tuples
        """
        if not self.bucket:
            return []
        
        try:
            prefix = f"{cache_key.screener}/{cache_key.exchange}/{cache_key.symbol}/{cache_key.interval.value}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            months = set()
            for blob in blobs:
                # Parse year/month from path
                parts = blob.name.split("/")
                if len(parts) >= 6:
                    try:
                        year = int(parts[-3])
                        month = int(parts[-2])
                        months.add((year, month))
                    except ValueError:
                        continue
            
            return sorted(list(months))
            
        except Exception as e:
            logger.error(f"Failed to list cached months from GCS: {e}")
            return []

# Global GCS storage instance
gcs_storage = GCSStorage()
