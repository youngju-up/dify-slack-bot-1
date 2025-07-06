"""
Slack bot implementation for handling events and interactions.
"""
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
import requests
from typing import Dict, Any, Optional
from .config import Config
from .dify_client import DifyClient
from .utils import (
    logger, conversation_cache, extract_text_from_event,
    format_dify_response, build_error_message, truncate_text,
    get_file_info_from_event
)


class SlackBot:
    """Main Slack bot class."""

    def __init__(self, flask_app: Flask):
        """Initialize the Slack bot with Flask app."""
        self.app = App(
            token=Config.SLACK_BOT_TOKEN,
            signing_secret=Config.SLACK_SIGNING_SECRET
        )
        self.handler = SlackRequestHandler(self.app)
        self.dify = DifyClient()
        self.flask_app = flask_app

        # Get bot user ID for mention detection
        self.bot_user_id = self._get_bot_user_id()

        # Set up event handlers
        self.setup_events()

        # Set up Flask routes
        self.setup_routes(flask_app)

        logger.info("SlackBot initialized successfully")

    def _get_bot_user_id(self) -> str:
        """Get the bot's user ID."""
        try:
            response = self.app.client.auth_test()
            return response.get('user_id', '')
        except Exception as e:
            logger.error(f"Error getting bot user ID: {e}")
            return ''

    def setup_events(self):
        """Set up Slack event handlers."""

        @self.app.event("app_mention")
        def handle_mention(event, say, client):
            """Handle @mentions of the bot."""
            logger.info(f"Received app mention: {event}")
            self._process_message(event, say, client)

        @self.app.event("message")
        def handle_message(event, say, client):
            """Handle direct messages and messages in channels where bot is present."""
            # Skip if this is a bot message or an edited message
            if event.get('bot_id') or event.get('edited'):
                return

            # Only process if it's a DM or the bot is mentioned
            channel_type = event.get('channel_type')
            if channel_type == 'im' or self._is_bot_mentioned(event):
                logger.info(f"Received message: {event}")
                self._process_message(event, say, client)

        @self.app.event("file_shared")
        def handle_file_shared(event, say, client):
            """Handle file sharing events."""
            logger.info(f"File shared: {event}")
            # File handling is done in _process_message when files are present

    def _is_bot_mentioned(self, event: Dict[str, Any]) -> bool:
        """Check if the bot is mentioned in the message."""
        text = event.get('text', '')
        return f'<@{self.bot_user_id}>' in text

    def _process_message(self, event: Dict[str, Any], say, client):
        """Process incoming messages and send to Dify."""
        try:
            user_id = event.get('user')
            channel = event.get('channel')
            thread_ts = event.get('thread_ts') or event.get('ts')
            text = extract_text_from_event(event)

            if not text and not event.get('files'):
                say("I need some text or files to work with!", thread_ts=thread_ts)
                return

            # Send typing indicator
            client.chat_postEphemeral(
                channel=channel,
                user=user_id,
                text="Thinking... 🤔"
            )

            # Get or create conversation ID
            conversation_id = conversation_cache.get(user_id, channel, thread_ts)

            # Handle file uploads if present
            files = []
            file_infos = get_file_info_from_event(event)

            for file_info in file_infos:
                try:
                    file_data = self._download_slack_file(file_info['url_private'])
                    if file_data:
                        # Upload to Dify
                        upload_response = self.dify.upload_file(
                            file_data,
                            file_info['name'],
                            user_id
                        )

                        # Add to files list for message
                        files.append({
                            "type": self._get_file_type(file_info['mimetype']),
                            "transfer_method": "local_file",
                            "upload_file_id": upload_response['id']
                        })
                except Exception as e:
                    logger.error(f"Error processing file: {e}")

            # Send message to Dify
            response = self.dify.send_message(
                user_id=user_id,
                message=text,
                conversation_id=conversation_id,
                files=files if files else None
            )

            # Cache conversation ID
            new_conversation_id = response.get('conversation_id')
            if new_conversation_id:
                conversation_cache.set(user_id, channel, new_conversation_id, thread_ts)

            # Format and send response
            formatted_response = format_dify_response(response)
            formatted_response = truncate_text(formatted_response)

            # Send response in thread
            say(formatted_response, thread_ts=thread_ts)

            # Add suggested questions if available
            if response.get('message_id'):
                suggestions = self.dify.get_suggested_questions(
                    response['message_id'],
                    user_id
                )

                if suggestions:
                    suggestions_text = "*Suggested follow-up questions:*\n"
                    for i, suggestion in enumerate(suggestions[:3], 1):
                        suggestions_text += f"{i}. {suggestion}\n"

                    say(suggestions_text, thread_ts=thread_ts)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_message = build_error_message(e)
            say(error_message, thread_ts=thread_ts)

    def _download_slack_file(self, url: str) -> Optional[bytes]:
        """Download a file from Slack."""
        try:
            headers = {"Authorization": f"Bearer {Config.SLACK_BOT_TOKEN}"}
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download file: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    def _get_file_type(self, mimetype: str) -> str:
        """Map MIME type to Dify file type."""
        if mimetype.startswith('image/'):
            return 'image'
        elif mimetype in ['text/plain', 'text/markdown', 'application/pdf',
                          'text/html', 'application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/csv', 'application/xml', 'application/epub+zip']:
            return 'document'
        elif mimetype.startswith('audio/'):
            return 'audio'
        elif mimetype.startswith('video/'):
            return 'video'
        else:
            return 'custom'

    def setup_routes(self, flask_app: Flask):
        """Set up Flask routes."""

        @flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            """Handle Slack events."""
            # URL verification
            if request.json and request.json.get("type") == "url_verification":
                return jsonify({"challenge": request.json.get("challenge")})

            # Handle events
            return self.handler.handle(request)

        @flask_app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            try:
                # Check Slack connection
                slack_test = self.app.client.auth_test()
                slack_ok = slack_test.get('ok', False)

                # Check Dify connection
                dify_ok = False
                try:
                    app_info = self.dify.get_app_info()
                    dify_ok = bool(app_info.get('name'))
                except:
                    pass

                status = "healthy" if (slack_ok and dify_ok) else "unhealthy"

                return jsonify({
                    "status": status,
                    "services": {
                        "slack": "connected" if slack_ok else "disconnected",
                        "dify": "connected" if dify_ok else "disconnected"
                    },
                    "cache_size": len(conversation_cache._cache)
                })

            except Exception as e:
                logger.error(f"Health check error: {e}")
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e)
                }), 500

        @flask_app.route("/", methods=["GET"])
        def index():
            """Root endpoint."""
            return jsonify({
                "name": "dify-slack-bot",
                "version": "1.0.0",
                "status": "running"
            })

    def add_reaction(self, channel: str, timestamp: str, reaction: str):
        """Add a reaction to a message."""
        try:
            self.app.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")

    def update_message(self, channel: str, timestamp: str, text: str):
        """Update an existing message."""
        try:
            self.app.client.chat_update(
                channel=channel,
                ts=timestamp,
                text=text
            )
        except Exception as e:
            logger.error(f"Error updating message: {e}")
