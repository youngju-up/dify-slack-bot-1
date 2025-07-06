# dify-slack-bot

A production-ready, class-based Slack bot for integrating Slack with any [Dify](https://dify.ai/) API-compatible application. Modular, secure, and easily extensible for all your AI-powered Slack automation needs.

## Features

- Class-based design for maintainability and scalability
- Simple configuration via `.env` file
- Easy to extend for file uploads, conversation history, etc.
- Flask-based webhook for Slack events
- Works with any Dify-compatible API
- Supports both blocking and streaming responses
- Conversation management and history
- Thread support for organized discussions
- Error handling and retry logic
- File upload support (images, documents)

## Quick Start

1. **Clone the repository**
   ```sh
   git clone https://github.com/shamspias/dify-slack-bot.git
   cd dify-slack-bot
   ```

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Copy `.env.example` to `.env` and fill in your secrets:
   ```sh
   cp .env.example .env
   ```

4. **Run the bot**
   ```sh
   python -m src.app
   ```

5. **Set your Slack app's Event Subscription to**
   ```
   https://your-domain.com/slack/events
   ```

## Project Structure

```
src/
    app.py           # Flask app, entry point
    bot.py           # SlackBot class (handles Slack events)
    dify_client.py   # DifyClient class (handles Dify API)
    config.py        # Config loading (env, secrets)
    utils.py         # Utility functions
tests/
    test_bot.py      # Example tests
.env.example         # Template for your environment variables
requirements.txt     # Python dependencies
README.md            # You're reading it!
```

## Environment Variables

See `.env.example` for all required configuration:

- `SLACK_BOT_TOKEN`: Your Slack bot user OAuth token (starts with xoxb-)
- `SLACK_SIGNING_SECRET`: Your Slack app's signing secret
- `DIFY_API_KEY`: Your Dify application API key
- `DIFY_BASE_URL`: Dify API base URL (default: https://dify.com/v1)
- `FLASK_PORT`: Port for the Flask server (default: 3000)
- `RESPONSE_MODE`: Response mode for Dify API (blocking/streaming, default: blocking)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR, default: INFO)

## Slack App Configuration

1. Create a new Slack app at https://api.slack.com/apps
2. Add the following OAuth scopes:
   - `app_mentions:read` - Read messages that mention your app
   - `chat:write` - Send messages
   - `files:read` - Read files shared in channels
   - `channels:history` - View messages in public channels
   - `groups:history` - View messages in private channels
   - `im:history` - View direct messages
   - `mpim:history` - View group direct messages
3. Enable Event Subscriptions and add:
   - `app_mention` - Listen for @mentions
   - `message.channels` - Listen for channel messages (optional)
   - `message.groups` - Listen for private channel messages (optional)
   - `message.im` - Listen for direct messages (optional)
4. Install the app to your workspace

## Usage

### Basic Chat
Simply mention the bot in any channel:
```
@dify-bot What are the specs of iPhone 13 Pro Max?
```

### Thread Conversations
The bot maintains conversation context within threads:
```
@dify-bot Tell me about the latest iPhone
// Bot responds...
@dify-bot How does it compare to the previous model?
// Bot continues the conversation with context
```

### File Uploads
Share images or documents with the bot:
```
@dify-bot [upload an image] What's in this image?
```

## Extend

- Add more event handlers in `bot.py`
- Add more Dify API endpoints in `dify_client.py`
- Implement custom conversation storage in `utils.py`
- Add logging, monitoring, and error reporting
- Implement rate limiting and request queuing
- Add support for Slack interactive components

## API Endpoints

The bot exposes the following endpoints:

- `POST /slack/events` - Slack event webhook
- `GET /health` - Health check endpoint

## Error Handling

The bot includes comprehensive error handling:
- Validates Slack request signatures
- Handles Dify API errors gracefully
- Provides user-friendly error messages
- Logs errors for debugging

## Security

- All Slack requests are verified using signing secrets
- API keys are stored securely in environment variables
- No sensitive data is logged
- HTTPS recommended for production deployment

## License

MIT