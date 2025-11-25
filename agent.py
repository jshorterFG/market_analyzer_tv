import vertexai
import asyncio
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from server import get_analysis

# Initialize Vertex AI
PROJECT_ID = "sp500trading"
LOCATION = "us-central1" # You might want to ask the user for location or default to one

vertexai.init(project=PROJECT_ID, location=LOCATION)

# Define Tool Functions
def get_crypto_analysis(symbol: str, exchange: str = "BINANCE", interval: str = "1d"):
    """Get technical analysis for a crypto pair."""
    return asyncio.run(get_analysis(symbol, "crypto", exchange, interval))

def get_stock_analysis(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """Get technical analysis for a stock."""
    return asyncio.run(get_analysis(symbol, "america", exchange, interval))

def get_forex_analysis(symbol: str, exchange: str = "FX_IDC", interval: str = "1d"):
    """Get technical analysis for a forex pair."""
    return asyncio.run(get_analysis(symbol, "forex", exchange, interval))

def get_index_analysis(symbol: str, exchange: str = "CBOE", interval: str = "1d"):
    """Get technical analysis for a US index.
    
    Common symbols:
    - SPX (S&P 500) on CBOE
    - DJI (Dow Jones) on DJ
    - IXIC (Nasdaq Composite) on NASDAQ
    """
    # Map common index symbols to their correct exchanges
    index_exchanges = {
        "SPX": "CBOE",
        "DJI": "DJ",
        "IXIC": "NASDAQ"
    }
    
    if symbol in index_exchanges:
        exchange = index_exchanges[symbol]
    
    return asyncio.run(get_analysis(symbol, "america", exchange, interval))

def get_commodity_analysis(symbol: str, exchange: str = "TVC", interval: str = "1d"):
    """Get technical analysis for commodities (energy, metals).
    
    Common symbols:
    - XAUUSD (Gold) on FX_IDC (use cfd screener)
    - For other commodities, specify the exchange
    """
    # Gold uses cfd screener
    if symbol == "XAUUSD":
        return asyncio.run(get_analysis(symbol, "cfd", "FX_IDC", interval))
    
    return asyncio.run(get_analysis(symbol, "cfd", exchange, interval))

def get_multi_timeframe_analysis(symbol: str, asset_type: str = "crypto", exchange: str = "BINANCE") -> str:
    """
    Get comprehensive technical analysis across multiple timeframes (5m, 15m, 30m, 1h) to provide 
    entry, stop loss, and take profit recommendations for trading decisions.
    
    This tool analyzes trend indicators, oscillators, moving averages, candle patterns, and provides
    bullish/bearish direction to help determine optimal entry points, stop loss levels, and profit targets.
    
    Args:
        symbol: The trading symbol (e.g., 'BTCUSDT', 'TSLA', 'SPX')
        asset_type: Type of asset - 'crypto', 'stock', 'forex', 'index', or 'commodity'
        exchange: The exchange (default varies by asset_type)
    
    Returns:
        Detailed multi-timeframe analysis with trend direction, key levels, and trading signals.
    """
    import time
    import asyncio
    from datetime import datetime, timedelta
    
    # Map asset types to screeners
    screener_map = {
        "crypto": "crypto",
        "stock": "america",
        "forex": "forex",
        "index": "america",
        "commodity": "cfd"
    }
    
    # Set default exchanges
    if asset_type == "crypto" and exchange == "BINANCE":
        exchange = "BINANCE"
    elif asset_type == "stock" and exchange == "BINANCE":
        exchange = "NASDAQ"
    elif asset_type == "index":
        index_exchanges = {"SPX": "CBOE", "DJI": "DJ", "IXIC": "NASDAQ"}
        exchange = index_exchanges.get(symbol, "CBOE")
    elif asset_type == "forex" and exchange == "BINANCE":
        exchange = "FX_IDC"
    elif asset_type == "commodity" and symbol == "XAUUSD":
        exchange = "FX_IDC"
    
    screener = screener_map.get(asset_type, "crypto")
    
    timeframes = ["5m", "15m", "30m", "1h"]
    results = {}
    
    start_time = datetime.now()
    
    for i, tf in enumerate(timeframes):
        try:
            # Add delay between requests to avoid rate limiting (except for first request)
            if i > 0:
                time.sleep(3)  # Wait 3 seconds between requests
            
            analysis_text = asyncio.run(get_analysis(symbol, screener, exchange, tf))
            results[tf] = analysis_text
        except Exception as e:
            results[tf] = f"Error: {str(e)}"
    
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # Calculate when next analysis can be safely done (recommend 2 minutes wait)
    next_analysis_time = end_time + timedelta(minutes=2)
    
    # Format output
    output = f"Multi-Timeframe Analysis for {symbol} on {exchange}\n"
    output += "=" * 60 + "\n\n"
    
    for tf, result in results.items():
        output += f"--- {tf.upper()} Timeframe ---\n"
        output += result + "\n\n"
    
    # Add rate limiting info
    output += "=" * 60 + "\n"
    output += f"Analysis completed in {elapsed_time:.1f} seconds\n"
    output += f"⏰ RATE LIMIT INFO: To avoid API errors, wait until {next_analysis_time.strftime('%H:%M:%S')} "
    output += f"(~2 minutes) before requesting another multi-timeframe analysis.\n"
    output += "Single timeframe requests can be made immediately.\n"
    
    return output

def get_parabolic_sar_signal(symbol: str, asset_type: str = "crypto", exchange: str = "BINANCE") -> str:
    """
    Analyze Parabolic SAR across multiple timeframes (1m, 5m, 15m, 30m, 1h) to generate 
    buy/sell signals with stop loss and take profit levels.
    
    This strategy:
    1. Checks if ALL Parabolic SAR indicators across timeframes are aligned (all bullish or all bearish)
    2. Uses the 1-minute candle direction to confirm the trade signal
    3. Calculates stop loss and take profit based on the 15-minute timeframe
    
    Args:
        symbol: The trading symbol (e.g., 'BTCUSDT', 'TSLA', 'SPX')
        asset_type: Type of asset - 'crypto', 'stock', 'forex', 'index', or 'commodity'
        exchange: The exchange (default varies by asset_type)
    
    Returns:
        Trading signal with entry price, stop loss, and take profit levels, or no signal if SAR not aligned.
    """
    import time
    import asyncio
    from datetime import datetime, timedelta
    from server import get_analysis_data  # We'll need raw data, not formatted text
    
    # Supported symbols only
    SUPPORTED_SYMBOLS = {
        "SPX": {"asset_type": "index", "exchange": "CBOE", "screener": "america"},
        "USOIL": {"asset_type": "commodity", "exchange": "TVC", "screener": "cfd"},
        "XAUUSD": {"asset_type": "forex", "exchange": "FX_IDC", "screener": "cfd"},
        "BTCUSDT": {"asset_type": "crypto", "exchange": "BINANCE", "screener": "crypto"},
        "COIN": {"asset_type": "stock", "exchange": "NASDAQ", "screener": "america"},
        "USDJPY": {"asset_type": "forex", "exchange": "FX_IDC", "screener": "forex"}
    }
    
    # Validate symbol
    if symbol not in SUPPORTED_SYMBOLS:
        supported_list = ", ".join(SUPPORTED_SYMBOLS.keys())
        return f"""
⚠️ UNSUPPORTED SYMBOL: {symbol}

This analyzer only supports the following symbols:
  • SPX (S&P 500 Index)
  • USOIL (Crude Oil)
  • XAUUSD (Gold)
  • BTCUSDT (Bitcoin)
  • COIN (Coinbase Stock)
  • USDJPY (USD/JPY Forex)

Please analyze one of these symbols instead.

======================================================================
⚠️ DISCLAIMER
======================================================================
This analysis and all recommendations are provided for ENTERTAINMENT PURPOSES ONLY.
This is NOT financial advice. Trading involves substantial risk of loss.
Always conduct your own research and consult with a licensed financial advisor
before making any trading decisions.
"""
    
    # Get symbol configuration
    symbol_config = SUPPORTED_SYMBOLS[symbol]
    screener = symbol_config["screener"]
    if exchange == "BINANCE" or exchange not in [symbol_config["exchange"]]:
        exchange = symbol_config["exchange"]
    
    # Track analysis timing for rate limit estimation
    start_time = datetime.now()
    
    # Timeframes to analyze
    timeframes = ["1m", "5m", "15m"]
    sar_data = {}
    
    output = f"Parabolic SAR Multi-Timeframe Analysis for {symbol} on {exchange}\n"
    output += "=" * 70 + "\n\n"
    
    # Fetch data for all timeframes
    for i, tf in enumerate(timeframes):
        try:
            if i > 0:
                time.sleep(2)  # Rate limiting
            
            # Use asyncio.run to execute the async function
            data = asyncio.run(get_analysis_data(symbol, screener, exchange, tf))
            if data:
                sar_data[tf] = data
        except Exception as e:
            output += f"⚠️ Error fetching {tf} data: {str(e)}\n"
            return output + "\n❌ Cannot generate signal due to data fetch errors.\n"
    
    # Check if we have all required data
    if len(sar_data) != len(timeframes):
        output += "❌ Missing data for some timeframes. Cannot generate signal.\n"
        return output
    
    # Analyze SAR alignment
    output += "📊 Parabolic SAR Analysis by Timeframe:\n"
    output += "-" * 70 + "\n"
    
    sar_bullish_count = 0
    sar_bearish_count = 0
    
    # First check if ANY data is from cache (rate limited)
    has_cached_data = any(sar_data[tf].get('from_cache', False) for tf in timeframes if tf in sar_data)
    
    if has_cached_data:
        # Automatically provide simple price analysis with cached data
        output += f"\n{'='*70}\n"
        cache_warning = sar_data.get(timeframes[0], {}).get('cache_warning')
        if cache_warning:
            output += f"{cache_warning}\n"
        else:
            output += "⚠️ Rate limit exceeded - using cached data.\n"
        output += f"{'='*70}\n\n"
        output += "📊 Simple Price Analysis (Cached Data)\n"
        output += "-" * 70 + "\n\n"
        
        # Provide candle analysis for each available timeframe
        for tf in timeframes:
            if tf not in sar_data:
                continue
                
            data = sar_data[tf]
            open_price = data.get('open')
            high_price = data.get('high')
            low_price = data.get('low')
            close_price = data.get('close')
            
            if not all([open_price, high_price, low_price, close_price]):
                continue
            
            candle_range = high_price - low_price
            candle_body = abs(close_price - open_price)
            body_pct = (candle_body / candle_range * 100) if candle_range > 0 else 0
            
            output += f"{tf.upper()} Timeframe:\n"
            output += f"  Open: {open_price:.4f} | High: {high_price:.4f} | Low: {low_price:.4f} | Close: {close_price:.4f}\n"
            
            if close_price > open_price:
                output += f"  🟢 Bullish Candle - Body: {candle_body:.4f} ({body_pct:.1f}% of range)\n"
            elif close_price < open_price:
                output += f"  🔴 Bearish Candle - Body: {candle_body:.4f} ({body_pct:.1f}% of range)\n"
            else:
                output += f"  ⚪ Doji Candle - No directional bias\n"
            output += "\n"
        
        # Provide basic recommendation based on 1m and 15m candles
        data_1m = sar_data.get("1m", {})
        data_15m = sar_data.get("15m", {})
        
        close_1m = data_1m.get('close')
        open_1m = data_1m.get('open')
        close_15m = data_15m.get('close')
        open_15m = data_15m.get('open')
        high_15m = data_15m.get('high')
        low_15m = data_15m.get('low')
        
        if all([close_1m, open_1m, close_15m, open_15m, high_15m, low_15m]):
            output += "=" * 70 + "\n"
            output += "📍 Basic Price Levels (Cached Data)\n"
            output += "=" * 70 + "\n"
            
            range_15m = high_15m - low_15m
            bullish_1m = close_1m > open_1m
            bullish_15m = close_15m > open_15m
            
            if bullish_1m and bullish_15m:
                # Both bullish
                entry = close_1m
                stop = low_15m - (range_15m * 0.1)
                tp1 = entry + (range_15m * 1.5)
                tp2 = entry + (range_15m * 2.5)
                
                output += "Direction: 🟢 BULLISH (Watch Levels)\n"
                output += f"Entry Zone:     {entry:.4f}\n"
                output += f"Stop Loss:      {stop:.4f}\n"
                output += f"Take Profit 1:  {tp1:.4f}\n"
                output += f"Take Profit 2:  {tp2:.4f}\n"
                
            elif not bullish_1m and not bullish_15m:
                # Both bearish
                entry = close_1m
                stop = high_15m + (range_15m * 0.1)
                tp1 = entry - (range_15m * 1.5)
                tp2 = entry - (range_15m * 2.5)
                
                output += "Direction: 🔴 BEARISH (Watch Levels)\n"
                output += f"Entry Zone:     {entry:.4f}\n"
                output += f"Stop Loss:      {stop:.4f}\n"
                output += f"Take Profit 1:  {tp1:.4f}\n"
                output += f"Take Profit 2:  {tp2:.4f}\n"
            else:
                # Mixed signals
                output += "Direction: ⚪ MIXED SIGNALS\n"
                output += f"Current Price:  {close_1m:.4f}\n"
                output += f"15m High:       {high_15m:.4f}\n"
                output += f"15m Low:        {low_15m:.4f}\n"
                output += f"15m Range:      {range_15m:.4f}\n"
            
            output += "\n⚠️ Note: These levels are based on cached price data only.\n"
            output += "   For complete SAR analysis with all indicators, please retry in a moment.\n"
        
        return output
    
    # Check if we have valid SAR data for non-cached responses
    for tf in timeframes:
        data = sar_data[tf]
        psar = data.get('psar')
        close = data.get('close')
        
        if psar is None or close is None:
            output += f"{tf:>5}: ⚠️ SAR data not available\n"
            output += "\n❌ Cannot generate signal - missing SAR data.\n"
            output += "   This may indicate an API issue or unsupported timeframe.\n"
            output += "   Please try again or use a different analysis tool.\n"
            return output
        
        if close > psar:
            sar_bullish_count += 1
            signal = "🟢 BULLISH"
        else:
            sar_bearish_count += 1
            signal = "🔴 BEARISH"
        
        output += f"{tf:>5}: Price: {close:.4f} | SAR: {psar:.4f} | {signal}\n"
    
    output += "-" * 70 + "\n"
    output += f"Alignment: {sar_bullish_count} Bullish / {sar_bearish_count} Bearish\n\n"
    
    # Check if all SAR indicators are aligned
    all_bullish = sar_bullish_count == len(timeframes)
    all_bearish = sar_bearish_count == len(timeframes)
    
    if not (all_bullish or all_bearish):
        output += "⚠️ Parabolic SAR indicators are NOT aligned across all timeframes.\n"
        output += "   Using 15m timeframe for potential setup levels.\n"
    
    # Get 1-minute candle direction
    data_1m = sar_data["1m"]
    open_1m = data_1m.get('open')
    close_1m = data_1m.get('close')
    
    if open_1m is None or close_1m is None:
        output += "❌ Cannot determine 1-minute candle direction.\n"
        return output
    
    candle_bullish = close_1m > open_1m
    candle_bearish = close_1m < open_1m
    
    output += "🕐 1-Minute Candle Analysis:\n"
    output += f"   Open: {open_1m:.4f} | Close: {close_1m:.4f}\n"
    if candle_bullish:
        output += "   Direction: 🟢 BULLISH (Close > Open)\n\n"
    elif candle_bearish:
        output += "   Direction: 🔴 BEARISH (Close < Open)\n\n"
    else:
        output += "   Direction: ⚪ DOJI (Close = Open)\n\n"
    
    # Get 15-minute data for stop loss and take profit calculation
    data_15m = sar_data["15m"]
    high_15m = data_15m.get('high')
    low_15m = data_15m.get('low')
    close_15m = data_15m.get('close')
    psar_15m = data_15m.get('psar')
    fi_15m = data_15m.get('fi')
    
    if high_15m is None or low_15m is None or close_15m is None:
        output += "❌ Cannot calculate stop loss/take profit - missing 15m data.\n"
        return output
    
    # Calculate ATR-like range from 15m candle
    range_15m = high_15m - low_15m
    
    # Force Index Analysis (15m)
    fi_status = "N/A"
    fi_bullish = False
    fi_bearish = False
    
    if fi_15m is not None:
        if fi_15m > 0:
            fi_status = f"🟢 POSITIVE ({fi_15m:.4f})"
            fi_bullish = True
        else:
            fi_status = f"🔴 NEGATIVE ({fi_15m:.4f})"
            fi_bearish = True
    
    output += f"💪 15m Force Index: {fi_status}\n\n"
    
    # Determine direction for recommendation
    # Priority 1: All timeframes aligned + 1m candle confirms + 15m FI confirms (STRONG SIGNAL)
    # Priority 2: 15m trend direction (POTENTIAL SETUP)
    
    is_strong_signal = False
    recommendation_type = "POTENTIAL SETUP (Watch Levels)"
    
    if all_bullish and candle_bullish and fi_bullish:
        direction = "BUY"
        is_strong_signal = True
        recommendation_type = "✅ TRADING SIGNAL: BUY"
    elif all_bearish and candle_bearish and fi_bearish:
        direction = "SELL"
        is_strong_signal = True
        recommendation_type = "✅ TRADING SIGNAL: SELL"
    else:
        # Fallback to 15m SAR direction
        if close_15m > psar_15m:
            direction = "BUY"
            recommendation_type = "⚠️ POTENTIAL BUY SETUP (Conditions not fully met)"
        else:
            direction = "SELL"
            recommendation_type = "⚠️ POTENTIAL SELL SETUP (Conditions not fully met)"

    # Generate trading values
    output += "=" * 70 + "\n"
    output += f"{recommendation_type}\n"
    output += "=" * 70 + "\n"
    
    if direction == "BUY":
        entry_price = close_1m
        stop_loss = psar_15m if psar_15m else (low_15m - range_15m * 0.1)
        take_profit_1 = entry_price + (range_15m * 1.5)
        take_profit_2 = entry_price + (range_15m * 2.5)
        
        risk = entry_price - stop_loss
        reward_1 = take_profit_1 - entry_price
        reward_2 = take_profit_2 - entry_price
        
        # Handle edge case where SL is above Entry (shouldn't happen with SAR logic but safety check)
        if risk <= 0:
            risk = range_15m * 0.5 # Fallback risk
            stop_loss = entry_price - risk
            
        output += f"📍 Entry Price:     {entry_price:.4f}\n"
        output += f"🛑 Stop Loss:       {stop_loss:.4f} (Risk: {risk:.4f} or {(risk/entry_price*100):.2f}%)\n"
        output += f"🎯 Take Profit 1:   {take_profit_1:.4f} (Reward: {reward_1:.4f}, R:R = 1:{(reward_1/risk):.2f})\n"
        output += f"🎯 Take Profit 2:   {take_profit_2:.4f} (Reward: {reward_2:.4f}, R:R = 1:{(reward_2/risk):.2f})\n"
        
        if is_strong_signal:
            output += "\n💡 Strategy: All Parabolic SAR indicators are bullish and 1m candle confirms upward momentum.\n"
        else:
            output += "\n💡 Analysis: Strict alignment conditions NOT met. Showing levels based on 15m trend.\n"
            if not all_bullish:
                output += "   - Warning: Not all timeframes are bullish.\n"
            if not candle_bullish:
                output += "   - Warning: 1m candle is not bullish.\n"
            output += "   Wait for confirmation before entering.\n"
            
    else: # SELL
        entry_price = close_1m
        stop_loss = psar_15m if psar_15m else (high_15m + range_15m * 0.1)
        take_profit_1 = entry_price - (range_15m * 1.5)
        take_profit_2 = entry_price - (range_15m * 2.5)
        
        risk = stop_loss - entry_price
        reward_1 = entry_price - take_profit_1
        reward_2 = entry_price - take_profit_2
        
        # Handle edge case
        if risk <= 0:
            risk = range_15m * 0.5
            stop_loss = entry_price + risk

        output += f"📍 Entry Price:     {entry_price:.4f}\n"
        output += f"🛑 Stop Loss:       {stop_loss:.4f} (Risk: {risk:.4f} or {(risk/entry_price*100):.2f}%)\n"
        output += f"🎯 Take Profit 1:   {take_profit_1:.4f} (Reward: {reward_1:.4f}, R:R = 1:{(reward_1/risk):.2f})\n"
        output += f"🎯 Take Profit 2:   {take_profit_2:.4f} (Reward: {reward_2:.4f}, R:R = 1:{(reward_2/risk):.2f})\n"
        
        if is_strong_signal:
            output += "\n💡 Strategy: All Parabolic SAR indicators are bearish and 1m candle confirms downward momentum.\n"
        else:
            output += "\n💡 Analysis: Strict alignment conditions NOT met. Showing levels based on 15m trend.\n"
            if not all_bearish:
                output += "   - Warning: Not all timeframes are bearish.\n"
            if not candle_bearish:
                output += "   - Warning: 1m candle is not bearish.\n"
            output += "   Wait for confirmation before entering.\n"
            
    output += f"   Based on 15m timeframe: High={high_15m:.4f}, Low={low_15m:.4f}, Range={range_15m:.4f}\n\n"
    
    # Add Order Recommendations Section
    output += "=" * 70 + "\n"
    output += "📋 ORDER RECOMMENDATIONS\n"
    output += "=" * 70 + "\n\n"
    
    if direction == "BUY":
        # Immediate Orders
        output += "🟢 IMMEDIATE ORDERS (Market Execution):\n"
        output += f"   Market Buy @ {entry_price:.4f}\n"
        output += f"   Set Stop Loss: {stop_loss:.4f}\n"
        output += f"   Set Take Profit 1: {take_profit_1:.4f} (Partial close)\n"
        output += f"   Set Take Profit 2: {take_profit_2:.4f} (Full close)\n\n"
        
        # Pending Orders  
        pullback_entry = entry_price - (range_15m * 0.3)
        pullback_sl = pullback_entry - (range_15m * 0.5)
        pullback_tp1 = pullback_entry + (range_15m * 1.5)
        pullback_tp2 = pullback_entry + (range_15m * 2.5)
        
        breakout_entry = high_15m + (range_15m * 0.1)
        breakout_sl = high_15m - (range_15m * 0.2)
        breakout_tp1 = breakout_entry + (range_15m * 1.5)
        breakout_tp2 = breakout_entry + (range_15m * 2.5)
        
        output += "⏸️ PENDING ORDERS (If Retracement):\n"
        output += f"   Buy Limit @ {pullback_entry:.4f}\n"
        output += f"   Set Stop Loss: {pullback_sl:.4f}\n"
        output += f"   Set Take Profit 1: {pullback_tp1:.4f}\n"
        output += f"   Set Take Profit 2: {pullback_tp2:.4f}\n\n"
        
        output += "⏸️ PENDING ORDERS (If Breakout):\n"
        output += f"   Buy Stop @ {breakout_entry:.4f}\n"
        output += f"   Set Stop Loss: {breakout_sl:.4f}\n"
        output += f"   Set Take Profit 1: {breakout_tp1:.4f}\n"
        output += f"   Set Take Profit 2: {breakout_tp2:.4f}\n\n"
        
    else: # SELL
        # Immediate Orders
        output += "🔴 IMMEDIATE ORDERS (Market Execution):\n"
        output += f"   Market Sell @ {entry_price:.4f}\n"
        output += f"   Set Stop Loss: {stop_loss:.4f}\n"
        output += f"   Set Take Profit 1: {take_profit_1:.4f} (Partial close)\n"
        output += f"   Set Take Profit 2: {take_profit_2:.4f} (Full close)\n\n"
        
        # Pending Orders
        pullback_entry = entry_price + (range_15m * 0.3)
        pullback_sl = pullback_entry + (range_15m * 0.5)
        pullback_tp1 = pullback_entry - (range_15m * 1.5)
        pullback_tp2 = pullback_entry - (range_15m * 2.5)
        
        breakout_entry = low_15m - (range_15m * 0.1)
        breakout_sl = low_15m + (range_15m * 0.2)
        breakout_tp1 = breakout_entry - (range_15m * 1.5)
        breakout_tp2 = breakout_entry - (range_15m * 2.5)
        
        output += "⏸️ PENDING ORDERS (If Retracement):\n"
        output += f"   Sell Limit @ {pullback_entry:.4f}\n"
        output += f"   Set Stop Loss: {pullback_sl:.4f}\n"
        output += f"   Set Take Profit 1: {pullback_tp1:.4f}\n"
        output += f"   Set Take Profit 2: {pullback_tp2:.4f}\n\n"
        
        output += "⏸️ PENDING ORDERS (If Breakout):\n"
        output += f"   Sell Stop @ {breakout_entry:.4f}\n"
        output += f"   Set Stop Loss: {breakout_sl:.4f}\n"
        output += f"   Set Take Profit 1: {breakout_tp1:.4f}\n"
        output += f"   Set Take Profit 2: {breakout_tp2:.4f}\n"
    
    # Calculate rate limit information
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # We made API calls with delays between them
    # Recommend waiting ~2 minutes between analyses to avoid rate limits
    api_calls_made = len(timeframes)
    wait_time_seconds = 120  # 2 minutes recommended wait
    next_analysis_time = end_time + timedelta(seconds=wait_time_seconds)
    
    output += f"\n\n⏱️ RATE LIMIT INFO:\n"
    output += f"   Analysis completed in {elapsed_time:.1f} seconds\n"
    output += f"   API calls made: {api_calls_made}\n"
    output += f"   ⚠️ Wait until {next_analysis_time.strftime('%H:%M:%S')} (~{wait_time_seconds//60} minutes) before next analysis\n"
    output += f"   Single timeframe requests can be made immediately.\n\n"
    
    # Financial Disclaimer
    output += "=" * 70 + "\n"
    output += "⚠️ DISCLAIMER\n"
    output += "=" * 70 + "\n"
    output += "This analysis and all recommendations are provided for ENTERTAINMENT PURPOSES ONLY.\n"
    output += "This is NOT financial advice. Trading involves substantial risk of loss.\n"
    output += "Always conduct your own research and consult with a licensed financial advisor\n"
    output += "before making any trading decisions.\n"
    
    return output

# Define Function Declarations
get_crypto_analysis_func = FunctionDeclaration.from_func(get_crypto_analysis)
get_stock_analysis_func = FunctionDeclaration.from_func(get_stock_analysis)
get_forex_analysis_func = FunctionDeclaration.from_func(get_forex_analysis)
get_index_analysis_func = FunctionDeclaration.from_func(get_index_analysis)
get_commodity_analysis_func = FunctionDeclaration.from_func(get_commodity_analysis)
get_multi_timeframe_analysis_func = FunctionDeclaration.from_func(get_multi_timeframe_analysis)
get_parabolic_sar_signal_func = FunctionDeclaration.from_func(get_parabolic_sar_signal)

# Create the tools list
tools = Tool(
    function_declarations=[
        get_crypto_analysis_func,
        get_stock_analysis_func,
        get_forex_analysis_func,
        get_index_analysis_func,
        get_commodity_analysis_func,
        get_multi_timeframe_analysis_func,
        get_parabolic_sar_signal_func,
    ]
)

def create_chat():
    # Initialize the model with tools and system instruction
    system_instruction = """You are a professional market analysis assistant. Your role is to:

1. Use the available tools to fetch technical analysis data when users ask for market analysis
2. Provide clear, actionable trading recommendations including entry points, stop loss, and take profit levels
3. ALWAYS use the get_parabolic_sar_signal tool as your PRIMARY analysis method for any asset (crypto, forex, stocks)
4. Only use other tools if specifically asked for "simple analysis" or "indicators only"
5. Synthesize the technical data into specific price levels and trading advice
6. Be confident in your recommendations based on the technical indicators provided

When a user asks to "analyze" or for "recommendations":
- IMMEDIATELY call get_parabolic_sar_signal(symbol, asset_type, exchange)
- Do not ask for clarification, just run the analysis
- The tool will provide the Entry, Stop Loss, and Take Profit levels
- Present the tool's output directly to the user

The get_parabolic_sar_signal tool is specifically designed for:
- Checking if ALL Parabolic SAR indicators across multiple timeframes are aligned
- Using 1-minute candle direction to confirm the trade
- Calculating stop loss and take profit based on 15-minute timeframe data
- Providing "Potential Setup" levels even if alignment is not perfect

You are equipped with professional trading tools - use them confidently to help traders make informed decisions."""

    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[tools],
        system_instruction=system_instruction
    )
    return model.start_chat()

