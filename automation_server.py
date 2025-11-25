"""
Flask app for automated endpoints (email reports, caching, etc.)
This runs alongside the Streamlit app on different routes.
"""

from flask import Flask, jsonify, request
import asyncio
import logging
from email_report import send_report_email, is_market_hours
from datetime import datetime
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/send-hourly-report", methods=["GET", "POST"])
def hourly_report_endpoint():
    """
    Endpoint called by Cloud Scheduler every hour.
    Sends trade report emails if within market hours.
    """
    try:
        logger.info("Hourly report endpoint triggered")
        
        # Send report (includes market hours check)
        result = send_report_email()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in hourly report endpoint: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat()
        }), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "automation-endpoints",
        "market_hours": is_market_hours()
    }), 200

@app.route("/test-email", methods=["GET", "POST"])
def test_email():
    """
    Test endpoint to manually trigger email send (bypasses market hours check).
    Useful for testing email configuration.
    """
    try:
        # Force send regardless of market hours for testing
        from email_report import generate_full_report
        import os
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            return jsonify({"error": "SENDGRID_API_KEY not configured"}), 500
        
        from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'reports@market-analyzer.com')
        recipients = ["jwshorter@gmail.com", "jshorter@fluidgenius.com"]
        
        html_content = generate_full_report()
        now_cst = datetime.now(ZoneInfo("America/Chicago"))
        
        message = Mail(
            from_email=from_email,
            to_emails=recipients,
            subject=f"[TEST] Market Analysis Report - {now_cst.strftime('%b %d, %I:%M %p %Z')}",
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        return jsonify({
            "status": "sent",
            "recipients": recipients,
            "timestamp": now_cst.isoformat(),
            "status_code": response.status_code,
            "note": "This was a test email"
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=8080, debug=True)
