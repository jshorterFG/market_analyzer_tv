"""
Data models for time-series market data storage.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class Interval(str, Enum):
    """Supported timeframe intervals."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"

@dataclass
class Bar:
    """Represents a single OHLCV bar."""
    timestamp: int  # Unix timestamp in seconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bar':
        """Create Bar from dictionary."""
        return cls(**data)

@dataclass
class CacheKey:
    """Unique identifier for cached data."""
    symbol: str
    screener: str
    exchange: str
    interval: Interval
    
    def to_string(self) -> str:
        """Convert to string key for storage."""
        return f"{self.screener}:{self.exchange}:{self.symbol}:{self.interval.value}"
    
    @classmethod
    def from_string(cls, key: str) -> 'CacheKey':
        """Parse cache key from string."""
        parts = key.split(":")
        if len(parts) != 4:
            raise ValueError(f"Invalid cache key format: {key}")
        return cls(
            screener=parts[0],
            exchange=parts[1],
            symbol=parts[2],
            interval=Interval(parts[3])
        )

@dataclass
class TimeRange:
    """Represents a time range for data queries."""
    start_timestamp: int  # Unix timestamp in seconds
    end_timestamp: int  # Unix timestamp in seconds
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """Check if this range overlaps with another."""
        return not (self.end_timestamp < other.start_timestamp or 
                   self.start_timestamp > other.end_timestamp)
    
    def contains(self, timestamp: int) -> bool:
        """Check if timestamp is within this range."""
        return self.start_timestamp <= timestamp <= self.end_timestamp
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp
        }

@dataclass
class CachedData:
    """Represents cached market data with metadata."""
    cache_key: CacheKey
    bars: List[Bar]
    time_range: TimeRange
    cached_at: int  # Unix timestamp when data was cached
    tier: str  # "hot" or "cold"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "cache_key": self.cache_key.to_string(),
            "bars": [bar.to_dict() for bar in self.bars],
            "time_range": self.time_range.to_dict(),
            "cached_at": self.cached_at,
            "tier": self.tier
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedData':
        """Create CachedData from dictionary."""
        return cls(
            cache_key=CacheKey.from_string(data["cache_key"]),
            bars=[Bar.from_dict(bar) for bar in data["bars"]],
            time_range=TimeRange(**data["time_range"]),
            cached_at=data["cached_at"],
            tier=data["tier"]
        )

@dataclass
class DataGap:
    """Represents a gap in cached data that needs to be fetched."""
    cache_key: CacheKey
    time_range: TimeRange
    
    def __str__(self) -> str:
        """String representation of the gap."""
        start_dt = datetime.fromtimestamp(self.time_range.start_timestamp)
        end_dt = datetime.fromtimestamp(self.time_range.end_timestamp)
        return f"Gap for {self.cache_key.to_string()}: {start_dt} to {end_dt}"
