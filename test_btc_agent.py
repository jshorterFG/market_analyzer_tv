import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from server import get_analysis
import sys

# Initialize Vertex AI
PROJECT_ID = "sp500trading"
LOCATION = "us-central1"

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

# Define Function Declarations
get_crypto_analysis_func = FunctionDeclaration.from_func(get_crypto_analysis)
get_stock_analysis_func = FunctionDeclaration.from_func(get_stock_analysis)
get_forex_analysis_func = FunctionDeclaration.from_func(get_forex_analysis)

# Create the tools list
tools = Tool(
    function_declarations=[
        get_crypto_analysis_func,
        get_stock_analysis_func,
        get_forex_analysis_func,
    ]
)

# Initialize the model with tools
model = GenerativeModel(
    "gemini-2.0-flash",
    tools=[tools],
)

def run_test():
    chat = model.start_chat()
    prompt = "Analyze BTCUSDT using 1 minute, 5 minute, and 15 minute time frames to determine buy, sell, or hold."
    
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
