from agent import get_multi_timeframe_analysis

if __name__ == "__main__":
    print("Testing multi-timeframe analysis...")
    try:
        result = get_multi_timeframe_analysis("BTCUSDT", "crypto", "BINANCE")
        print("Success!")
        print(result[:500])
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
