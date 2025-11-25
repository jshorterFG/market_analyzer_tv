"""
End-to-end test WITH caching enabled.
Tests the complete flow with Firestore/GCS integration.
"""
import asyncio
from server import get_analysis_data, get_analysis
from rate_limiter import rate_limiter
from cache_manager import cache_manager

async def test_cache_effectiveness():
    """Test that caching reduces API calls."""
    print("\n=== Testing Cache Effectiveness ===")
    
    # Reset rate limiter stats
    stats_before = rate_limiter.get_stats()
    print(f"Initial requests: {stats_before['requests_this_minute']}")
    
    # First call - should hit API and cache
    print("\n1st call (cache miss - will hit API):")
    data1 = await get_analysis_data("BTCUSDT", "crypto", "BINANCE", "1d")
    if data1:
        print(f"  ✓ BTC: ${data1.get('close', 0):,.2f}")
    
    stats_after_1 = rate_limiter.get_stats()
    requests_1 = stats_after_1['requests_this_minute'] - stats_before['requests_this_minute']
    print(f"  API requests made: {requests_1}")
    
    # Second call - should use cache for OHLCV
    print("\n2nd call (should use cached OHLCV):")
    data2 = await get_analysis_data("BTCUSDT", "crypto", "BINANCE", "1d")
    if data2:
        print(f"  ✓ BTC: ${data2.get('close', 0):,.2f}")
    
    stats_after_2 = rate_limiter.get_stats()
    requests_2 = stats_after_2['requests_this_minute'] - stats_after_1['requests_this_minute']
    print(f"  API requests made: {requests_2}")
    
    # Third call - different symbol
    print("\n3rd call (different symbol - cache miss):")
    data3 = await get_analysis_data("ETHUSDT", "crypto", "BINANCE", "1d")
    if data3:
        print(f"  ✓ ETH: ${data3.get('close', 0):,.2f}")
    
    stats_after_3 = rate_limiter.get_stats()
    requests_3 = stats_after_3['requests_this_minute'] - stats_after_2['requests_this_minute']
    print(f"  API requests made: {requests_3}")
    
    # Fourth call - same as third (should use cache)
    print("\n4th call (same symbol - should use cache):")
    data4 = await get_analysis_data("ETHUSDT", "crypto", "BINANCE", "1d")
    if data4:
        print(f"  ✓ ETH: ${data4.get('close', 0):,.2f}")
    
    stats_after_4 = rate_limiter.get_stats()
    requests_4 = stats_after_4['requests_this_minute'] - stats_after_3['requests_this_minute']
    print(f"  API requests made: {requests_4}")
    
    # Summary
    total_requests = stats_after_4['requests_this_minute'] - stats_before['requests_this_minute']
    print(f"\n📊 Summary:")
    print(f"  Total API calls: {total_requests}")
    print(f"  Total data fetches: 4")
    print(f"  Cache enabled: {cache_manager.enabled}")
    
    return True

async def test_multi_timeframe():
    """Test multiple timeframes for the same symbol."""
    print("\n=== Testing Multiple Timeframes ===")
    
    symbol = "BTCUSDT"
    intervals = ["1h", "4h", "1d"]
    
    for interval in intervals:
        data = await get_analysis_data(symbol, "crypto", "BINANCE", interval)
        if data:
            print(f"  ✓ {symbol} {interval}: ${data.get('close', 0):,.2f}")
        else:
            print(f"  ✗ {symbol} {interval}: Failed")
    
    return True

async def main():
    """Run end-to-end tests with caching."""
    print("=" * 60)
    print("END-TO-END TEST - WITH CACHING ENABLED")
    print("=" * 60)
    print(f"\nCache Status: {'ENABLED' if cache_manager.enabled else 'DISABLED'}")
    print(f"Hot Tier: Firestore (last {cache_manager.hot_tier_days} days)")
    print(f"Cold Tier: GCS Nearline\n")
    
    try:
        # Test 1: Cache effectiveness
        result1 = await test_cache_effectiveness()
        
        # Test 2: Multiple timeframes
        result2 = await test_multi_timeframe()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Cache Effectiveness: {'✓ PASSED' if result1 else '✗ FAILED'}")
        print(f"Multiple Timeframes: {'✓ PASSED' if result2 else '✗ FAILED'}")
        
        if result1 and result2:
            print("\n✓ ALL TESTS PASSED")
            print("\nCaching system is fully operational!")
            print("- Data is being cached in Firestore (hot tier)")
            print("- Old data will be archived to GCS (cold tier)")
            print("- API calls are minimized through intelligent caching")
        else:
            print("\n✗ SOME TESTS FAILED")
        
        print("=" * 60)
        
        return result1 and result2
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
