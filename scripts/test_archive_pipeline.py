#!/usr/bin/env python3
"""
Test Archive Generation Pipeline
"""
import sys
import os
sys.path.append('/home/derek/Desktop/new-analytics/scripts')

from api_integration import (
    generate_archive,
    create_monthly_archive,
    create_final_archive
)
import json
from pathlib import Path

def test_archive_pipeline():
    print("=== Testing Archive Generation Pipeline ===\n")
    
    # Test 1: Monthly Archive Generation (with force since season might be active)
    print("1. Testing Monthly Archive Generation...")
    print("\n--- Creating Monthly Archive (Force Mode) ---")
    
    monthly_result = create_monthly_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics",
        force=True  # Override safety checks for testing
    )
    
    if monthly_result["success"]:
        print("✅ Monthly archive created successfully!")
        print(f"   Archive Path: {monthly_result['archive_path']}")
        print(f"   Processing Time: {monthly_result['processing_time']} seconds")
        print(f"   Message: {monthly_result['message']}")
        
        # Check if metadata was created
        metadata_path = Path(monthly_result['archive_path']) / "archive_metadata.json"
        if metadata_path.exists():
            print(f"   ✅ Metadata file created: {metadata_path}")
            
            # Load and display key metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            archive_info = metadata["archive_info"]
            file_summary = metadata["file_summary"]
            
            print(f"   📊 Archive Info:")
            print(f"      - Season: {archive_info['season_number']}")
            print(f"      - Type: {archive_info['archive_type']}")
            print(f"      - Created: {archive_info['created_date']}")
            print(f"      - Total Characters: {file_summary['total_entries']:,}")
            print(f"      - Total Size: {file_summary['total_size_mb']} MB")
            
            # Check pipeline status
            pipeline_status = metadata["pipeline_status"]
            print(f"   🔧 Pipeline Status:")
            for step, status in pipeline_status.items():
                status_icon = "✅" if status == "completed" else "⚠️" if status in ["placeholder", "skipped"] else "❌"
                print(f"      - {step}: {status} {status_icon}")
        else:
            print("   ⚠️  Metadata file not found")
    else:
        print("❌ Monthly archive creation failed")
        print(f"   Error: {monthly_result['error']}")
        print(f"   Failed Step: {monthly_result.get('step_failed', 'unknown')}")
    
    print("\n" + "="*50)
    
    # Test 2: Final Archive Generation (with force)
    print("\n2. Testing Final Archive Generation...")
    print("\n--- Creating Final Archive (Force Mode) ---")
    
    final_result = create_final_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics", 
        force=True
    )
    
    if final_result["success"]:
        print("✅ Final archive created successfully!")
        print(f"   Archive Path: {final_result['archive_path']}")
        print(f"   Processing Time: {final_result['processing_time']} seconds")
        print(f"   Message: {final_result['message']}")
        
        # Check metadata
        metadata_path = Path(final_result['archive_path']) / "archive_metadata.json"
        if metadata_path.exists():
            print(f"   ✅ Metadata file created: {metadata_path}")
        else:
            print("   ⚠️  Metadata file not found")
    else:
        print("❌ Final archive creation failed")
        print(f"   Error: {final_result['error']}")
        print(f"   Failed Step: {final_result.get('step_failed', 'unknown')}")
    
    print("\n" + "="*50)
    
    # Test 3: Archive Directory Structure Verification
    print("\n3. Verifying Archive Directory Structure...")
    
    base_path = Path("/home/derek/Desktop/new-analytics")
    season_path = base_path / "Season" / "13"
    
    if season_path.exists():
        print(f"✅ Season directory exists: {season_path}")
        
        # List what was created
        for item in season_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(season_path)
                size_mb = round(item.stat().st_size / (1024 * 1024), 2)
                print(f"   📄 {rel_path} ({size_mb} MB)")
            elif item.is_dir() and item != season_path:
                rel_path = item.relative_to(season_path)
                print(f"   📁 {rel_path}/")
    else:
        print("❌ Season directory not found")
    
    print("\n" + "="*50)
    
    # Test 4: Safety Check (without force)
    print("\n4. Testing Safety Checks...")
    print("\n--- Attempting Monthly Archive Without Force ---")
    
    safety_result = create_monthly_archive(
        season_number=13,
        base_path="/home/derek/Desktop/new-analytics",
        force=False  # Should fail if season is active
    )
    
    if not safety_result["success"] and "still active" in safety_result["error"]:
        print("✅ Safety check working correctly")
        print(f"   Expected safety error: {safety_result['error']}")
    elif safety_result["success"]:
        print("⚠️  Safety check bypassed (season might have ended)")
    else:
        print("❌ Unexpected error in safety check")
        print(f"   Error: {safety_result['error']}")
    
    print("\n=== Archive Pipeline Tests Complete ===")

if __name__ == "__main__":
    test_archive_pipeline()