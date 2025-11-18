#!/usr/bin/env python3
"""
Test script for archive folder structure functionality
Tests creation, validation, and information gathering for archive folders
"""

import sys
import os
from pathlib import Path

# Add the current directory to sys.path to import api_integration
sys.path.append(str(Path(__file__).parent))

import api_integration

def test_archive_folder_structure():
    """Test the complete archive folder structure functionality"""
    
    print("🗂️  Testing Archive Folder Structure")
    print("=" * 50)
    
    # Test parameters
    season_number = 13
    test_base_path = Path.cwd() / "test_archives"
    
    # Clean up any existing test folder
    if test_base_path.exists():
        import shutil
        shutil.rmtree(test_base_path)
        print(f"Cleaned up existing test folder: {test_base_path}")
    
    print(f"Testing with Season {season_number}")
    print(f"Base path: {test_base_path}")
    print()
    
    # Test 1: Get folder info before creation
    print("📋 Test 1: Get Archive Folder Info (before creation)")
    monthly_info = api_integration.get_archive_folder_info(season_number, "monthly", test_base_path)
    final_info = api_integration.get_archive_folder_info(season_number, "final", test_base_path)
    
    print("Monthly archive info:")
    for key, value in monthly_info.items():
        print(f"  {key}: {value}")
    print()
    
    print("Final archive info:")
    for key, value in final_info.items():
        print(f"  {key}: {value}")
    print()
    
    # Test 2: Validate folder structure before creation (should fail)
    print("🔍 Test 2: Validate Structure (before creation - should fail)")
    monthly_validation = api_integration.validate_archive_folder_structure(season_number, "monthly", test_base_path)
    final_validation = api_integration.validate_archive_folder_structure(season_number, "final", test_base_path)
    
    print(f"Monthly validation success: {monthly_validation['success']}")
    print(f"Final validation success: {final_validation['success']}")
    print()
    
    # Test 3: Create monthly archive structure
    print("📁 Test 3: Create Monthly Archive Structure")
    monthly_creation = api_integration.create_archive_folder_structure(season_number, "monthly", test_base_path)
    
    if monthly_creation['success']:
        print("✅ Monthly archive structure created successfully!")
        print(f"  Season folder: {monthly_creation['season_folder']}")
        print(f"  Archive folder: {monthly_creation['archive_folder']}")
        print(f"  Charts folder: {monthly_creation['charts_folder']}")
        print(f"  Archive name: {monthly_creation['archive_name']}")
    else:
        print(f"❌ Monthly archive creation failed: {monthly_creation['error']}")
    print()
    
    # Test 4: Create final archive structure
    print("📁 Test 4: Create Final Archive Structure") 
    final_creation = api_integration.create_archive_folder_structure(season_number, "final", test_base_path)
    
    if final_creation['success']:
        print("✅ Final archive structure created successfully!")
        print(f"  Season folder: {final_creation['season_folder']}")
        print(f"  Archive folder: {final_creation['archive_folder']}")
        print(f"  Charts folder: {final_creation['charts_folder']}")
        print(f"  Archive name: {final_creation['archive_name']}")
    else:
        print(f"❌ Final archive creation failed: {final_creation['error']}")
    print()
    
    # Test 5: Validate folder structure after creation (should succeed)
    print("🔍 Test 5: Validate Structure (after creation - should succeed)")
    monthly_validation_after = api_integration.validate_archive_folder_structure(season_number, "monthly", test_base_path)
    final_validation_after = api_integration.validate_archive_folder_structure(season_number, "final", test_base_path)
    
    print("Monthly validation after creation:")
    print(f"  Success: {monthly_validation_after['success']}")
    print(f"  All exist: {monthly_validation_after['all_exist']}")
    print(f"  All directories: {monthly_validation_after['all_directories']}")
    print(f"  All writable: {monthly_validation_after['all_writable']}")
    print()
    
    print("Final validation after creation:")
    print(f"  Success: {final_validation_after['success']}")
    print(f"  All exist: {final_validation_after['all_exist']}")
    print(f"  All directories: {final_validation_after['all_directories']}")
    print(f"  All writable: {final_validation_after['all_writable']}")
    print()
    
    # Test 6: Test duplicate creation (should be safe)
    print("🔄 Test 6: Test Duplicate Creation (should be safe)")
    duplicate_creation = api_integration.create_archive_folder_structure(season_number, "monthly", test_base_path)
    
    if duplicate_creation['success']:
        print("✅ Duplicate creation handled safely!")
    else:
        print(f"❌ Duplicate creation failed: {duplicate_creation['error']}")
    print()
    
    # Test 7: Check actual folder structure
    print("📂 Test 7: Verify Actual Folder Structure")
    season_path = test_base_path / "Season" / str(season_number)
    
    if season_path.exists():
        print(f"Season folder exists: {season_path}")
        for item in season_path.iterdir():
            if item.is_dir():
                print(f"  📁 {item.name}/")
                charts_path = item / "charts"
                if charts_path.exists():
                    print(f"    📁 charts/")
                else:
                    print(f"    ❌ charts/ missing")
    else:
        print(f"❌ Season folder not found: {season_path}")
    print()
    
    # Test 8: Test error handling with invalid paths
    print("⚠️  Test 8: Test Error Handling")
    invalid_path = "/nonexistent/invalid/path"
    error_test = api_integration.create_archive_folder_structure(season_number, "monthly", invalid_path)
    
    if not error_test['success']:
        print(f"✅ Error handling works: {error_test['error']}")
    else:
        print("❌ Expected error handling to fail with invalid path")
    print()
    
    print("🎉 Archive Folder Structure Testing Complete!")
    print(f"Test archives created in: {test_base_path}")
    print("You can inspect the folder structure and then delete the test_archives folder when done.")

if __name__ == "__main__":
    test_archive_folder_structure()