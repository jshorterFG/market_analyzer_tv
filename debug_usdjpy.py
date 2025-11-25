#!/usr/bin/env python3
"""Debug which timeframes are available for USDJPY"""

from server import get_analysis_data
import time

symbol = "USDJPY"
screener = "forex"
exchange = "FX_IDC"
timeframes = ["1m", "5m", "15m", "30m", "1h"]

print(f"Testing timeframe availability for {symbol} on {exchange}")
print("=" * 70)

for tf in timeframes:
    try:
        data = get_analysis_data(symbol, screener, exchange, tf)
        if data and data.get('close') is not None:
            print(f"✅ {tf:4s}: Available - Close: {data.get('close')}, PSAR: {data.get('psar')}, FI: {data.get('fi')}")
        else:
            print(f"❌ {tf:4s}: No data returned")
        time.sleep(2)  # Rate limiting
    except Exception as e:
        print(f"❌ {tf:4s}: Error - {str(e)}")
        time.sleep(2)
