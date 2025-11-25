import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from server import get_analysis
import sys

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
    """Get technical analysis for a US index."""
    index_exchanges = {
        "SPX": "CBOE",
        "DJI": "DJ",
        "IXIC": "NASDAQ"
    }
    
    if symbol in index_exchanges:
        exchange = index_exchanges[symbol]
    
    return get_analysis(symbol, "america", exchange, interval)

def get_commodity_analysis(symbol: str, exchange: str = "TVC", interval: str = "1d"):
    """Get technical analysis for commodities (energy, metals)."""
    if symbol == "XAUUSD":
        return get_analysis(symbol, "cfd", "FX_IDC", interval)
    
    return get_analysis(symbol, "cfd", exchange, interval)

def run_test():
    # Initialize Vertex AI
    PROJECT_ID = "sp500trading"
    LOCATION = "us-central1"
    
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Define Function Declarations
    get_crypto_analysis_func = FunctionDeclaration.from_func(get_crypto_analysis)
    get_stock_analysis_func = FunctionDeclaration.from_func(get_stock_analysis)
    get_forex_analysis_func = FunctionDeclaration.from_func(get_forex_analysis)
    get_index_analysis_func = FunctionDeclaration.from_func(get_index_analysis)
    get_commodity_analysis_func = FunctionDeclaration.from_func(get_commodity_analysis)

    # Create the tools list
    tools = Tool(
        function_declarations=[
            get_crypto_analysis_func,
            get_stock_analysis_func,
            get_forex_analysis_func,
            get_index_analysis_func,
            get_commodity_analysis_func,
        ]
    )

    # Initialize the model with tools
    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[tools],
    )

    chat = model.start_chat()
    prompt = "Analyze SPX, DJI, and XAUUSD to give me an overview of the markets."
    
    print(f"Sending Prompt: {prompt}")
    
    try:
        response = chat.send_message(prompt)
        
        response_parts = response.candidates[0].content.parts
        function_calls = [part.function_call for part in response_parts if part.function_call]
        
        if function_calls:
            function_responses = []
            for function_call in function_calls:
                function_name = function_call.name
                function_args = function_call.args
                print(f"Calling Tool: {function_name} with {function_args}")
                
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
                
                if result:
                    function_responses.append(
                        vertexai.generative_models.Part.from_function_response(
                            name=function_name,
                            response={"content": result}
                        )
                    )
            
            if function_responses:
                final_response = chat.send_message(function_responses)
                print("\n--- Agent Response ---")
                print(final_response.text)
        else:
            print("\n--- Agent Response ---")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
