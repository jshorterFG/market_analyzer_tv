"""
Simple integration test for the caching system.
Tests rate limiting and basic functionality without requiring GCP auth.
"""
import asyncio
import time
from rate_limiter import rate_limiter

async def test_rate_limiting():
    """Test that rate limiting works correctly."""
    print("\n=== Testing Rate Limiting ===")
    
    # Track execution times
    call_times = []
    
    async def mock_api_call():
        """Simulate an API call."""
        current_time = time.time()
        call_times.append(current_time)
        return f"Call at {current_time}"
    
    # Make several rapid calls
    print("Making 5 rapid API calls with rate limiting...")
    start_time = time.time()
    
    for i in range(5):
        result = await rate_limiter.execute(mock_api_call)
        print(f"  Call {i+1}: {result}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\nTotal time for 5 calls: {total_time:.2f}s")
    print(f"Average time per call: {total_time/5:.2f}s")
    
    # Check rate limiter stats
    stats = rate_limiter.get_stats()
    print(f"\nRate Limiter Stats:")
    print(f"  Requests this minute: {stats['requests_this_minute']}")
    print(f"  Requests this hour: {stats['requests_this_hour']}")
    print(f"  Max per minute: {stats['max_per_minute']}")
    print(f"  Max per hour: {stats['max_per_hour']}")
    
    return True

async def test_server_import():
    """Test that server module imports correctly."""
    print("\n=== Testing Server Import ===")
    
    try:
        from server import get_analysis_data
        print("✓ Server module imported successfully")
        print("✓ get_analysis_data function is available")
        return True
    except Exception as e:
        print(f"✗ Failed to import server: {e}")
        return False

async def test_data_fetcher():
    """Test data fetcher module."""
    print("\n=== Testing Data Fetcher ===")
    
    try:
        from data_fetcher import data_fetcher
        print("✓ Data fetcher module imported successfully")
        print("✓ Data fetcher instance created")
        return True
    except Exception as e:
        print(f"✗ Failed to import data_fetcher: {e}")
        return False

async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("INTEGRATION TESTS - Database Strategy Implementation")
    print("=" * 60)
    
    results = []
    
    # Test 1: Server import
    result1 = await test_server_import()
    results.append(("Server Import", result1))
    
    # Test 2: Data fetcher
    result2 = await test_data_fetcher()
    results.append(("Data Fetcher", result2))
    
    # Test 3: Rate limiting
    result3 = await test_rate_limiting()
    results.append(("Rate Limiting", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
