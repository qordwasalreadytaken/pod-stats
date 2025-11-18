#!/usr/bin/env python3
"""
Test script for archive-specific API enhancements
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_integration import (
    get_archive_season_info,
    should_create_monthly_archive,
    should_create_final_archive,
    should_freeze_live_site,
    get_banner_text_for_archive,
    get_live_site_freeze_banner,
    get_archive_folder_name
)


def test_archive_api():
    """Test all archive-specific API functions"""
    
    print("🧪 Testing Archive API Integration")
    print("=" * 50)
    
    # Test main season info function
    print("\n1. Testing get_archive_season_info():")
    archive_info = get_archive_season_info()
    if archive_info:
        print(f"   ✓ Season: {archive_info['season_number']}")
        print(f"   ✓ Status: {archive_info['status']}")
        print(f"   ✓ Archive Folder: {archive_info['archive_folder']}")
        print(f"   ✓ Banner Text: {archive_info['banner_text']}")
        print(f"   ✓ Is Season End: {archive_info['is_season_end']}")
        print(f"   ✓ Needs Freeze: {archive_info['needs_freeze']}")
        if archive_info['end_time']:
            print(f"   ✓ End Time: {archive_info['end_time']}")
    else:
        print("   ❌ Failed to get archive season info")
        return False
    
    # Test monthly archive condition
    print("\n2. Testing should_create_monthly_archive():")
    monthly_result = should_create_monthly_archive()
    print(f"   Should create monthly archive: {monthly_result}")
    
    # Test final archive condition
    print("\n3. Testing should_create_final_archive():")
    final_result = should_create_final_archive()
    print(f"   Should create final archive: {final_result}")
    
    # Test live site freeze condition
    print("\n4. Testing should_freeze_live_site():")
    freeze_result = should_freeze_live_site()
    print(f"   Should freeze live site: {freeze_result}")
    
    # Test banner text generation
    print("\n5. Testing banner text functions:")
    monthly_banner = get_banner_text_for_archive("monthly")
    final_banner = get_banner_text_for_archive("final")
    freeze_banner = get_live_site_freeze_banner()
    
    print(f"   Monthly banner: {monthly_banner}")
    print(f"   Final banner: {final_banner}")
    print(f"   Freeze banner: {freeze_banner}")
    
    # Test folder name
    print("\n6. Testing get_archive_folder_name():")
    folder_name = get_archive_folder_name()
    print(f"   Archive folder name: {folder_name}")
    
    print("\n" + "=" * 50)
    print("🎉 Archive API testing complete!")
    
    return True


if __name__ == "__main__":
    test_archive_api()