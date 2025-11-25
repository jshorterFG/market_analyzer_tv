"""
Data fetcher with caching and rate limiting integration.
Wraps TradingView API calls with intelligent caching.
"""
import logging
from datetime import datetime
from typing import List, Optional
from tradingview_ta import TA_Handler, Interval as TVInterval

from models import Bar, CacheKey, TimeRange, Interval
from cache_manager import cache_manager
from rate_limiter import rate_limiter, RateLimitExceeded
from config import config

logger = logging.getLogger(__name__)

# Map our Interval enum to TradingView intervals
TV_INTERVAL_MAP = {
    Interval.ONE_MINUTE: TVInterval.INTERVAL_1_MINUTE,
    Interval.FIVE_MINUTES: TVInterval.INTERVAL_5_MINUTES,
    Interval.FIFTEEN_MINUTES: TVInterval.INTERVAL_15_MINUTES,
    Interval.THIRTY_MINUTES: TVInterval.INTERVAL_30_MINUTES,
    Interval.ONE_HOUR: TVInterval.INTERVAL_1_HOUR,
    Interval.FOUR_HOURS: TVInterval.INTERVAL_4_HOURS,
    Interval.ONE_DAY: TVInterval.INTERVAL_1_DAY,
    Interval.ONE_WEEK: TVInterval.INTERVAL_1_WEEK,
    Interval.ONE_MONTH: TVInterval.INTERVAL_1_MONTH,
}

# Reverse map for string to Interval
STRING_INTERVAL_MAP = {
    "1m": Interval.ONE_MINUTE,
    "5m": Interval.FIVE_MINUTES,
    "15m": Interval.FIFTEEN_MINUTES,
    "30m": Interval.THIRTY_MINUTES,
    "1h": Interval.ONE_HOUR,
    "4h": Interval.FOUR_HOURS,
    "1d": Interval.ONE_DAY,
    "1W": Interval.ONE_WEEK,
    "1M": Interval.ONE_MONTH,
}