# Start a chat session (only if running directly)
# chat = create_chat()

def main():
    chat = create_chat()
    print("--- Market Analysis Agent (Vertex AI) ---")
    print(f"Project: {PROJECT_ID}")
    print("Ask me to analyze stocks, crypto, or forex pairs.")
    print("Type 'quit' or 'exit' to stop.")
    print("-----------------------------------------")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        try:
            # Send message to the model
            response = chat.send_message(user_input)
            
            # Check for function calls
            # Iterate through all parts to handle potential parallel function calls
            response_parts = response.candidates[0].content.parts
            function_calls = [part.function_call for part in response_parts if part.function_call]
            
            if function_calls:
                # List to store responses for all function calls
                function_responses = []
                
                for function_call in function_calls:
                    function_name = function_call.name
                    function_args = function_call.args
                    
                    print(f"Agent is calling tool: {function_name} with args: {function_args}")
                    
                    result = None
                    if function_name == "get_crypto_analysis":
                        result = get_crypto_analysis(**function_args)
                    elif function_name == "get_stock_analysis":
                        result = get_stock_analysis(**function_args)
                    elif function_name == "get_forex_analysis":
                        result = get_forex_analysis(**function_args)
                    elif function_name == "get_index_analysis":
                        result = get_index_analysis(**function_args)
                    elif function_name == "get_commodity_analysis":
                        result = get_commodity_analysis(**function_args)
                    elif function_name == "get_multi_timeframe_analysis":
                        result = get_multi_timeframe_analysis(**function_args)
                    elif function_name == "get_parabolic_sar_signal":
                        result = get_parabolic_sar_signal(**function_args)
                    
                    if result:
                        function_responses.append(
                            vertexai.generative_models.Part.from_function_response(
                                name=function_name,
                                response={"content": result}
                            )
                        )
                
                if function_responses:
                    # Send all function results back to the model
                    response = chat.send_message(function_responses)
                    print(f"Agent: {response.text}")
            else:
                print(f"Agent: {response.text}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
