#!/usr/bin/env python3
"""Test the Parabolic SAR signal function with EURUSD and demonstrate rate limit estimation"""

from agent import get_parabolic_sar_signal

if __name__ == "__main__":
    print("Testing Parabolic SAR Signal Function with Rate Limit Estimation")
    print("=" * 70)
    print()

    # Test with EURUSD (forex pair that should work)
    print("Testing EURUSD (Forex)...")
    result = get_parabolic_sar_signal("EURUSD", "forex", "FX_IDC")
    print(result)
    print()
