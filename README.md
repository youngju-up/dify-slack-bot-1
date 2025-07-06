# dify-slack-bot

A production-ready, class-based Slack bot for integrating Slack with any [Dify](https://dify.ai/) API-compatible application. Modular, secure, and easily extensible for all your AI-powered Slack automation needs.

## Features

- Class-based design for maintainability and scalability
- Simple configuration via `.env` file
- Easy to extend for file uploads, conversation history, etc.
- Flask-based webhook for Slack events
- Works with any Dify-compatible API

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

5. **Set your Slack app’s Event Subscription to**

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
README.md            # You’re reading it!
```

## Environment Variables

See `.env.example` for all required configuration.

## Extend

* Add more event handlers in `bot.py`
* Add more Dify API endpoints in `dify_client.py`
* Add logging, error reporting, etc.
