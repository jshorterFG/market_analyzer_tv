"""
Hot tier storage implementation using Cloud Firestore.
Stores recent data (last 3 months) for fast access.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from google.cloud import firestore
from google.api_core import exceptions as gcp_exceptions

from config import config
from models import Bar, CacheKey, TimeRange, CachedData

logger = logging.getLogger(__name__)

class FirestoreStorage:
    """
    Hot tier storage using Cloud Firestore.
    
    Data structure:
    - Collection: market_data
    - Document ID: {screener}:{exchange}:{symbol}:{interval}:{date}
    - Fields: bars (array), cached_at, tier
    """
    
    def __init__(self):
        """Initialize Firestore client."""
        try:
            self.db = firestore.Client(
                project=config.gcp.project_id,
                database=config.gcp.firestore_database
            )
            self.collection = self.db.collection("market_data")
            logger.info(f"Firestore initialized: project={config.gcp.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.collection = None
    
    def _get_document_id(self, cache_key: CacheKey, date: datetime) -> str:
        """Generate document ID for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        return f"{cache_key.to_string()}:{date_str}"
    
    def _get_date_from_timestamp(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to date."""
        return datetime.fromtimestamp(timestamp).replace(hour=0, minute=0, second=0, microsecond=0)
    
    async def store(self, cache_key: CacheKey, bars: List[Bar]) -> bool:
        """
        Store bars in Firestore, partitioned by date.
        
        Args:
            cache_key: Cache key identifying the data
            bars: List of bars to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db or not bars:
            return False
        
        try:
            # Group bars by date
            bars_by_date = {}
            for bar in bars:
                date = self._get_date_from_timestamp(bar.timestamp)
                date_key = date.strftime("%Y-%m-%d")
                if date_key not in bars_by_date:
                    bars_by_date[date_key] = []
                bars_by_date[date_key].append(bar)
            
            # Store each date's bars in a separate document
            batch = self.db.batch()
            current_time = int(datetime.now().timestamp())
            
            for date_str, date_bars in bars_by_date.items():
                date = datetime.strptime(date_str, "%Y-%m-%d")
                doc_id = self._get_document_id(cache_key, date)
                doc_ref = self.collection.document(doc_id)
                
                data = {
                    "cache_key": cache_key.to_string(),
                    "date": date_str,
                    "bars": [bar.to_dict() for bar in date_bars],
                    "cached_at": current_time,
                    "tier": "hot"
                }
                
                batch.set(doc_ref, data, merge=True)
            
            batch.commit()
            logger.info(f"Stored {len(bars)} bars across {len(bars_by_date)} documents for {cache_key.to_string()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store data in Firestore: {e}")
            return False
    
    async def retrieve(self, cache_key: CacheKey, time_range: TimeRange) -> Optional[List[Bar]]:
        """
        Retrieve bars from Firestore for the given time range.
        
        Args:
            cache_key: Cache key identifying the data
            time_range: Time range to retrieve
            
        Returns:
            List of bars if found, None otherwise
        """
        if not self.db:
            return None
        
        try:
            # Calculate date range
            start_date = self._get_date_from_timestamp(time_range.start_timestamp)
            end_date = self._get_date_from_timestamp(time_range.end_timestamp)
            
            all_bars = []
            current_date = start_date
            
            # Query each date in the range
            while current_date <= end_date:
                doc_id = self._get_document_id(cache_key, current_date)
                doc_ref = self.collection.document(doc_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    data = doc.to_dict()
                    bars_data = data.get("bars", [])
                    
                    # Filter bars within the time range
                    for bar_dict in bars_data:
                        bar = Bar.from_dict(bar_dict)
                        if time_range.contains(bar.timestamp):
                            all_bars.append(bar)
                
                current_date += timedelta(days=1)
            
            if all_bars:
                # Sort by timestamp
                all_bars.sort(key=lambda b: b.timestamp)
                logger.info(f"Retrieved {len(all_bars)} bars from Firestore for {cache_key.to_string()}")
                return all_bars
            
            logger.debug(f"No data found in Firestore for {cache_key.to_string()}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve data from Firestore: {e}")
            return None
    
    async def delete_old_data(self, days: int = 90) -> int:
        """
        Delete data older than specified days (for migration to cold tier).
        
        Args:
            days: Delete data older than this many days
            
        Returns:
            Number of documents deleted
        """
        if not self.db:
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            # Query documents older than cutoff
            query = self.collection.where("cached_at", "<", cutoff_timestamp)
            docs = query.stream()
            
            deleted_count = 0
            batch = self.db.batch()
            batch_size = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                batch_size += 1
                
                # Firestore batch limit is 500
                if batch_size >= 500:
                    batch.commit()
                    deleted_count += batch_size
                    batch = self.db.batch()
                    batch_size = 0
            
            # Commit remaining
            if batch_size > 0:
                batch.commit()
                deleted_count += batch_size
            
            logger.info(f"Deleted {deleted_count} old documents from Firestore")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete old data from Firestore: {e}")
            return 0
    
    async def get_cached_ranges(self, cache_key: CacheKey) -> List[TimeRange]:
        """
        Get all time ranges that are cached for a given key.
        
        Args:
            cache_key: Cache key to check
            
        Returns:
            List of time ranges that have cached data
        """
        if not self.db:
            return []
        
        try:
            # Query all documents for this cache key
            query = self.collection.where("cache_key", "==", cache_key.to_string())
            docs = query.stream()
            
            ranges = []
            for doc in docs:
                data = doc.to_dict()
                bars_data = data.get("bars", [])
                
                if bars_data:
                    timestamps = [bar["timestamp"] for bar in bars_data]
                    ranges.append(TimeRange(
                        start_timestamp=min(timestamps),
                        end_timestamp=max(timestamps)
                    ))
            
            return ranges
            
        except Exception as e:
            logger.error(f"Failed to get cached ranges from Firestore: {e}")
            return []

# Global Firestore storage instance
firestore_storage = FirestoreStorage()
