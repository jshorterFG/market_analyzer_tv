"""
Configuration management for the Market Analyzer application.
Handles GCP settings, cache configuration, and rate limiting parameters.
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class GCPConfig:
    """Google Cloud Platform configuration."""
    project_id: str = "sp500trading"
    location: str = "us-central1"
    firestore_database: str = "(default)"
    gcs_bucket_name: str = "market-analyzer-cache"
    
@dataclass
class CacheConfig:
    """Cache configuration for tiered storage."""
    # Hot tier: last 3 months of data in Firestore
    hot_tier_days: int = 90
    
    # Cold tier: data older than 3 months in GCS Nearline
    cold_tier_days: int = 90
    
    # Cache TTL for different timeframes (in seconds)
    ttl_1m: int = 60  # 1 minute bars cached for 1 minute
    ttl_5m: int = 300  # 5 minute bars cached for 5 minutes
    ttl_15m: int = 900  # 15 minute bars cached for 15 minutes
    ttl_30m: int = 1800  # 30 minute bars cached for 30 minutes
    ttl_1h: int = 3600  # 1 hour bars cached for 1 hour
    ttl_1d: int = 86400  # Daily bars cached for 24 hours
    
    # Maximum bars to request per API call
    max_bars_per_request: int = 5000
    
@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    # TradingView API rate limits (conservative estimates)
    max_requests_per_minute: int = 50
    max_requests_per_hour: int = 2000
    
    # Exponential backoff settings
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    
    # Request queue settings
    queue_max_size: int = 1000
    request_timeout_seconds: int = 30

@dataclass
class AppConfig:
    """Main application configuration."""
    gcp: GCPConfig
    cache: CacheConfig
    rate_limit: RateLimitConfig
    
    # Enable/disable caching (useful for testing)
    enable_cache: bool = True
    
    # Enable/disable rate limiting
    enable_rate_limiting: bool = True
    
    # Logging level
    log_level: str = "INFO"

# Default configuration instance
def get_config() -> AppConfig:
    """Get application configuration with environment variable overrides."""
    return AppConfig(
        gcp=GCPConfig(
            project_id=os.getenv("GCP_PROJECT_ID", "sp500trading"),
            location=os.getenv("GCP_LOCATION", "us-central1"),
            firestore_database=os.getenv("FIRESTORE_DATABASE", "(default)"),
            gcs_bucket_name=os.getenv("GCS_BUCKET_NAME", "market-analyzer-cache"),
        ),
        cache=CacheConfig(
            hot_tier_days=int(os.getenv("HOT_TIER_DAYS", "90")),
            cold_tier_days=int(os.getenv("COLD_TIER_DAYS", "90")),
        ),
        rate_limit=RateLimitConfig(
            max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "50")),
            max_requests_per_hour=int(os.getenv("MAX_REQUESTS_PER_HOUR", "2000")),
        ),
        enable_cache=os.getenv("ENABLE_CACHE", "true").lower() == "true",
        enable_rate_limiting=os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

# Global config instance
config = get_config()
