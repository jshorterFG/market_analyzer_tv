import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from tradingview_ta import TA_Handler, Interval, Exchange

# Initialize Server
app = Server("tradingview-analyzer")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_crypto_analysis",
            description="Get technical analysis for a crypto pair",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The crypto symbol (e.g., 'BTCUSDT')"},
                    "exchange": {"type": "string", "default": "BINANCE", "description": "The exchange"},
                    "interval": {"type": "string", "default": "1d", "description": "The interval (1m, 5m, 15m, 1h, 4h, 1d, 1W, 1M)"}
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_stock_analysis",
            description="Get technical analysis for a stock",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The stock symbol (e.g., 'TSLA')"},
                    "exchange": {"type": "string", "default": "NASDAQ", "description": "The exchange"},
                    "interval": {"type": "string", "default": "1d", "description": "The interval (1m, 5m, 15m, 1h, 4h, 1d, 1W, 1M)"}
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_forex_analysis",
            description="Get technical analysis for a forex pair",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The forex symbol (e.g., 'EURUSD')"},
                    "exchange": {"type": "string", "default": "FX_IDC", "description": "The exchange"},
                    "interval": {"type": "string", "default": "1d", "description": "The interval (1m, 5m, 15m, 1h, 4h, 1d, 1W, 1M)"}
                },
                "required": ["symbol"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    if name == "get_crypto_analysis":
        return [TextContent(type="text", text=get_analysis(arguments["symbol"], "crypto", arguments.get("exchange", "BINANCE"), arguments.get("interval", "1d")))]
    elif name == "get_stock_analysis":
        return [TextContent(type="text", text=get_analysis(arguments["symbol"], "america", arguments.get("exchange", "NASDAQ"), arguments.get("interval", "1d")))]
    elif name == "get_forex_analysis":
        return [TextContent(type="text", text=get_analysis(arguments["symbol"], "forex", arguments.get("exchange", "FX_IDC"), arguments.get("interval", "1d")))]
    else:
        raise ValueError(f"Unknown tool: {name}")

def get_analysis(symbol: str, screener: str, exchange: str, interval: str) -> str:
    try:
        # Map interval string to tradingview_ta Interval constant
        interval_map = {
            "1m": Interval.INTERVAL_1_MINUTE,
            "5m": Interval.INTERVAL_5_MINUTES,
            "15m": Interval.INTERVAL_15_MINUTES,
            "1h": Interval.INTERVAL_1_HOUR,
            "4h": Interval.INTERVAL_4_HOURS,
            "1d": Interval.INTERVAL_1_DAY,
            "1W": Interval.INTERVAL_1_WEEK,
            "1M": Interval.INTERVAL_1_MONTH,
        }
        
        tv_interval = interval_map.get(interval, Interval.INTERVAL_1_DAY)

        handler = TA_Handler(
            symbol=symbol,
            screener=screener,
            exchange=exchange,
            interval=tv_interval
        )
        
        analysis = handler.get_analysis()
        
        # Get candle data
        open_price = analysis.indicators.get('open', 0)
        close_price = analysis.indicators.get('close', 0)
        high_price = analysis.indicators.get('high', 0)
        low_price = analysis.indicators.get('low', 0)
        
        # Format the output
        output = f"Analysis for {symbol} on {exchange} ({interval}):\n"
        output += f"Recommendation: {analysis.summary['RECOMMENDATION']}\n"
        output += f"Buy: {analysis.summary['BUY']}, Sell: {analysis.summary['SELL']}, Neutral: {analysis.summary['NEUTRAL']}\n\n"
        
        # Add candle direction
        output += "Candle Analysis:\n"
        if close_price > open_price:
            candle_body = close_price - open_price
            output += f"🟢 Bullish Candle (Close > Open)\n"
        elif close_price < open_price:
            candle_body = open_price - close_price
            output += f"🔴 Bearish Candle (Close < Open)\n"
        else:
            candle_body = 0
            output += f"⚪ Doji Candle (Close = Open)\n"
        
        output += f"Open: {open_price:.2f}, Close: {close_price:.2f}, High: {high_price:.2f}, Low: {low_price:.2f}\n"
        if candle_body > 0:
            candle_range = high_price - low_price
            body_percentage = (candle_body / candle_range * 100) if candle_range > 0 else 0
            output += f"Body size: {candle_body:.2f} ({body_percentage:.1f}% of range)\n"
        output += "\n"
        
        output += "Oscillators:\n"
        output += f"Recommendation: {analysis.oscillators['RECOMMENDATION']}\n"
        if 'RSI' in analysis.indicators:
            rsi = analysis.indicators['RSI']
            output += f"RSI: {rsi:.2f}"
            if rsi > 70:
                output += " (Overbought - Bearish)\n"
            elif rsi < 30:
                output += " (Oversold - Bullish)\n"
            else:
                output += " (Neutral)\n"
        if 'MACD.macd' in analysis.indicators:
            output += f"MACD: {analysis.indicators['MACD.macd']:.2f}\n"
            
        output += "\nMoving Averages:\n"
        output += f"Recommendation: {analysis.moving_averages['RECOMMENDATION']}\n"
        if 'EMA20' in analysis.indicators:
            output += f"EMA20: {analysis.indicators['EMA20']:.2f}\n"
        if 'SMA50' in analysis.indicators:
            output += f"SMA50: {analysis.indicators['SMA50']:.2f}\n"
        if 'SMA200' in analysis.indicators:
            output += f"SMA200: {analysis.indicators['SMA200']:.2f}\n"
        
        # Add Parabolic SAR
        output += "\nTrend Indicators:\n"
        if 'P.SAR' in analysis.indicators:
            psar = analysis.indicators['P.SAR']
            close = analysis.indicators.get('close', 0)
            output += f"Parabolic SAR: {psar:.2f}"
            if close > psar:
                output += " (Price above SAR - Bullish trend)\n"
            else:
                output += " (Price below SAR - Bearish trend)\n"
        
        # Add ADX (Average Directional Index)
        if 'ADX' in analysis.indicators:
            adx = analysis.indicators['ADX']
            output += f"ADX: {adx:.2f}"
            if adx > 25:
                output += " (Strong trend)\n"
            elif adx > 20:
                output += " (Developing trend)\n"
            else:
                output += " (Weak/No trend)\n"
        
        # Add Awesome Oscillator (instead of Force Index)
        if 'AO' in analysis.indicators:
            ao = analysis.indicators['AO']
            ao_prev = analysis.indicators.get('AO[1]', 0)
            output += f"Awesome Oscillator: {ao:.2f}"
            if ao > 0 and ao > ao_prev:
                output += " (Bullish momentum increasing)\n"
            elif ao > 0:
                output += " (Bullish momentum)\n"
            elif ao < 0 and ao < ao_prev:
                output += " (Bearish momentum increasing)\n"
            else:
                output += " (Bearish momentum)\n"
        
        # Overall trend direction
        output += "\n📊 TREND DIRECTION:\n"
        bullish_signals = 0
        bearish_signals = 0
        
        # Count signals
        if analysis.summary['RECOMMENDATION'] in ['BUY', 'STRONG_BUY']:
            bullish_signals += 2
        elif analysis.summary['RECOMMENDATION'] in ['SELL', 'STRONG_SELL']:
            bearish_signals += 2
        
        if 'RSI' in analysis.indicators:
            if analysis.indicators['RSI'] < 30:
                bullish_signals += 1
            elif analysis.indicators['RSI'] > 70:
                bearish_signals += 1
        
        if 'P.SAR' in analysis.indicators and 'close' in analysis.indicators:
            if analysis.indicators['close'] > analysis.indicators['P.SAR']:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        if 'AO' in analysis.indicators:
            if analysis.indicators['AO'] > 0:
                bullish_signals += 1
            elif analysis.indicators['AO'] < 0:
                bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            output += f"🟢 BULLISH ({bullish_signals} bullish vs {bearish_signals} bearish signals)\n"
        elif bearish_signals > bullish_signals:
            output += f"🔴 BEARISH ({bearish_signals} bearish vs {bullish_signals} bullish signals)\n"
        else:
            output += f"⚪ NEUTRAL ({bullish_signals} bullish vs {bearish_signals} bearish signals)\n"
            
        return output

    except Exception as e:
        return f"Error fetching analysis for {symbol}: {str(e)}"

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
