import asyncio
import os
import sys
from dotenv import load_dotenv
from bot import TelegramBot
from logger_config import setup_logger

def main():
    """Main entry point for the AI Seller Bot."""
    # Set up logging
    logger = setup_logger("main", "INFO")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Starting AI Seller Bot...")
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with the required variables. See .env.example for reference.")
        return
    
    try:
        logger.info("Initializing Telegram Bot...")
        # Create and start the bot
        bot = TelegramBot()
        
        logger.info("Starting bot polling...")
        # Run the bot
        asyncio.run(bot.start_polling())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        print(f"❌ Error starting bot: {e}")
        print("Please check your configuration and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
