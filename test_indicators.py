from tradingview_ta import TA_Handler, Interval

print("Testing enhanced indicators...")
try:
    handler = TA_Handler(
        symbol="BTCUSDT",
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.INTERVAL_15_MINUTES
    )
    analysis = handler.get_analysis()
    
    print("\nAvailable indicators:")
    for key in sorted(analysis.indicators.keys()):
        print(f"  {key}: {analysis.indicators[key]}")
    
except Exception as e:
    print(f"Error: {e}")
