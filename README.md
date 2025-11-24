# TradingView MCP Server

This is an MCP server that provides technical analysis data from TradingView using the `tradingview-ta` library.

## Features

- **Get Crypto Analysis**: Get technical analysis for cryptocurrency pairs (e.g., BTCUSDT).
- **Get Stock Analysis**: Get technical analysis for stocks (e.g., TSLA).
- **Get Forex Analysis**: Get technical analysis for forex pairs (e.g., EURUSD).

## Installation

1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Server

You can run the server directly using Python:

```bash
python server.py
```

### Configuration for MCP Clients

To use this server with an MCP client (like Claude Desktop), add the following configuration to your `claude_desktop_config.json` (usually located in `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "python",
      "args": [
        "/Users/josephshorter/Documents/repos/market_analyzer_tv/server.py"
      ]
    }
  }
}
```

Make sure to use the absolute path to your python executable if it's not in the system PATH, or if you are using a virtual environment.

## Tools

### `get_crypto_analysis`
- **symbol**: The crypto symbol (e.g., "BTCUSDT").
- **exchange**: The exchange (default: "BINANCE").
- **interval**: The interval (default: "1d").

### `get_stock_analysis`
- **symbol**: The stock symbol (e.g., "TSLA").
- **exchange**: The exchange (default: "NASDAQ").
- **interval**: The interval (default: "1d").

### `get_forex_analysis`
- **symbol**: The forex symbol (e.g., "EURUSD").
- **exchange**: The exchange (default: "FX_IDC").
- **interval**: The interval (default: "1d").
