"""
Test cache functionality including gap detection and data integrity.
"""
import asyncio
import time
from datetime import datetime, timedelta
from models import Bar, CacheKey, TimeRange, Interval
from cache_manager import cache_manager

async def test_cache_basic():
    """Test basic cache operations."""
    print("\n=== Testing Basic Cache Operations ===")
    
    # Create test data
    cache_key = CacheKey(
        symbol="BTCUSDT",
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.ONE_MINUTE
    )
    
    # Generate test bars
    now = int(datetime.now().timestamp())
    bars = []
    for i in range(10):
        timestamp = now - (i * 60)  # 1 minute intervals
        bars.append(Bar(
            timestamp=timestamp,
            open=50000.0 + i,
            high=50100.0 + i,
            low=49900.0 + i,
            close=50050.0 + i,
            volume=1000.0
        ))
    
    bars.reverse()  # Sort oldest to newest
    
    # Test cache put
    print(f"Storing {len(bars)} bars...")
    success = await cache_manager.put(cache_key, bars)
    print(f"Store result: {success}")
    
    # Test cache get
    time_range = TimeRange(
        start_timestamp=bars[0].timestamp,
        end_timestamp=bars[-1].timestamp
    )
    
    print(f"Retrieving bars from cache...")
    cached_bars = await cache_manager.get(cache_key, time_range)
    
    if cached_bars:
        print(f"Retrieved {len(cached_bars)} bars from cache")
        print(f"First bar: timestamp={cached_bars[0].timestamp}, close={cached_bars[0].close}")
        print(f"Last bar: timestamp={cached_bars[-1].timestamp}, close={cached_bars[-1].close}")
    else:
        print("No bars retrieved from cache")
    
    return success and cached_bars is not None

async def test_gap_detection():
    """Test gap detection in cached data."""
    print("\n=== Testing Gap Detection ===")
    
    cache_key = CacheKey(
        symbol="ETHUSDT",
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.FIVE_MINUTES
    )
    
    # Create bars with a gap in the middle
    now = int(datetime.now().timestamp())
    bars = []
    
    # First segment: 5 bars
    for i in range(5):
        timestamp = now - (i * 300)  # 5 minute intervals
        bars.append(Bar(
            timestamp=timestamp,
            open=3000.0,
            high=3100.0,
            low=2900.0,
            close=3050.0,
            volume=500.0
        ))
    
    # Gap of 1 hour
    
    # Second segment: 5 bars
    for i in range(5):
        timestamp = now - (3600 + i * 300)  # 1 hour gap + 5 minute intervals
        bars.append(Bar(
            timestamp=timestamp,
            open=3000.0,
            high=3100.0,
            low=2900.0,
            close=3050.0,
            volume=500.0
        ))
    
    bars.reverse()
    
    # Store bars
    print(f"Storing {len(bars)} bars with gap...")
    await cache_manager.put(cache_key, bars)
    
    # Request range that spans the gap
    time_range = TimeRange(
        start_timestamp=bars[0].timestamp - 600,  # Request before first bar
        end_timestamp=bars[-1].timestamp + 600  # Request after last bar
    )
    
    print(f"Finding gaps in requested range...")
    gaps = await cache_manager.find_gaps(cache_key, time_range)
    
    print(f"Found {len(gaps)} gaps:")
    for gap in gaps:
        print(f"  {gap}")
    
    return len(gaps) > 0

async def test_tier_partitioning():
    """Test automatic partitioning between hot and cold tiers."""
    print("\n=== Testing Tier Partitioning ===")
    
    cache_key = CacheKey(
        symbol="AAPL",
        screener="america",
        exchange="NASDAQ",
        interval=Interval.ONE_DAY
    )
    
    # Create bars spanning hot and cold tiers
    now = datetime.now()
    bars = []
    
    # Recent bars (hot tier) - last 30 days
    for i in range(30):
        dt = now - timedelta(days=i)
        bars.append(Bar(
            timestamp=int(dt.timestamp()),
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1000000.0
        ))
    
    # Old bars (cold tier) - 100-130 days ago
    for i in range(100, 130):
        dt = now - timedelta(days=i)
        bars.append(Bar(
            timestamp=int(dt.timestamp()),
            open=140.0,
            high=145.0,
            low=138.0,
            close=142.0,
            volume=900000.0
        ))
    
    bars.reverse()
    
    print(f"Storing {len(bars)} bars spanning hot and cold tiers...")
    success = await cache_manager.put(cache_key, bars)
    print(f"Store result: {success}")
    
    # Retrieve all bars
    time_range = TimeRange(
        start_timestamp=bars[0].timestamp,
        end_timestamp=bars[-1].timestamp
    )
    
    print(f"Retrieving bars from both tiers...")
    cached_bars = await cache_manager.get(cache_key, time_range)
    
    if cached_bars:
        print(f"Retrieved {len(cached_bars)} bars from cache")
        print(f"Expected {len(bars)} bars")
    else:
        print("No bars retrieved")
    
    return success

async def main():
    """Run all cache tests."""
    print("Starting cache tests...")
    print("Note: These tests require GCP credentials and Firestore/GCS setup")
    
    try:
        # Test 1: Basic operations
        result1 = await test_cache_basic()
        print(f"\n✓ Basic cache test: {'PASSED' if result1 else 'FAILED'}")
        
        # Test 2: Gap detection
        result2 = await test_gap_detection()
        print(f"✓ Gap detection test: {'PASSED' if result2 else 'FAILED'}")
        
        # Test 3: Tier partitioning
        result3 = await test_tier_partitioning()
        print(f"✓ Tier partitioning test: {'PASSED' if result3 else 'FAILED'}")
        
        print("\n=== All Tests Complete ===")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
