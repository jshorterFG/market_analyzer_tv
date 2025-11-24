import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from server import get_analysis
from typing import Dict, List
import json

# Initialize Vertex AI
PROJECT_ID = "sp500trading"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

def get_multi_timeframe_analysis(symbol: str, asset_type: str = "crypto", exchange: str = "BINANCE") -> str:
    """
    Get technical analysis across multiple timeframes (1m, 5m, 15m, 30m, 1h) for trading decisions.
    
    Args:
        symbol: The trading symbol (e.g., 'BTCUSDT', 'TSLA', 'SPX')
        asset_type: Type of asset - 'crypto', 'stock', 'forex', 'index', or 'commodity'
        exchange: The exchange (default varies by asset_type)
    """
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
    
    timeframes = ["1m", "5m", "15m", "30m", "1h"]
    results = {}
    
    for tf in timeframes:
        try:
            analysis_text = get_analysis(symbol, screener, exchange, tf)
            results[tf] = analysis_text
        except Exception as e:
            results[tf] = f"Error: {str(e)}"
    
    # Format output
    output = f"Multi-Timeframe Analysis for {symbol} on {exchange}\n"
    output += "=" * 60 + "\n\n"
    
    for tf, result in results.items():
        output += f"--- {tf.upper()} Timeframe ---\n"
        output += result + "\n\n"
    
    return output

def generate_trade_recommendation(symbol: str, asset_type: str = "crypto", exchange: str = "BINANCE") -> str:
    """
    Generate entry, stop loss, and take profit recommendations based on multi-timeframe analysis.
    This function should be called by the LLM after getting multi-timeframe data.
    
    Args:
        symbol: The trading symbol
        asset_type: Type of asset
        exchange: The exchange
    """
    analysis = get_multi_timeframe_analysis(symbol, asset_type, exchange)
    
    prompt = f"""Based on the following multi-timeframe technical analysis, provide:
1. Entry recommendation (BUY/SELL/HOLD)
2. Suggested entry price level
3. Stop loss level
4. Take profit level(s)
5. Risk/reward ratio
6. Confidence level (1-10)

Analysis Data:
{analysis}

Provide a structured recommendation."""
    
    return analysis

# Define Function Declarations
get_multi_timeframe_analysis_func = FunctionDeclaration.from_func(get_multi_timeframe_analysis)
generate_trade_recommendation_func = FunctionDeclaration.from_func(generate_trade_recommendation)

# Create the tools list
tools = Tool(
    function_declarations=[
        get_multi_timeframe_analysis_func,
        generate_trade_recommendation_func,
    ]
)

# Initialize the model with tools
model = GenerativeModel(
    "gemini-2.0-flash",
    tools=[tools],
)

def test_trade_recommendation():
    chat = model.start_chat()
    prompt = "Analyze BTCUSDT and give me entry, stop loss, and take profit recommendations based on 1m, 5m, 15m, 30m, and 1h timeframes."
    
    print(f"Sending Prompt: {prompt}\n")
    
    try:
        response = chat.send_message(prompt)
        
        # Handle multiple rounds of function calling
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            response_parts = response.candidates[0].content.parts
            function_calls = [part.function_call for part in response_parts if part.function_call]
            
            # Check if there's text in the response
            text_parts = [part.text for part in response_parts if hasattr(part, 'text') and part.text]
            
            if not function_calls:
                # No more function calls, print final response
                if text_parts:
                    print("\n" + "=" * 60)
                    print("AGENT RECOMMENDATION")
                    print("=" * 60)
                    for text in text_parts:
                        print(text)
                break
            
            # Execute function calls
            function_responses = []
            for function_call in function_calls:
                function_name = function_call.name
                function_args = function_call.args
                print(f"Calling Tool: {function_name} with {function_args}\n")
                
                result = None
                if function_name == "get_multi_timeframe_analysis":
                    result = get_multi_timeframe_analysis(**function_args)
                elif function_name == "generate_trade_recommendation":
                    result = generate_trade_recommendation(**function_args)
                
                if result:
                    print("--- Tool Result (truncated) ---")
                    print(result[:300] + "..." if len(result) > 300 else result)
                    print()
                    
                    function_responses.append(
                        vertexai.generative_models.Part.from_function_response(
                            name=function_name,
                            response={"content": result}
                        )
                    )
            
            if function_responses:
                response = chat.send_message(function_responses)
                iteration += 1
            else:
                break
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()




if __name__ == "__main__":
    test_trade_recommendation()
