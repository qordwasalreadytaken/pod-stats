#!/usr/bin/env python3
"""
Test corrected archive logic - monthly archives should work during active seasons
"""
import sys
import os
sys.path.append('/home/derek/Desktop/new-analytics/scripts')

from api_integration import (
    create_monthly_archive,
    create_final_archive
)

def test_corrected_logic():
    print("=== Testing Corrected Archive Logic ===\n")
    
    # Test 1: Monthly archive during active season (should work without force)
    print("1. Testing Monthly Archive During Active Season...")
    print("   (Should work without force=True)")
    
    monthly_result = create_monthly_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics",
        force=False  # Should work without force now
    )
    
    if monthly_result["success"]:
        print("✅ Monthly archive created successfully during active season!")
        print(f"   Archive Path: {monthly_result['archive_path']}")
        print(f"   Processing Time: {monthly_result['processing_time']} seconds")
    else:
        print("❌ Monthly archive failed")
        print(f"   Error: {monthly_result['error']}")
    
    print("\n" + "="*50)
    
    # Test 2: Final archive during active season (should be blocked without force)
    print("\n2. Testing Final Archive During Active Season...")
    print("   (Should be blocked without force=True)")
    
    final_result = create_final_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics",
        force=False  # Should be blocked
    )
    
    if not final_result["success"] and "still active" in final_result["error"]:
        print("✅ Final archive correctly blocked during active season")
        print(f"   Expected safety error: {final_result['error']}")
    elif final_result["success"]:
        print("⚠️  Final archive created (season might have ended)")
        print(f"   Archive Path: {final_result['archive_path']}")
    else:
        print("❌ Unexpected error")
        print(f"   Error: {final_result['error']}")
    
    print("\n" + "="*50)
    
    # Test 3: Final archive with force (should work)
    print("\n3. Testing Final Archive With Force During Active Season...")
    print("   (Should work with force=True)")
    
    final_force_result = create_final_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics",
        force=True  # Override safety check
    )
    
    if final_force_result["success"]:
        print("✅ Final archive created with force override")
        print(f"   Archive Path: {final_force_result['archive_path']}")
        print(f"   Processing Time: {final_force_result['processing_time']} seconds")
    else:
        print("❌ Final archive with force failed")
        print(f"   Error: {final_force_result['error']}")
    
    print("\n=== Corrected Logic Summary ===")
    print("During ACTIVE season:")
    print("  ✅ Monthly archives: Allowed without force")
    print("  ❌ Final archives: Blocked (unless force=True)")
    print("\nDuring ENDED season:")
    print("  ✅ Monthly archives: Allowed")
    print("  ✅ Final archives: Allowed")
    print("\nDaily page updates:")
    print("  🔄 Active season: Continue updating")
    print("  🛑 Ended season: Freeze (no updates)")

if __name__ == "__main__":
    test_corrected_logic()