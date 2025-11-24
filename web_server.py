import streamlit as st
import vertexai
from vertexai.generative_models import Part
from agent import create_chat, get_crypto_analysis, get_stock_analysis, get_forex_analysis, get_index_analysis, get_commodity_analysis, get_multi_timeframe_analysis

# Page Config
st.set_page_config(
    page_title="Market Analysis Agent",
    page_icon="📈",
    layout="centered"
)

st.title("📈 Market Analysis Agent")
st.caption("Powered by Gemini 2.0 Flash & TradingView")

# Add example prompts
with st.expander("💡 Example Prompts", expanded=False):
    st.markdown("""
    **Multi-Timeframe Analysis:**
    - `Analyze BTCUSDT and give me entry, stop loss, and take profit recommendations`
    - `Analyze US30USD and give me a trade setup`
    - `Give me trading signals for SPX`
    
    **Single Timeframe:**
    - `Analyze TSLA on the 1h timeframe`
    - `What's the outlook for XAUUSD (Gold)?`
    - `Check DJI for me`
    
    **Supported Assets:**
    - Crypto: BTCUSDT, ETHUSDT, etc.
    - Stocks: TSLA, AAPL, etc.
    - Indexes: SPX, DJI, IXIC
    - Forex: EURUSD, GBPUSD, US30USD, etc.
    - Commodities: XAUUSD (Gold)
    """)

# Initialize Chat Session
if "chat" not in st.session_state:
    with st.spinner("Initializing AI agent..."):
        try:
            st.session_state.chat = create_chat()
            st.session_state.messages = []
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.stop()


# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("e.g., 'Analyze US30USD and give me entry, stop loss, and take profit recommendations'"):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            response = st.session_state.chat.send_message(prompt)
            
            # Handle Function Calls
            response_parts = response.candidates[0].content.parts
            function_calls = [part.function_call for part in response_parts if part.function_call]
            
            if function_calls:
                function_responses = []
                status_text = st.status("Analyzing market data...", expanded=True)
                
                for function_call in function_calls:
                    function_name = function_call.name
                    function_args = function_call.args
                    
                    status_text.write(f"Calling tool: `{function_name}`")
                    
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
                            Part.from_function_response(
                                name=function_name,
                                response={"content": result}
                            )
                        )
                
                if function_responses:
                    status_text.update(label="Analysis complete!", state="complete", expanded=False)
                    # Send function results back to model
                    final_response = st.session_state.chat.send_message(function_responses)
                    full_response = final_response.text
            else:
                full_response = response.text
                
            message_placeholder.markdown(full_response)
            
            # Add assistant response to state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
