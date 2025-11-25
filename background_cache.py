"""
Background caching endpoint for Google Cloud Run.
This endpoint should be called by Cloud Scheduler every 15 minutes to pre-fetch and cache data.
"""

import asyncio
import logging
from datetime import datetime
from flask import Flask, jsonify
from server import get_analysis_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for background caching endpoint
cache_app = Flask(__name__)

# Supported symbols with their configurations
SUPPORTED_SYMBOLS = {
    "SPX": {"screener": "america", "exchange": "CBOE"},
    "USOIL": {"screener": "cfd", "exchange": "TVC"},
    "XAUUSD": {"screener": "cfd", "exchange": "FX_IDC"},
    "BTCUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "COIN": {"screener": "america", "exchange": "NASDAQ"},
    "USDJPY": {"screener": "forex", "exchange": "FX_IDC"}
}

# Timeframes to cache in background
BACKGROUND_TIMEFRAMES = ["15m", "30m", "1h"]

@cache_app.route("/cache-update", methods=["GET", "POST"])
async def cache_update():
    """
    Endpoint to be called by Cloud Scheduler every 15 minutes.
    Fetches and caches 15m, 30m, and 1h data for all supported symbols.
    """
    start_time = datetime.now()
    logger.info("Starting background cache update...")
    
    results = {
        "timestamp": start_time.isoformat(),
        "symbols_processed": [],
        "errors": []
    }
    
    # Process each symbol
    for symbol, config in SUPPORTED_SYMBOLS.items():
        screener = config["screener"]
        exchange = config["exchange"]
        
        logger.info(f"Caching data for {symbol}...")
        
        # Fetch each timeframe
        for timeframe in BACKGROUND_TIMEFRAMES:
            try:
                # This will fetch and cache the data
                data = await get_analysis_data(symbol, screener, exchange, timeframe)
                
                if data and not data.get('error'):
                    logger.info(f"✓ Cached {symbol} {timeframe}")
                    results["symbols_processed"].append(f"{symbol}_{timeframe}")
                else:
                    error_msg = f"Failed to cache {symbol} {timeframe}: {data.get('error', 'Unknown error')}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                
                # Small delay between requests to avoid hitting rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = f"Error caching {symbol} {timeframe}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Delay between symbols
        await asyncio.sleep(2)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    results["duration_seconds"] = duration
    results["completed_at"] = end_time.isoformat()
    
    logger.info(f"Background cache update completed in {duration:.1f}s")
    logger.info(f"Processed: {len(results['symbols_processed'])} datapoints")
    logger.info(f"Errors: {len(results['errors'])}")
    
    return jsonify(results), 200

@cache_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "background-cache"}), 200

if __name__ == "__main__":
    # For local testing
    import uvicorn
    uvicorn.run(cache_app, host="0.0.0.0", port=8081)
