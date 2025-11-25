#!/usr/bin/env python3
"""Test the Parabolic SAR signal function with USDJPY"""

from agent import get_parabolic_sar_signal

if __name__ == "__main__":
    print("Testing Parabolic SAR Signal Function with USDJPY")
    print("=" * 70)
    print()

    # Test with USDJPY (forex pair)
    result = get_parabolic_sar_signal("USDJPY", "forex", "FX_IDC")
    print(result)
