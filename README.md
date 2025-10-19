# AI Seller Telegram Bot 🌸

An intelligent Telegram bot that acts as a proactive sales agent, helping customers find and choose perfect bouquets through natural conversation using AI-powered search capabilities.

## Features

### 🤖 AI Sales Agent
- **Proactive personality** - asks clarifying questions to understand customer needs
- **Natural conversation** - speaks like a real salesperson
- **Intelligent recommendations** - provides personalized suggestions based on context
- **Multilingual support** - English, Russian, and Uzbek languages

### 🔍 Smart Search Capabilities
- **Text Search** - Describe what you're looking for in natural language
- **Photo Search** - Upload images to find similar bouquets
- **Smart Filtering** - Automatic price range, occasion, and preference detection
- **Vector Search** - Uses ChromaDB for semantic similarity matching
- **Visual Results** - Automatically displays product photos with search results

### 💳 Payment Integration
- **Click Payment** - Secure payment processing via Click.uz
- **Automatic Pricing** - Dynamic price calculation based on product selection
- **Payment Links** - Direct payment URLs generated for each product
- **Payment Buttons** - One-click payment buttons in Telegram messages
- **Return Handling** - Seamless return to bot after payment completion

### 💬 Telegram Bot Features
- `/start` - Welcome message and introduction
- `/help` - Usage instructions and examples
- `/clear` - Reset conversation context
- **Photo upload handling** - Direct image processing
- **Typing indicators** - Better user experience
- **Error handling** - Graceful error recovery

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │───▶│   AI Agent      │───▶│  Search Tools   │
│   (aiogram)     │    │   (LiteLLM)     │    │  (ChromaDB)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

- **Telegram Bot** - Handles user interactions and message routing
- **AI Agent** - Processes conversations and makes intelligent decisions
- **Search Tools** - Performs vector searches on product database
- **ChromaDB** - Stores and queries product embeddings

## Installation

### Prerequisites
- Python 3.12+
- Telegram Bot Token
- OpenAI API Key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd easify-seller
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv/Scripts/activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Set up your .env file**
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   DEFAULT_LANGUAGE=en
   ```

## Usage

### Running the Bot

```bash
python main.py
```

### Testing the Agent

```bash
python test_bot.py
```

### Bot Commands

- `/start` - Start a conversation with the bot
- `/help` - Get help and usage examples
- `/clear` - Reset your conversation context

### Example Interactions

**Text Search:**
```
User: "I need a romantic bouquet for my girlfriend"
Bot: [Sends photo] "I'd love to help you find the perfect romantic bouquet! Here are some beautiful options that would be perfect for expressing your love..."
```

**Photo Search:**
```
User: [Uploads photo of a bouquet]
Bot: [Sends similar photos] "What a beautiful bouquet! I can see you're drawn to [description]. Here are similar arrangements that capture that same elegance..."
```

**Price Filtering:**
```
User: "Show me bouquets under $50"
Bot: [Sends photos] "I'll find some wonderful bouquets within your budget! Here are options that give you great value..."
```

**Purchase Flow:**
```
User: "I want to buy the red roses bouquet"
Bot: "Excellent choice! 🌹 The 'Red Roses Romance' bouquet is perfect for expressing your love.

Price: 850,000 uzs

Here's your secure payment link:
https://my.click.uz/services/pay/?service_id=30067&merchant_id=22535&amount=850000.00&transaction_param=165884&return_url=https://t.me/easify_seller_bot

[💳 Pay Now] <- Clickable button"
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | Yes |
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `DEFAULT_LANGUAGE` | Default language for responses (en/ru/uz) | No |

### Customization

- **System Prompt**: Edit `agent.py` to modify the AI's personality and behavior
- **Search Functions**: Modify `search_tools.py` to change search behavior
- **Bot Handlers**: Update `bot.py` to add new commands or features

## Development

### Project Structure

```
easify-seller/
├── agent.py              # AI agent with LiteLLM integration
├── bot.py                # Telegram bot implementation
├── search_tools.py       # Search functions for ChromaDB
├── main.py               # Entry point
├── test_bot.py           # Test script
├── .env.example          # Environment template
├── pyproject.toml        # Dependencies
└── README.md             # This file
```

### Dependencies

- `aiogram>=3.22.0` - Telegram Bot API
- `litellm>=1.78.5` - LLM integration
- `chromadb>=1.2.0` - Vector database
- `sentence-transformers>=5.1.1` - Embeddings
- `pillow>=12.0.0` - Image processing
- `python-dotenv>=1.1.1` - Environment management

## Logging

The bot includes comprehensive logging to help with debugging and monitoring:

### Log Files
- Logs are stored in the `logs/` directory
- Daily log files: `ai_seller_bot_YYYYMMDD.log`
- Separate loggers for different components:
  - `main` - Application startup and shutdown
  - `bot` - Telegram bot operations
  - `agent` - AI agent processing
  - `search_tools` - Search operations

### Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages with full stack traces

### Testing Logging
```bash
python test_logging.py
```

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check your `TELEGRAM_BOT_TOKEN` is correct
   - Verify the bot is running without errors
   - Check logs for error messages

2. **Search not working**
   - Ensure ChromaDB is properly set up
   - Check that product embeddings exist
   - Review search logs for errors

3. **API errors**
   - Verify your `OPENAI_API_KEY` is valid
   - Check your API usage limits
   - Check logs for API error details

4. **Photo issues**
   - Check logs for photo processing errors
   - Verify photo URLs are accessible
   - Review photo search logs

### Debug Mode

Enable verbose logging by setting:
```python
litellm.set_verbose = True
```

### Log Analysis
- Check `logs/` directory for detailed error information
- Look for ERROR level messages for critical issues
- DEBUG level provides detailed operation information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the example interactions

---

Made with ❤️ for beautiful flower arrangements
