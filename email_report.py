"""
Hourly trade report email system using SendGrid.
Sends analysis for all 6 symbols during market hours (Sun 6PM - Fri 2PM CST).
"""

import os
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from agent import get_parabolic_sar_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Market configuration
SUPPORTED_SYMBOLS = ["SPX", "USOIL", "XAUUSD", "BTCUSDT", "COIN", "USDJPY"]
RECIPIENT_EMAILS = ["jwshorter@gmail.com", "jshorter@fluidgenius.com"]
CST = ZoneInfo("America/Chicago")

def is_market_hours() -> bool:
    """
    Check if current time is within market hours:
    Sunday 6:00 PM CST through Friday 2:00 PM CST
    
    Returns:
        bool: True if within market hours, False otherwise
    """
    now_cst = datetime.now(CST)
    day_of_week = now_cst.weekday()  # 0=Monday, 6=Sunday
    hour = now_cst.hour
    
    # Sunday after 6 PM (18:00)
    if day_of_week == 6 and hour >= 18:
        return True
    
    # Monday through Thursday (all day)
    if day_of_week in [0, 1, 2, 3]:
        return True
    
    # Friday before 2 PM (14:00)
    if day_of_week == 4 and hour < 14:
        return True
    
    return False

def generate_symbol_html(symbol: str) -> str:
    """
    Generate HTML section for a single symbol's analysis.
    
    Args:
        symbol: Trading symbol to analyze
        
    Returns:
        HTML string with analysis
    """
    try:
        # Get analysis from the agent
        analysis = get_parabolic_sar_signal(symbol, asset_type="", exchange="")
        
        # Determine if bullish or bearish based on analysis content
        if "BUY" in analysis.upper() and "MARKET BUY" in analysis.upper():
            signal_color = "#28a745"  # Green
            signal_text = "🟢 BUY SIGNAL"
        elif "SELL" in analysis.upper() and "MARKET SELL" in analysis.upper():
            signal_color = "#dc3545"  # Red
            signal_text = "🔴 SELL SIGNAL"
        else:
            signal_color = "#6c757d"  # Gray
            signal_text = "⚪ MIXED/NEUTRAL"
        
        html = f"""
        <div style="margin-bottom: 30px; border: 1px solid #ddd; border-radius: 8px; padding: 20px; background-color: #f8f9fa;">
            <h2 style="color: #333; margin-top: 0;">
                {symbol}
                <span style="color: {signal_color}; font-size: 18px; margin-left: 10px;">{signal_text}</span>
            </h2>
            <pre style="background-color: #fff; padding: 15px; border-radius: 4px; border: 1px solid #e0e0e0; overflow-x: auto; font-size: 12px; line-height: 1.5;">
{analysis}
            </pre>
        </div>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Error generating analysis for {symbol}: {e}")
        return f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
            <h3 style="color: #856404; margin-top: 0;">{symbol}</h3>
            <p style="color: #856404;">⚠️ Error generating analysis: {str(e)}</p>
        </div>
        """

def generate_full_report() -> str:
    """
    Generate complete HTML email report for all symbols.
    
    Returns:
        HTML string for email body
    """
    now_cst = datetime.now(CST)
    timestamp = now_cst.strftime("%A, %B %d, %Y at %I:%M %p %Z")
    
    # Generate analysis for all symbols
    symbol_sections = ""
    for symbol in SUPPORTED_SYMBOLS:
        logger.info(f"Generating analysis for {symbol}...")
        symbol_sections += generate_symbol_html(symbol)
    
    # Complete HTML email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
            .footer {{ margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin: 0; color: white;">📈 Hourly Market Analysis Report</h1>
            <p style="margin: 10px 0 0 0; color: #e0e0e0;">{timestamp}</p>
        </div>
        
        {symbol_sections}
        
        <div class="footer">
            <strong>⚠️ DISCLAIMER:</strong> This analysis and all recommendations are provided for ENTERTAINMENT PURPOSES ONLY.
            This is NOT financial advice. Trading involves substantial risk of loss.
            Always conduct your own research and consult with a licensed financial advisor before making any trading decisions.
        </div>
    </body>
    </html>
    """
    
    return html

def send_report_email() -> Dict:
    """
    Send hourly report email to configured recipients.
    
    Returns:
        Dict with status information
    """
    try:
        # Check if we're in market hours
        if not is_market_hours():
            now_cst = datetime.now(CST)
            return {
                "status": "skipped",
                "reason": "Outside market hours",
                "timestamp": now_cst.isoformat()
            }
        
        # Get SendGrid API key from environment
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            raise ValueError("SENDGRID_API_KEY environment variable not set")
        
        from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'reports@market-analyzer.com')
        
        # Generate report
        logger.info("Generating report for all symbols...")
        html_content = generate_full_report()
        
        # Create email
        now_cst = datetime.now(CST)
        subject = f"Market Analysis Report - {now_cst.strftime('%b %d, %I:%M %p %Z')}"
        
        message = Mail(
            from_email=from_email,
            to_emails=RECIPIENT_EMAILS,
            subject=subject,
            html_content=html_content
        )
        
        # Send via SendGrid
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        logger.info(f"Email sent successfully. Status code: {response.status_code}")
        
        return {
            "status": "sent",
            "recipients": RECIPIENT_EMAILS,
            "timestamp": now_cst.isoformat(),
            "status_code": response.status_code
        }
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(CST).isoformat()
        }

if __name__ == "__main__":
    # For local testing
    print("Testing market hours logic...")
    print(f"Is market hours: {is_market_hours()}")
    print(f"Current time CST: {datetime.now(CST)}")
    
    print("\nGenerating sample report...")
    result = send_report_email()
    print(f"Result: {result}")
