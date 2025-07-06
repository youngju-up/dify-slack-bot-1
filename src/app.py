"""
Main application entry point for dify-slack-bot.
"""
from flask import Flask
import sys
import os
import signal
import threading
import time
from .bot import SlackBot
from .config import Config
from .utils import logger, conversation_cache


def create_app():
    """Create and configure the Flask application."""
    # Validate configuration
    Config.validate()

    # Create Flask app
    app = Flask(__name__)
    app.config['DEBUG'] = Config.DEBUG

    # Initialize SlackBot
    bot = SlackBot(app)

    logger.info(f"Application created successfully")
    logger.info(f"Dify API URL: {Config.DIFY_BASE_URL}")
    logger.info(f"Response mode: {Config.RESPONSE_MODE}")

    return app


def cleanup_cache():
    """Periodically clean up expired cache entries."""
    while True:
        try:
            time.sleep(300)  # Run every 5 minutes
            conversation_cache.clear_expired()
            logger.debug("Cache cleanup completed")
        except Exception as e:
            logger.error(f"Error in cache cleanup: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, cleaning up...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start cache cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_cache, daemon=True)
    cleanup_thread.start()

    # Create and run app
    app = create_app()

    logger.info(f"Starting server on port {Config.FLASK_PORT}")

    if Config.DEBUG:
        # Development server
        app.run(
            host='127.0.0.1',
            port=Config.FLASK_PORT,
            debug=True,
            use_reloader=False  # Disable reloader to avoid duplicate initialization
        )
    else:
        # Production server (use gunicorn or similar in production)
        # For now, use Flask's built-in server with threading
        app.run(
            host='127.0.0.1',
            port=Config.FLASK_PORT,
            debug=False,
            threaded=True
        )


if __name__ == "__main__":
    main()
