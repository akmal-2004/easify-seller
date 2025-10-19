#!/usr/bin/env python3
"""
Test script to verify photo functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from search_tools import search_products_by_text, get_product_photo_url, get_product_photo_urls

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
        main_photo = get_product_photo_url(meta)
        all_photos = get_product_photo_urls(meta)
        
        if main_photo:
            print(f"Main Photo: {main_photo}")
        else:
            print("❌ No main photo found")
        
        if all_photos:
            print(f"All Photos: {len(all_photos)} photos")
            for j, photo in enumerate(all_photos[:3]):  # Show first 3
                print(f"  Photo {j+1}: {photo}")
        else:
            print("❌ No photos found")
        
        print("-" * 30)

if __name__ == "__main__":
    test_photo_extraction()
