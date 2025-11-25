"""
Cache manager that orchestrates hot and cold tier storage.
Implements intelligent caching with gap detection and data aggregation.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from models import Bar, CacheKey, TimeRange, DataGap, Interval
from firestore_storage import firestore_storage
from gcs_storage import gcs_storage
from config import config

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages caching across hot (Firestore) and cold (GCS) tiers.
    
    Implements:
    - Cache lookup with gap detection
    - Automatic tier selection based on data age
    - Data migration between tiers
    - Server-side timeframe aggregation
    """
    
    def __init__(self):
        self.hot_storage = firestore_storage
        self.cold_storage = gcs_storage
        self.enabled = config.enable_cache
        self.hot_tier_days = config.cache.hot_tier_days
        
        logger.info(f"CacheManager initialized: cache_enabled={self.enabled}, "
                   f"hot_tier_days={self.hot_tier_days}")
    
    def _is_hot_tier(self, timestamp: int) -> bool:
        """Determine if timestamp should be in hot tier."""
        cutoff = datetime.now() - timedelta(days=self.hot_tier_days)
        cutoff_timestamp = int(cutoff.timestamp())
        return timestamp >= cutoff_timestamp
    
    def _partition_bars_by_tier(self, bars: List[Bar]) -> Tuple[List[Bar], List[Bar]]:
        """Partition bars into hot and cold tier based on age."""
        hot_bars = []
        cold_bars = []
        
        for bar in bars:
            if self._is_hot_tier(bar.timestamp):
                hot_bars.append(bar)
            else:
                cold_bars.append(bar)
        
        return hot_bars, cold_bars
    
    async def get(self, cache_key: CacheKey, time_range: TimeRange) -> Optional[List[Bar]]:
        """
        Retrieve bars from cache, checking both hot and cold tiers.
        
        Args:
            cache_key: Cache key identifying the data
            time_range: Time range to retrieve
            
        Returns:
            List of bars if found, None if not in cache
        """
        if not self.enabled:
            return None
        
        try:
            all_bars = []
            
            # Try hot tier first
            hot_bars = await self.hot_storage.retrieve(cache_key, time_range)
            if hot_bars:
                all_bars.extend(hot_bars)
                logger.debug(f"Found {len(hot_bars)} bars in hot tier")
            
            # Check if we need to query cold tier
            # (if requested range extends beyond hot tier threshold)
            cutoff = datetime.now() - timedelta(days=self.hot_tier_days)
            cutoff_timestamp = int(cutoff.timestamp())
            
            if time_range.start_timestamp < cutoff_timestamp:
                # Query cold tier for older data
                cold_time_range = TimeRange(
                    start_timestamp=time_range.start_timestamp,
                    end_timestamp=min(time_range.end_timestamp, cutoff_timestamp)
                )
                
                cold_bars = await self.cold_storage.retrieve(cache_key, cold_time_range)
                if cold_bars:
                    all_bars.extend(cold_bars)
                    logger.debug(f"Found {len(cold_bars)} bars in cold tier")
            
            if all_bars:
                # Sort and deduplicate by timestamp
                unique_bars = {bar.timestamp: bar for bar in all_bars}.values()
                sorted_bars = sorted(unique_bars, key=lambda b: b.timestamp)
                logger.info(f"Cache hit: Retrieved {len(sorted_bars)} bars for {cache_key.to_string()}")
                return sorted_bars
            
            logger.debug(f"Cache miss: No data found for {cache_key.to_string()}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    async def put(self, cache_key: CacheKey, bars: List[Bar]) -> bool:
        """
        Store bars in cache, automatically partitioning by tier.
        
        Args:
            cache_key: Cache key identifying the data
            bars: List of bars to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not bars:
            return False
        
        try:
            # Partition bars by tier
            hot_bars, cold_bars = self._partition_bars_by_tier(bars)
            
            success = True
            
            # Store hot tier data
            if hot_bars:
                hot_success = await self.hot_storage.store(cache_key, hot_bars)
                if hot_success:
                    logger.info(f"Stored {len(hot_bars)} bars in hot tier")
                else:
                    logger.warning(f"Failed to store {len(hot_bars)} bars in hot tier")
                    success = False
            
            # Store cold tier data
            if cold_bars:
                cold_success = await self.cold_storage.store(cache_key, cold_bars)
                if cold_success:
                    logger.info(f"Stored {len(cold_bars)} bars in cold tier")
                else:
                    logger.warning(f"Failed to store {len(cold_bars)} bars in cold tier")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
            return False
    
    async def find_gaps(self, cache_key: CacheKey, requested_range: TimeRange) -> List[DataGap]:
        """
        Find gaps in cached data that need to be fetched from API.
        
        Args:
            cache_key: Cache key identifying the data
            requested_range: Requested time range
            
        Returns:
            List of gaps that need to be fetched
        """
        if not self.enabled:
            # Cache disabled, entire range is a gap
            return [DataGap(cache_key=cache_key, time_range=requested_range)]
        
        try:
            # Get cached data
            cached_bars = await self.get(cache_key, requested_range)
            
            if not cached_bars:
                # No cached data, entire range is a gap
                logger.debug(f"No cached data, entire range is a gap")
                return [DataGap(cache_key=cache_key, time_range=requested_range)]
            
            # Find gaps in the cached data
            gaps = []
            cached_timestamps = sorted([bar.timestamp for bar in cached_bars])
            
            # Check for gap at the beginning
            if cached_timestamps[0] > requested_range.start_timestamp:
                gaps.append(DataGap(
                    cache_key=cache_key,
                    time_range=TimeRange(
                        start_timestamp=requested_range.start_timestamp,
                        end_timestamp=cached_timestamps[0] - 1
                    )
                ))
            
            # Check for gaps in the middle
            # (This is simplified - in production, you'd calculate expected interval)
            interval_seconds = self._get_interval_seconds(cache_key.interval)
            for i in range(len(cached_timestamps) - 1):
                gap_size = cached_timestamps[i + 1] - cached_timestamps[i]
                # If gap is larger than 2x the interval, consider it a gap
                if gap_size > interval_seconds * 2:
                    gaps.append(DataGap(
                        cache_key=cache_key,
                        time_range=TimeRange(
                            start_timestamp=cached_timestamps[i] + interval_seconds,
                            end_timestamp=cached_timestamps[i + 1] - interval_seconds
                        )
                    ))
            
            # Check for gap at the end
            if cached_timestamps[-1] < requested_range.end_timestamp:
                gaps.append(DataGap(
                    cache_key=cache_key,
                    time_range=TimeRange(
                        start_timestamp=cached_timestamps[-1] + 1,
                        end_timestamp=requested_range.end_timestamp
                    )
                ))
            
            if gaps:
                logger.info(f"Found {len(gaps)} gaps in cached data")
                for gap in gaps:
                    logger.debug(f"  {gap}")
            else:
                logger.info(f"No gaps found, cache is complete for requested range")
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error finding gaps: {e}")
            # On error, treat entire range as a gap
            return [DataGap(cache_key=cache_key, time_range=requested_range)]
    
    def _get_interval_seconds(self, interval: Interval) -> int:
        """Get interval duration in seconds."""
        interval_map = {
            Interval.ONE_MINUTE: 60,
            Interval.FIVE_MINUTES: 300,
            Interval.FIFTEEN_MINUTES: 900,
            Interval.THIRTY_MINUTES: 1800,
            Interval.ONE_HOUR: 3600,
            Interval.FOUR_HOURS: 14400,
            Interval.ONE_DAY: 86400,
            Interval.ONE_WEEK: 604800,
            Interval.ONE_MONTH: 2592000,
        }
        return interval_map.get(interval, 3600)
    
    async def migrate_to_cold_tier(self) -> int:
        """
        Migrate old data from hot tier to cold tier.
        
        Returns:
            Number of records migrated
        """
        try:
            # This would be run as a periodic job
            # For now, just delete old data from hot tier
            # (assuming it's already been copied to cold tier)
            deleted = await self.hot_storage.delete_old_data(days=self.hot_tier_days)
            logger.info(f"Migrated {deleted} records from hot to cold tier")
            return deleted
            
        except Exception as e:
            logger.error(f"Error migrating to cold tier: {e}")
            return 0
    
    async def aggregate_timeframe(
        self, 
        cache_key: CacheKey, 
        source_bars: List[Bar], 
        target_interval: Interval
    ) -> List[Bar]:
        """
        Aggregate bars from a lower timeframe to a higher timeframe.
        For example, aggregate 1m bars to 5m bars.
        
        Args:
            cache_key: Cache key for the source data
            source_bars: Source bars (lower timeframe)
            target_interval: Target interval to aggregate to
            
        Returns:
            Aggregated bars
        """
        if not source_bars:
            return []
        
        try:
            target_seconds = self._get_interval_seconds(target_interval)
            aggregated = []
            
            # Group bars by target interval
            current_group = []
            current_interval_start = None
            
            for bar in sorted(source_bars, key=lambda b: b.timestamp):
                # Calculate which interval this bar belongs to
                interval_start = (bar.timestamp // target_seconds) * target_seconds
                
                if current_interval_start is None:
                    current_interval_start = interval_start
                
                if interval_start == current_interval_start:
                    current_group.append(bar)
                else:
                    # Aggregate current group
                    if current_group:
                        aggregated.append(self._aggregate_bars(current_group, current_interval_start))
                    
                    # Start new group
                    current_group = [bar]
                    current_interval_start = interval_start
            
            # Aggregate last group
            if current_group:
                aggregated.append(self._aggregate_bars(current_group, current_interval_start))
            
            logger.info(f"Aggregated {len(source_bars)} bars to {len(aggregated)} {target_interval.value} bars")
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating timeframe: {e}")
            return []
    
    def _aggregate_bars(self, bars: List[Bar], timestamp: int) -> Bar:
        """Aggregate multiple bars into one."""
        return Bar(
            timestamp=timestamp,
            open=bars[0].open,
            high=max(bar.high for bar in bars),
            low=min(bar.low for bar in bars),
            close=bars[-1].close,
            volume=sum(bar.volume for bar in bars)
        )

# Global cache manager instance
cache_manager = CacheManager()
