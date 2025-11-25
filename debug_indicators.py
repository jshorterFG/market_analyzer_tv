from tradingview_ta import TA_Handler, Interval, Exchange

handler = TA_Handler(
    symbol="BTCUSDT",
    screener="crypto",
    exchange="BINANCE",
    interval=Interval.INTERVAL_15_MINUTES
)

analysis = handler.get_analysis()
print("Available Indicators:")
for key in sorted(analysis.indicators.keys()):
    print(f"{key}: {analysis.indicators[key]}")
