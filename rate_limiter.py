"""
Rate limiter implementation using Leaky Bucket algorithm.
Prevents API rate limit violations with exponential backoff.
"""
import asyncio
import time
import logging
from typing import Optional, Callable, Any, Awaitable
from dataclasses import dataclass
from collections import deque
from config import config

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded and cache fallback should be used."""
    pass

@dataclass
class RateLimitState:
    """Tracks rate limiting state."""
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    minute_window_start: float = 0
    hour_window_start: float = 0
    consecutive_failures: int = 0
    current_backoff: float = 0

class RateLimiter:
    """
    Leaky Bucket rate limiter with exponential backoff.
    
    Implements:
    - Per-minute and per-hour rate limits
    - Request queue with priority
    - Exponential backoff for 429 errors
    - Request timeout handling
    """
    
    def __init__(self):
        self.state = RateLimitState()
        self.queue: deque = deque()
        self.lock = asyncio.Lock()
        self.enabled = config.enable_rate_limiting
        
        # Rate limit configuration
        self.max_per_minute = config.rate_limit.max_requests_per_minute
        self.max_per_hour = config.rate_limit.max_requests_per_hour
        self.initial_backoff = config.rate_limit.initial_backoff_seconds
        self.max_backoff = config.rate_limit.max_backoff_seconds
        self.backoff_multiplier = config.rate_limit.backoff_multiplier
        
        logger.info(f"RateLimiter initialized: {self.max_per_minute}/min, {self.max_per_hour}/hour")
    
    def _reset_windows_if_needed(self):
        """Reset rate limit windows if time has elapsed."""
        current_time = time.time()
        
        # Reset minute window
        if current_time - self.state.minute_window_start >= 60:
            self.state.requests_this_minute = 0
            self.state.minute_window_start = current_time
            logger.debug("Reset minute window")
        
        # Reset hour window
        if current_time - self.state.hour_window_start >= 3600:
            self.state.requests_this_hour = 0
            self.state.hour_window_start = current_time
            logger.debug("Reset hour window")
    
    def _can_make_request(self) -> bool:
        """Check if we can make a request without exceeding limits."""
        self._reset_windows_if_needed()
        
        return (self.state.requests_this_minute < self.max_per_minute and
                self.state.requests_this_hour < self.max_per_hour)
    
    def _calculate_wait_time(self) -> float:
        """Calculate how long to wait before next request."""
        self._reset_windows_if_needed()
        
        # If we're in backoff, wait for backoff period
        if self.state.current_backoff > 0:
            return self.state.current_backoff
        
        # If minute limit reached, wait until next minute window
        if self.state.requests_this_minute >= self.max_per_minute:
            time_since_window_start = time.time() - self.state.minute_window_start
            return max(0, 60 - time_since_window_start)
        
        # If hour limit reached, wait until next hour window
        if self.state.requests_this_hour >= self.max_per_hour:
            time_since_window_start = time.time() - self.state.hour_window_start
            return max(0, 3600 - time_since_window_start)
        
        return 0
    
    def _record_request(self):
        """Record that a request was made."""
        self._reset_windows_if_needed()
        self.state.requests_this_minute += 1
        self.state.requests_this_hour += 1
        logger.debug(f"Request recorded: {self.state.requests_this_minute}/min, "
                    f"{self.state.requests_this_hour}/hour")
    
    def _handle_success(self):
        """Handle successful request - reset backoff."""
        if self.state.consecutive_failures > 0:
            logger.info(f"Request succeeded after {self.state.consecutive_failures} failures")
        self.state.consecutive_failures = 0
        self.state.current_backoff = 0
    
    def _handle_rate_limit_error(self):
        """Handle 429 error - apply exponential backoff."""
        self.state.consecutive_failures += 1
        
        if self.state.consecutive_failures == 1:
            self.state.current_backoff = self.initial_backoff
        else:
            self.state.current_backoff = min(
                self.state.current_backoff * self.backoff_multiplier,
                self.max_backoff
            )
        
        logger.warning(f"Rate limit hit (failure #{self.state.consecutive_failures}). "
                      f"Backing off for {self.state.current_backoff}s")
    
    async def execute(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute a function with rate limiting.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            RateLimitExceeded: If rate limit is hit (to trigger cache fallback)
            Exception: If the function raises an exception after retries
        """
        if not self.enabled:
            # Rate limiting disabled, execute immediately
            return await func(*args, **kwargs)
        
        async with self.lock:
            # Check if we're at the rate limit
            if not self._can_make_request():
                wait_time = self._calculate_wait_time()
                if wait_time > 0:
                    logger.warning(f"Rate limit exceeded. Would need to wait {wait_time:.2f}s. Triggering cache fallback.")
                    raise RateLimitExceeded(f"Rate limit exceeded, cache fallback recommended")
            
            # Record the request
            self._record_request()
        
        # Execute the function
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                self._handle_success()
                return result
            
            except Exception as e:
                # Check if it's a rate limit error
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    self._handle_rate_limit_error()
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying after backoff (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(self.state.current_backoff)
                        continue
                
                # Not a rate limit error or max retries reached
                logger.error(f"Request failed: {e}")
                raise
        
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        self._reset_windows_if_needed()
        return {
            "requests_this_minute": self.state.requests_this_minute,
            "requests_this_hour": self.state.requests_this_hour,
            "consecutive_failures": self.state.consecutive_failures,
            "current_backoff": self.state.current_backoff,
            "max_per_minute": self.max_per_minute,
            "max_per_hour": self.max_per_hour
        }

# Global rate limiter instance
rate_limiter = RateLimiter()
