#!/usr/bin/env python3
"""
Test JSON validation functions for archive creation
"""
import sys
import os
sys.path.append('/home/derek/Desktop/new-analytics/scripts')

from api_integration import (
    validate_ladder_json_file,
    validate_archive_json_files, 
    check_json_files_for_archive
)
import json

def test_json_validation():
    print("=== Testing JSON Validation Functions ===\n")
    
    # Test 1: Individual file validation
    print("1. Testing individual file validation...")
    
    # Test SC ladder file
    print("\n--- Validating SC Ladder File ---")
    sc_result = validate_ladder_json_file("/home/derek/Desktop/new-analytics/sc_ladder.json", "sc")
    if sc_result["valid"]:
        print("✅ SC ladder file is VALID")
        print(f"   - Entries: {sc_result['entry_count']:,}")
        print(f"   - Size: {sc_result['file_size_mb']} MB")
        if sc_result["sample_character"]:
            char = sc_result["sample_character"]
            print(f"   - Sample: {char['title']} {char['name']} ({char['class']}, Level {char['level']})")
    else:
        print("❌ SC ladder file is INVALID")
        print(f"   - Error: {sc_result['error']}")
    
    # Test HC ladder file
    print("\n--- Validating HC Ladder File ---")
    hc_result = validate_ladder_json_file("/home/derek/Desktop/new-analytics/hc_ladder.json", "hc")
    if hc_result["valid"]:
        print("✅ HC ladder file is VALID")
        print(f"   - Entries: {hc_result['entry_count']:,}")
        print(f"   - Size: {hc_result['file_size_mb']} MB")
        if hc_result["sample_character"]:
            char = hc_result["sample_character"]
            print(f"   - Sample: {char['title']} {char['name']} ({char['class']}, Level {char['level']})")
    else:
        print("❌ HC ladder file is INVALID")
        print(f"   - Error: {hc_result['error']}")
    
    # Test 2: Both files validation
    print("\n\n2. Testing combined file validation...")
    print("\n--- Validating Both Ladder Files ---")
    both_result = validate_archive_json_files("/home/derek/Desktop/new-analytics")
    
    if both_result["success"]:
        if both_result["both_valid"]:
            print("✅ Both ladder files are VALID")
            summary = both_result["summary"]
            print(f"   - SC entries: {summary['sc_entries']:,}")
            print(f"   - HC entries: {summary['hc_entries']:,}")
            print(f"   - Total size: {summary['total_size_mb']} MB")
        else:
            print("❌ One or both ladder files are INVALID")
            if not both_result["softcore"]["valid"]:
                print(f"   - SC Error: {both_result['softcore']['error']}")
            if not both_result["hardcore"]["valid"]:
                print(f"   - HC Error: {both_result['hardcore']['error']}")
    else:
        print("❌ Failed to validate files")
        print(f"   - Error: {both_result['error']}")
    
    # Test 3: Archive readiness check
    print("\n\n3. Testing archive readiness check...")
    print("\n--- Checking Archive Readiness ---")
    readiness_result = check_json_files_for_archive(
        season_number=13,
        archive_type="monthly",
        base_path="/home/derek/Desktop/new-analytics"
    )
    
    if readiness_result["ready"]:
        print("✅ Files are READY for archive creation")
        summary = readiness_result["file_summary"]
        print(f"   - Season: {readiness_result['season_number']}")
        print(f"   - Archive type: {readiness_result['archive_type']}")
        print(f"   - Total entries: {summary['total_entries']:,}")
        print(f"   - SC: {summary['sc_entries']:,} entries")
        print(f"   - HC: {summary['hc_entries']:,} entries")
        print(f"   - Total size: {summary['total_size_mb']} MB")
    else:
        print("❌ Files are NOT READY for archive creation")
        print(f"   - Error: {readiness_result['error']}")
        if "validation_errors" in readiness_result:
            for error in readiness_result["validation_errors"]:
                print(f"   - {error}")
    
    # Test 4: Error handling (non-existent file)
    print("\n\n4. Testing error handling...")
    print("\n--- Testing Non-Existent File ---")
    error_result = validate_ladder_json_file("/fake/path/does_not_exist.json", "sc")
    if not error_result["valid"]:
        print("✅ Error handling works correctly")
        print(f"   - Expected error: {error_result['error']}")
    else:
        print("❌ Error handling failed - should have detected missing file")
    
    print("\n=== JSON Validation Tests Complete ===")

if __name__ == "__main__":
    test_json_validation()