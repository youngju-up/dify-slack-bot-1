"""
Utility functions for dify-slack-bot.
Includes logging setup, conversation caching, and helper functions.
"""
import logging
import colorlog
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import json
import re
from .config import Config


def setup_logging():
    """Set up colored logging with appropriate level."""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(asctime)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    return logger


class ConversationCache:
    """Simple in-memory conversation cache with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _key(self, user_id: str, channel_id: str, thread_ts: Optional[str] = None) -> str:
        """Generate cache key from user, channel, and thread."""
        if thread_ts:
            return f"{user_id}:{channel_id}:{thread_ts}"
        return f"{user_id}:{channel_id}"

    def get(self, user_id: str, channel_id: str, thread_ts: Optional[str] = None) -> Optional[str]:
        """Get conversation ID from cache."""
        key = self._key(user_id, channel_id, thread_ts)
        entry = self._cache.get(key)

        if entry:
            # Check if entry has expired
            if time.time() - entry['timestamp'] > self._ttl:
                del self._cache[key]
                return None
            return entry['conversation_id']

        return None

    def set(self, user_id: str, channel_id: str, conversation_id: str, thread_ts: Optional[str] = None):
        """Set conversation ID in cache."""
        key = self._key(user_id, channel_id, thread_ts)
        self._cache[key] = {
            'conversation_id': conversation_id,
            'timestamp': time.time()
        }

    def clear_expired(self):
        """Clear expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry['timestamp'] > self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]


def extract_text_from_event(event: Dict[str, Any]) -> str:
    """Extract clean text from Slack event, removing bot mentions."""
    text = event.get('text', '')

    # Remove bot user mentions (e.g., <@U123456>)
    text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()

    # Clean up extra whitespace
    text = ' '.join(text.split())

    return text


def format_dify_response(response: Dict[str, Any]) -> str:
    """Format Dify API response for Slack display."""
    answer = response.get('answer', 'No response received.')

    # Add citation information if available
    retriever_resources = response.get('metadata', {}).get('retriever_resources', [])
    if retriever_resources:
        answer += "\n\n*Sources:*"
        for resource in retriever_resources[:3]:  # Limit to 3 sources
            dataset_name = resource.get('dataset_name', 'Unknown')
            document_name = resource.get('document_name', 'Unknown')
            score = resource.get('score', 0)
            answer += f"\n• {document_name} (from {dataset_name}) - Score: {score:.2f}"

    return answer


def parse_streaming_response(line: str) -> Optional[Dict[str, Any]]:
    """Parse a line from streaming response."""
    if not line.startswith('data: '):
        return None

    try:
        data = json.loads(line[6:])  # Remove 'data: ' prefix
        return data
    except json.JSONDecodeError:
        return None


def build_error_message(error: Exception) -> str:
    """Build user-friendly error message."""
    error_messages = {
        'connection': "I'm having trouble connecting to the AI service. Please try again later.",
        'timeout': "The request took too long to process. Please try again with a simpler question.",
        'rate_limit': "I'm receiving too many requests right now. Please wait a moment and try again.",
        'invalid_input': "I couldn't understand that input. Please try rephrasing your question.",
        'server_error': "Something went wrong on my end. Please try again later."
    }

    error_str = str(error).lower()

    if 'connection' in error_str or 'network' in error_str:
        return error_messages['connection']
    elif 'timeout' in error_str:
        return error_messages['timeout']
    elif 'rate' in error_str and 'limit' in error_str:
        return error_messages['rate_limit']
    elif '400' in error_str or 'bad request' in error_str:
        return error_messages['invalid_input']
    else:
        return error_messages['server_error']


def truncate_text(text: str, max_length: int = 3000) -> str:
    """Truncate text to avoid Slack message limits."""
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


def get_file_info_from_event(event: Dict[str, Any]) -> list:
    """Extract file information from Slack event."""
    files = []

    # Check for files in the event
    if 'files' in event:
        for file in event['files']:
            file_info = {
                'name': file.get('name', 'unknown'),
                'mimetype': file.get('mimetype', 'unknown'),
                'url_private': file.get('url_private'),
                'size': file.get('size', 0)
            }
            files.append(file_info)

    return files


# Initialize logger
logger = setup_logging()

# Initialize conversation cache
conversation_cache = ConversationCache(Config.CONVERSATION_CACHE_TTL)
