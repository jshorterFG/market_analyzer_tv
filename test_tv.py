from tradingview_ta import TA_Handler, Interval, Exchange

def test_analysis():
    print("Testing TradingView Analysis...")
    
    # Test Stock (Tesla)
    try:
        tesla = TA_Handler(
            symbol="TSLA",
            screener="america",
            exchange="NASDAQ",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = tesla.get_analysis()
        print(f"TSLA Recommendation: {analysis.summary['RECOMMENDATION']}")
        print(f"RSI: {analysis.indicators['RSI']}")
    except Exception as e:
        print(f"Error testing TSLA: {e}")

    # Test Crypto (Bitcoin)
    try:
        btc = TA_Handler(
            symbol="BTCUSDT",
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = btc.get_analysis()
        print(f"BTCUSDT Recommendation: {analysis.summary['RECOMMENDATION']}")
    except Exception as e:
        print(f"Error testing BTCUSDT: {e}")

if __name__ == "__main__":
    test_analysis()
