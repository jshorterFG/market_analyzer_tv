from tradingview_ta import TA_Handler, Interval

def test(symbol, screener, exchange):
    try:
        handler = TA_Handler(symbol=symbol, screener=screener, exchange=exchange, interval=Interval.INTERVAL_1_DAY)
        print(f"{symbol} | {screener} | {exchange} -> {handler.get_analysis().summary['RECOMMENDATION']}")
    except Exception as e:
        print(f"{symbol} | {screener} | {exchange} -> Failed")

print("Testing Oil...")
test("USOIL", "cfd", "TVC")
test("WTI", "cfd", "TVC")
test("CL1!", "america", "NYMEX")
test("CL1!", "america", "CME")

print("\nTesting Silver...")
test("XAGUSD", "forex", "FX_IDC")
test("XAGUSD", "cfd", "FX_IDC")
test("XAGUSD", "cfd", "TVC")
