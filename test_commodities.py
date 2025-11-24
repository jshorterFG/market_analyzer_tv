from tradingview_ta import TA_Handler, Interval, Exchange

def test_symbol(symbol, screener, exchange):
    print(f"Testing {symbol} on {exchange} ({screener})...")
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener=screener,
            exchange=exchange,
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        print(f"Success! Recommendation: {analysis.summary['RECOMMENDATION']}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

print("--- US Indexes ---")
test_symbol("SPX", "america", "TVC") # S&P 500
test_symbol("DJI", "america", "TVC") # Dow Jones
test_symbol("IXIC", "america", "NASDAQ") # Nasdaq Composite

print("\n--- Energy ---")
test_symbol("USOIL", "cfd", "TVC") # WTI Crude Oil
test_symbol("UKOIL", "cfd", "TVC") # Brent Crude Oil
test_symbol("NG1!", "america", "NYMEX") # Natural Gas Futures

print("\n--- Metals ---")
test_symbol("XAUUSD", "forex", "FX_IDC") # Gold Spot
test_symbol("GC1!", "america", "COMEX") # Gold Futures
test_symbol("XAGUSD", "forex", "FX_IDC") # Silver Spot