class DataFetcher:
    """
    Fetches market data with caching and rate limiting.
    
    This is a wrapper around TradingView API that:
    1. Checks cache before making API calls
    2. Uses rate limiter for all external requests
    3. Stores retrieved data in cache
    4. Handles cache misses gracefully
    """
    
    def __init__(self):
        self.cache = cache_manager
        self.rate_limiter = rate_limiter
        logger.info("DataFetcher initialized")
    
    async def get_current_bar(
        self,
        symbol: str,
        screener: str,
        exchange: str,
        interval: str
    ) -> Optional[Bar]:
        """
        Get the current bar for a symbol.
        This is cached with a short TTL based on the interval.
        
        Args:
            symbol: Trading symbol
            screener: Market screener (crypto, america, forex, etc.)
            exchange: Exchange name
            interval: Timeframe interval
            
        Returns:
            Current bar or None if error
        """
        try:
            # Convert interval string to our Interval enum
            interval_enum = STRING_INTERVAL_MAP.get(interval, Interval.ONE_DAY)
            
            # Create cache key
            cache_key = CacheKey(
                symbol=symbol,
                screener=screener,
                exchange=exchange,
                interval=interval_enum
            )
            
            # Check cache first
            now = int(datetime.now().timestamp())
            time_range = TimeRange(
                start_timestamp=now - 3600,  # Look back 1 hour
                end_timestamp=now
            )
            
            cached_bars = await self.cache.get(cache_key, time_range)
            
            if cached_bars:
                # Return most recent bar
                logger.info(f"Cache hit for {symbol} {interval}")
                return cached_bars[-1]
            
            # Cache miss - fetch from API with rate limiting
            logger.info(f"Cache miss for {symbol} {interval}, fetching from API")
            bar = await self._fetch_from_api(symbol, screener, exchange, interval_enum)
            
            if bar:
                # Store in cache
                await self.cache.put(cache_key, [bar])
            
            return bar
            
        except Exception as e:
            logger.error(f"Error getting current bar: {e}")
            return None
    
    async def _fetch_from_api(
        self,
        symbol: str,
        screener: str,
        exchange: str,
        interval: Interval
    ) -> Optional[Bar]:
        """
        Fetch current bar from TradingView API with rate limiting.
        
        Args:
            symbol: Trading symbol
            screener: Market screener
            exchange: Exchange name
            interval: Timeframe interval
            
        Returns:
            Current bar or None if error
        """
        async def fetch():
            """Inner function to be rate limited."""
            tv_interval = TV_INTERVAL_MAP.get(interval, TVInterval.INTERVAL_1_DAY)
            
            handler = TA_Handler(
                symbol=symbol,
                screener=screener,
                exchange=exchange,
                interval=tv_interval
            )
            
            analysis = handler.get_analysis()
            
            # Extract OHLCV data
            timestamp = int(datetime.now().timestamp())
            
            return Bar(
                timestamp=timestamp,
                open=analysis.indicators.get('open', 0),
                high=analysis.indicators.get('high', 0),
                low=analysis.indicators.get('low', 0),
                close=analysis.indicators.get('close', 0),
                volume=analysis.indicators.get('volume', 0)
            )
        
        try:
            # Execute with rate limiting
            bar = await self.rate_limiter.execute(fetch)
            logger.info(f"Fetched bar from API: {symbol} {interval.value}")
            return bar
            
        except Exception as e:
            logger.error(f"Error fetching from API: {e}")
            return None
    
    async def get_analysis_with_cache(
        self,
        symbol: str,
        screener: str,
        exchange: str,
        interval: str
    ) -> dict:
        """
        Get analysis data with caching.
        This is a drop-in replacement for the original get_analysis_data function.
        
        Args:
            symbol: Trading symbol
            screener: Market screener
            exchange: Exchange name
            interval: Timeframe interval string
            
        Returns:
            Dictionary with analysis data (includes 'from_cache' and 'cache_warning' keys if using cached data)
        """
        try:
            # Convert interval string to our Interval enum
            interval_enum = STRING_INTERVAL_MAP.get(interval, Interval.ONE_DAY)
            tv_interval = TV_INTERVAL_MAP.get(interval_enum, TVInterval.INTERVAL_1_DAY)
            
            # Try to get fresh data from API
            try:
                # Get current bar (with caching)
                bar = await self.get_current_bar(symbol, screener, exchange, interval)
                
                if not bar:
                    # Try to get from cache only
                    return await self._get_cached_analysis_only(symbol, screener, exchange, interval)
                
                # Fetch full analysis from API (this includes indicators)
                async def fetch_analysis():
                    handler = TA_Handler(
                        symbol=symbol,
                        screener=screener,
                        exchange=exchange,
                        interval=tv_interval
                    )
                    return handler.get_analysis()
                
                # Execute with rate limiting
                analysis = await self.rate_limiter.execute(fetch_analysis)
                
                # Return fresh analysis data
                result = {
                    'open': bar.open,
                    'close': bar.close,
                    'high': bar.high,
                    'low': bar.low,
                    'volume': bar.volume,
                    'psar': analysis.indicators.get('P.SAR'),
                    'rsi': analysis.indicators.get('RSI'),
                    'macd': analysis.indicators.get('MACD.macd'),
                    'ema20': analysis.indicators.get('EMA20'),
                    'sma50': analysis.indicators.get('SMA50'),
                    'sma200': analysis.indicators.get('SMA200'),
                    'adx': analysis.indicators.get('ADX'),
                    'fi': analysis.indicators.get('FI'),
                    'recommendation': analysis.summary.get('RECOMMENDATION'),
                    'from_cache': False,
                }
                
                # Calculate Force Index if missing
                if result['fi'] is None:
                    close = result['close']
                    change = analysis.indicators.get('change')
                    
                    if close and change is not None and bar.volume:
                        price_change = close * change / 100
                        result['fi'] = price_change * bar.volume
                
                return result
                
            except RateLimitExceeded as e:
                # Rate limit hit - fall back to cached data
                logger.warning(f"Rate limit exceeded for {symbol}, falling back to cache")
                return await self._get_cached_analysis_only(symbol, screener, exchange, interval)
            
        except Exception as e:
            logger.error(f"Error in get_analysis_with_cache: {e}")
            return {}
    
    async def _get_cached_analysis_only(
        self,
        symbol: str,
        screener: str,
        exchange: str,
        interval: str
    ) -> dict:
        """
        Get analysis data from cache only (no API calls).
        Used as fallback when rate-limited.
        
        Returns:
            Dictionary with cached data and warning flags
        """
        try:
            interval_enum = STRING_INTERVAL_MAP.get(interval, Interval.ONE_DAY)
            
            # Create cache key
            cache_key = CacheKey(
                symbol=symbol,
                screener=screener,
                exchange=exchange,
                interval=interval_enum
            )
            
            # Try to get cached data
            now = int(datetime.now().timestamp())
            time_range = TimeRange(
                start_timestamp=now - 86400,  # Look back 24 hours
                end_timestamp=now
            )
            
            cached_bars = await self.cache.get(cache_key, time_range)
            
            if cached_bars and len(cached_bars) > 0:
                # Use most recent cached bar
                bar = cached_bars[-1]
                cache_age = now - bar.timestamp
                
                logger.info(f"Returning cached data for {symbol} (age: {cache_age}s)")
                
                return {
                    'open': bar.open,
                    'close': bar.close,
                    'high': bar.high,
                    'low': bar.low,
                    'volume': bar.volume,
                    'from_cache': True,
                    'cache_age_seconds': cache_age,
                    'cache_warning': f"⚠️ Rate limit exceeded. Showing cached data from {cache_age // 60} minutes ago.",
                }
            
            # No cached data available
            logger.warning(f"No cached data available for {symbol}")
            return {
                'error': 'Rate limit exceeded and no cached data available',
                'from_cache': True,
            }
            
        except Exception as e:
            logger.error(f"Error getting cached analysis: {e}")
            return {
                'error': f'Failed to retrieve cached data: {str(e)}',
                'from_cache': True,
            }

# Global data fetcher instance
data_fetcher = DataFetcher()
