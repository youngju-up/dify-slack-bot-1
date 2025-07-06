"""
dify-slack-bot - A production-ready Slack bot for Dify API integration.
"""

__version__ = "1.0.0"
__author__ = "Shamsuddin Ahmed"
__email__ = "info@shamspias.com"

from .app import create_app
from .bot import SlackBot
from .dify_client import DifyClient
from .config import Config

__all__ = [
    "create_app",
    "SlackBot",
    "DifyClient",
    "Config"
]