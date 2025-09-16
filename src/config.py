"""
Configuration module for dify-slack-bot.
Loads and validates environment variables.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""

    # Slack Configuration
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

    # Dify Configuration
    DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
    DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://agents.algolyzerlab.com/v1")

    # Application Configuration
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 3000))
    RESPONSE_MODE = os.environ.get("RESPONSE_MODE", "blocking")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Advanced Configuration
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 15)) * 1024 * 1024  # Convert MB to bytes
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 30))
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    CONVERSATION_CACHE_TTL = int(os.environ.get("CONVERSATION_CACHE_TTL", 3600))
    
    # File upload configuration
    SUPPORTED_FILE_TYPES = os.environ.get("SUPPORTED_FILE_TYPES", 
        "image/jpeg,image/jpg,image/png,image/gif,image/webp,"
        "text/plain,text/markdown,application/pdf,text/html,text/csv,application/xml,"
        "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/epub+zip,audio/mpeg,audio/wav,audio/ogg,audio/mp3,"
        "video/mp4,video/avi,video/mov,video/wmv"
    ).split(",")

    @classmethod
    def validate(cls):
        """Validate required configuration values."""
        errors = []

        if not cls.SLACK_BOT_TOKEN:
            errors.append("SLACK_BOT_TOKEN is required")
        if not cls.SLACK_SIGNING_SECRET:
            errors.append("SLACK_SIGNING_SECRET is required")
        if not cls.DIFY_API_KEY:
            errors.append("DIFY_API_KEY is required")

        if cls.RESPONSE_MODE not in ["blocking", "streaming"]:
            errors.append("RESPONSE_MODE must be 'blocking' or 'streaming'")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

    @classmethod
    def get_headers(cls):
        """Get common headers for API requests."""
        return {
            "Authorization": f"Bearer {cls.DIFY_API_KEY}",
            "Content-Type": "application/json"
        }
