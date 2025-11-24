import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from server import get_analysis

# Initialize Vertex AI
PROJECT_ID = "sp500trading"
LOCATION = "us-central1" # You might want to ask the user for location or default to one

vertexai.init(project=PROJECT_ID, location=LOCATION)

# Define Tool Functions
def get_crypto_analysis(symbol: str, exchange: str = "BINANCE", interval: str = "1d"):
    """Get technical analysis for a crypto pair."""
    return get_analysis(symbol, "crypto", exchange, interval)

def get_stock_analysis(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """Get technical analysis for a stock."""
    return get_analysis(symbol, "america", exchange, interval)

def get_forex_analysis(symbol: str, exchange: str = "FX_IDC", interval: str = "1d"):
    """Get technical analysis for a forex pair."""
    return get_analysis(symbol, "forex", exchange, interval)

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
    
    return get_analysis(symbol, "america", exchange, interval)

def get_commodity_analysis(symbol: str, exchange: str = "TVC", interval: str = "1d"):
    """Get technical analysis for commodities (energy, metals).
    
    Common symbols:
    - XAUUSD (Gold) on FX_IDC (use cfd screener)
    - For other commodities, specify the exchange
    """
    # Gold uses cfd screener
    if symbol == "XAUUSD":
        return get_analysis(symbol, "cfd", "FX_IDC", interval)
    
    return get_analysis(symbol, "cfd", exchange, interval)

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
            
            analysis_text = get_analysis(symbol, screener, exchange, tf)
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

# Define Function Declarations
get_crypto_analysis_func = FunctionDeclaration.from_func(get_crypto_analysis)
get_stock_analysis_func = FunctionDeclaration.from_func(get_stock_analysis)
get_forex_analysis_func = FunctionDeclaration.from_func(get_forex_analysis)
get_index_analysis_func = FunctionDeclaration.from_func(get_index_analysis)
get_commodity_analysis_func = FunctionDeclaration.from_func(get_commodity_analysis)
get_multi_timeframe_analysis_func = FunctionDeclaration.from_func(get_multi_timeframe_analysis)

# Create the tools list
tools = Tool(
    function_declarations=[
        get_crypto_analysis_func,
        get_stock_analysis_func,
        get_forex_analysis_func,
        get_index_analysis_func,
        get_commodity_analysis_func,
        get_multi_timeframe_analysis_func,
    ]
)

def create_chat():
    # Initialize the model with tools and system instruction
    system_instruction = """You are a professional market analysis assistant. Your role is to:

1. Use the available tools to fetch technical analysis data when users ask for market analysis
2. Provide clear, actionable trading recommendations including entry points, stop loss, and take profit levels
3. When asked for entry/stop/profit recommendations, ALWAYS use get_multi_timeframe_analysis tool
4. Synthesize the technical data into specific price levels and trading advice
5. Be confident in your recommendations based on the technical indicators provided

When a user asks for trading recommendations:
- Call the appropriate analysis tool (multi-timeframe for comprehensive analysis)
- Analyze the data from all timeframes
- Provide specific entry price, stop loss level, and take profit target(s)
- Explain the reasoning based on support/resistance levels and trend indicators
- Calculate and mention the risk/reward ratio

You are equipped with professional trading tools - use them confidently to help traders make informed decisions."""

    model = GenerativeModel(
        "gemini-2.0-flash",
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
