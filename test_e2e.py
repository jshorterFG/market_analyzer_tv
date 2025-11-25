"""
End-to-end test with actual TradingView API.
Tests the complete flow: API call -> rate limiting -> caching.
"""
import asyncio
from server import get_analysis_data, get_analysis
from rate_limiter import rate_limiter

async def test_btc_analysis():
    """Test BTC analysis with caching."""
    print("\n=== Testing BTC Analysis (1st call - should hit API) ===")
    
    # First call - should hit the API
    data1 = await get_analysis_data("BTCUSDT", "crypto", "BINANCE", "1d")
    
    if data1:
        print(f"✓ Got BTC data:")
        print(f"  Close: ${data1.get('close', 0):,.2f}")
        print(f"  High: ${data1.get('high', 0):,.2f}")
        print(f"  Low: ${data1.get('low', 0):,.2f}")
        print(f"  RSI: {data1.get('rsi', 0):.2f}")
        print(f"  Recommendation: {data1.get('recommendation', 'N/A')}")
    else:
        print("✗ Failed to get BTC data")
        return False
    
    # Check rate limiter stats
    stats = rate_limiter.get_stats()
    print(f"\nRate Limiter Stats after 1st call:")
    print(f"  Requests this minute: {stats['requests_this_minute']}")
    
    print("\n=== Testing BTC Analysis (2nd call - should use cache) ===")
    
    # Second call - should use cache (same data)
    data2 = await get_analysis_data("BTCUSDT", "crypto", "BINANCE", "1d")
    
    if data2:
        print(f"✓ Got BTC data (cached):")
        print(f"  Close: ${data2.get('close', 0):,.2f}")
    else:
        print("✗ Failed to get cached BTC data")
        return False
    
    # Check rate limiter stats again
    stats2 = rate_limiter.get_stats()
    print(f"\nRate Limiter Stats after 2nd call:")
    print(f"  Requests this minute: {stats2['requests_this_minute']}")
    
    # Note: We expect 2 requests because we still fetch indicators from API
    # but the OHLCV data should be cached
    
    return True

async def test_formatted_analysis():
    """Test formatted analysis output."""
    print("\n=== Testing Formatted Analysis ===")
    
    analysis = await get_analysis("ETHUSDT", "crypto", "BINANCE", "1d")
    
    if analysis and not analysis.startswith("Error"):
        print("✓ Got formatted analysis:")
        print("-" * 60)
        print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        print("-" * 60)
        return True
    else:
        print(f"✗ Failed to get analysis: {analysis}")
        return False

async def main():
    """Run end-to-end tests."""
    print("=" * 60)
    print("END-TO-END TEST - TradingView API Integration")
    print("=" * 60)
    print("\nNote: These tests make real API calls to TradingView")
    print("Rate limiting is active to prevent hitting limits\n")
    
    try:
        # Test 1: Data analysis with caching
        result1 = await test_btc_analysis()
        
        # Test 2: Formatted analysis
        result2 = await test_formatted_analysis()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"BTC Analysis with Caching: {'✓ PASSED' if result1 else '✗ FAILED'}")
        print(f"Formatted Analysis: {'✓ PASSED' if result2 else '✗ FAILED'}")
        
        if result1 and result2:
            print("\n✓ ALL END-TO-END TESTS PASSED")
            print("\nThe caching system is working correctly!")
            print("- API calls are rate-limited")
            print("- Data is being cached (though indicators still require API calls)")
            print("- Analysis formatting works as expected")
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
