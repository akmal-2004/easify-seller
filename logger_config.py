import logging
import sys
from datetime import datetime

def setup_logger(name: str = "ai_seller_bot", level: str = "INFO") -> logging.Logger:
    """Set up a logger with both file and console handlers."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    
    # Create file handler
    # file_handler = logging.FileHandler(
    #     f'logs/ai_seller_bot_{datetime.now().strftime("%Y%m%d")}.log',
    #     encoding='utf-8'
    # )
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(file_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    # logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"ai_seller_bot.{name}")
    return logging.getLogger("ai_seller_bot")
