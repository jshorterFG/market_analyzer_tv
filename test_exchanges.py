#!/usr/bin/env python3
"""Test different exchanges for USDJPY"""

import asyncio
from server import get_analysis_data
import time

async def main():
    symbol = "USDJPY"
    screener = "forex"
    exchanges = ["FX_IDC", "OANDA", "FX"]
    timeframe = "15m"

    print(f"Testing exchanges for {symbol} on {timeframe} timeframe")
    print("=" * 70)

    for exchange in exchanges:
        try:
            data = await get_analysis_data(symbol, screener, exchange, timeframe)
            if data and data.get('close') is not None:
                print(f"✅ {exchange:10s}: Available - Close: {data.get('close'):.4f}, PSAR: {data.get('psar')}, FI: {data.get('fi')}")
            else:
                print(f"❌ {exchange:10s}: No data returned")
            # Small delay to be nice to the API
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ {exchange:10s}: Error - {str(e)}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
