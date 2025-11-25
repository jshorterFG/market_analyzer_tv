#!/usr/bin/env python3
"""
Quick test script for the Parabolic SAR signal function
"""

from agent import get_parabolic_sar_signal

if __name__ == "__main__":
    # Test with a popular crypto pair
    print("Testing Parabolic SAR Signal Function")
    print("=" * 70)
    print()

    try:
        result = get_parabolic_sar_signal("BTCUSDT", "crypto", "BINANCE")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
