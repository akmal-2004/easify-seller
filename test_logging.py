#!/usr/bin/env python3
"""
Test script to verify logging functionality
"""

import os
from logger_config import setup_logger

def test_logging():
    """Test logging functionality."""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Set up logger
    logger = setup_logger("test", "DEBUG")
    
    print("Testing logging functionality...")
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test exception logging
    try:
        raise ValueError("This is a test exception")
    except Exception as e:
        logger.error(f"Caught exception: {e}", exc_info=True)
    
    print("Logging test completed. Check logs/ directory for log files.")

if __name__ == "__main__":
    test_logging()
