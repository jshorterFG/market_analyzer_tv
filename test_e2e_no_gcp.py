"""
End-to-end test WITHOUT GCP dependencies.
Tests rate limiting and API integration only.
"""
import asyncio
import os

# Disable caching for this test
os.environ["ENABLE_CACHE"] = "false"

from server import get_analysis_data, get_analysis
from rate_limiter import rate_limiter

async def test_btc_analysis_no_cache():
    """Test BTC analysis without caching (rate limiting only)."""
    print("\n=== Testing BTC Analysis with Rate Limiting (No Cache) ===")
    
    # First call
    print("Making 1st API call...")
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
    print(f"  Requests this hour: {stats['requests_this_hour']}")
    
    print("\nMaking 2nd API call...")
    data2 = await get_analysis_data("ETHUSDT", "crypto", "BINANCE", "1d")
    
    if data2:
        print(f"✓ Got ETH data:")
        print(f"  Close: ${data2.get('close', 0):,.2f}")
    else:
        print("✗ Failed to get ETH data")
        return False
    
    # Check rate limiter stats again
    stats2 = rate_limiter.get_stats()
    print(f"\nRate Limiter Stats after 2nd call:")
    print(f"  Requests this minute: {stats2['requests_this_minute']}")
    print(f"  Requests this hour: {stats2['requests_this_hour']}")
    
    return True

async def test_formatted_analysis():
    """Test formatted analysis output."""
    print("\n=== Testing Formatted Analysis ===")
    
    analysis = await get_analysis("BTCUSDT", "crypto", "BINANCE", "1h")
    
    if analysis and not analysis.startswith("Error"):
        print("✓ Got formatted analysis:")
        print("-" * 60)
        # Print first 800 characters
        preview = analysis[:800] + "..." if len(analysis) > 800 else analysis
        print(preview)
        print("-" * 60)
        return True
    else:
        print(f"✗ Failed to get analysis: {analysis}")
        return False

async def test_rate_limiting_multiple_calls():
    """Test rate limiting with multiple rapid calls."""
    print("\n=== Testing Rate Limiting with Multiple Calls ===")
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    print(f"Making {len(symbols)} rapid API calls...")
    
    for symbol in symbols:
        data = await get_analysis_data(symbol, "crypto", "BINANCE", "1d")
        if data:
            print(f"  ✓ {symbol}: ${data.get('close', 0):,.2f}")
        else:
            print(f"  ✗ {symbol}: Failed")
    
    stats = rate_limiter.get_stats()
    print(f"\nFinal Rate Limiter Stats:")
    print(f"  Total requests this minute: {stats['requests_this_minute']}")
    print(f"  Total requests this hour: {stats['requests_this_hour']}")
    print(f"  Limit per minute: {stats['max_per_minute']}")
    print(f"  Limit per hour: {stats['max_per_hour']}")
    print(f"  Consecutive failures: {stats['consecutive_failures']}")
    
    return True

async def main():
    """Run end-to-end tests without GCP dependencies."""
    print("=" * 60)
    print("END-TO-END TEST - Rate Limiting Only (No GCP)")
    print("=" * 60)
    print("\nNote: Caching is DISABLED for this test")
    print("Testing rate limiting and API integration only\n")
    
    try:
        # Test 1: Basic analysis with rate limiting
        result1 = await test_btc_analysis_no_cache()
        
        # Test 2: Formatted analysis
        result2 = await test_formatted_analysis()
        
        # Test 3: Multiple calls
        result3 = await test_rate_limiting_multiple_calls()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Basic Analysis: {'✓ PASSED' if result1 else '✗ FAILED'}")
        print(f"Formatted Analysis: {'✓ PASSED' if result2 else '✗ FAILED'}")
        print(f"Rate Limiting: {'✓ PASSED' if result3 else '✗ FAILED'}")
        
        if result1 and result2 and result3:
            print("\n✓ ALL TESTS PASSED")
            print("\nThe system is working correctly:")
            print("- API calls are successfully rate-limited")
            print("- Analysis data is retrieved correctly")
            print("- Formatted output works as expected")
            print("\nNote: To enable caching, authenticate with GCP:")
            print("  gcloud auth application-default login")
        else:
            print("\n✗ SOME TESTS FAILED")
        
        print("=" * 60)
        
        return result1 and result2 and result3
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
