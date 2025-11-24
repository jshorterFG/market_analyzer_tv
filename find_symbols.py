from tradingview_ta import TA_Handler, Interval, Exchange

def search_and_test(query, category):
    print(f"\nSearching for {category} ({query})...")
    # Note: tradingview_ta doesn't have a direct search method exposed easily in the main import, 
    # but we can try to guess or just test common configurations.
    
    configs = [
        ("america", "TVC"),
        ("america", "CBOE"),
        ("america", "DJ"),
        ("cfd", "TVC"),
        ("cfd", "FX_IDC"),
        ("forex", "FX_IDC"),
        ("forex", "OANDA"),
    ]
    
    for screener, exchange in configs:
        try:
            handler = TA_Handler(
                symbol=query,
                screener=screener,
                exchange=exchange,
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()
            print(f"  FOUND! {query} on {exchange} ({screener}) -> {analysis.summary['RECOMMENDATION']}")
            return
        except Exception:
            pass
    print(f"  Not found: {query}")

search_and_test("SPX", "S&P 500")
search_and_test("DJI", "Dow Jones")
search_and_test("USOIL", "US Oil")
search_and_test("XAUUSD", "Gold")
search_and_test("XAGUSD", "Silver")
