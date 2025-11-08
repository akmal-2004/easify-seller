#!/usr/bin/env python3
"""
Test script to verify photo functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from app.search_tools import search_products_by_text

def test_photo_extraction():
    """Test photo extraction from search results."""
    load_dotenv()
    
    print("🖼️ Testing photo extraction from search results...")
    print("=" * 50)
    
    # Test search
    results = search_products_by_text("romantic bouquet", k=3)
    
    if not results:
        print("❌ No search results found")
        return
    
    print(f"✅ Found {len(results)} results")
    print()
    
    for i, result in enumerate(results, 1):
        meta = result['meta']
        name = meta.get('name_en', 'Unknown Product')
        price = meta.get('price', 0) / 1000
        
        print(f"Product {i}: {name}")
        print(f"Price: ${price:.2f}")
        
        # Test photo extraction
        main_photo = meta.get('photo_url')
        
        if main_photo:
            print(f"Main Photo: {main_photo}")
        else:
            print("❌ No main photo found")
        
        print("-" * 30)

if __name__ == "__main__":
    test_photo_extraction()
