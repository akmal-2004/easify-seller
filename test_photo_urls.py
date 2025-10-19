#!/usr/bin/env python3
"""
Test script to verify photo URLs are accessible
"""

import requests
from search_tools import search_products_by_text

def test_photo_urls():
    """Test if photo URLs are accessible."""
    print("🖼️ Testing photo URL accessibility...")
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
        photo_id = meta.get('photo')
        
        print(f"Product {i}: {name}")
        
        if photo_id:
            photo_url = f"https://imagedelivery.net/kjxkUqyuhQCleQqPHYxkVQ/{photo_id}/public"
            print(f"Photo URL: {photo_url}")
            
            try:
                response = requests.head(photo_url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Photo accessible (status: {response.status_code})")
                else:
                    print(f"❌ Photo not accessible (status: {response.status_code})")
            except Exception as e:
                print(f"❌ Photo URL test failed: {e}")
        else:
            print("❌ No photo ID found")
        
        print("-" * 30)

if __name__ == "__main__":
    test_photo_urls()
