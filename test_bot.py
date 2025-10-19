#!/usr/bin/env python3
"""
Test script for the AI Seller Bot
Run this to test the bot functionality without starting the full telegram bot
"""

import asyncio
import os
from dotenv import load_dotenv
from agent import AISellerAgent

async def test_agent():
    """Test the AI agent functionality."""
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    # Initialize agent
    agent = AISellerAgent(openai_api_key, "en")
    
    print("🤖 Testing AI Seller Agent with proper tool calls...")
    print("=" * 60)
    
    # Test 1: Text search
    print("\n📝 Test 1: Text search for romantic bouquets")
    try:
        response1 = await agent.process_message(123, "I need a romantic bouquet for my girlfriend")
        print(f"Response: {response1}")
    except Exception as e:
        print(f"Error in Test 1: {e}")
    
    # Test 2: Price filter
    print("\n💰 Test 2: Search with price filter")
    try:
        response2 = await agent.process_message(123, "Show me bouquets under $50")
        print(f"Response: {response2}")
    except Exception as e:
        print(f"Error in Test 2: {e}")
    
    # Test 3: Follow-up conversation
    print("\n💬 Test 3: Follow-up conversation")
    try:
        response3 = await agent.process_message(123, "I like the first one, tell me more about it")
        print(f"Response: {response3}")
    except Exception as e:
        print(f"Error in Test 3: {e}")
    
    # Test 4: Simple greeting (no tool call needed)
    print("\n👋 Test 4: Simple greeting")
    try:
        response4 = await agent.process_message(123, "Hello, how are you?")
        print(f"Response: {response4}")
    except Exception as e:
        print(f"Error in Test 4: {e}")
    
    print("\n✅ Agent tests completed!")

if __name__ == "__main__":
    asyncio.run(test_agent())
