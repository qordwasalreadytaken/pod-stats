#!/usr/bin/env python3
"""
GitHub Automation Script
Simple orchestrator for GitHub Actions/cron jobs that runs the modular page generation system
"""

import sys
import os
from datetime import datetime
import traceback

# Add current directory to path for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)

def run_full_update():
    """
    Run the complete update process:
    1. Generate all pages for both SC and HC using new modular system
    2. Fetch fresh data and update tracking files
    """
    
    print("🚀 Starting GitHub automation script...")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Generate all softcore pages
        print("\n�️ Generating all softcore pages...")
        os.system("python3 scripts/generate_pages.py --page all --mode sc")
        print("✅ Softcore pages generated")
        
        # Step 2: Generate all hardcore pages  
        print("\n⚔️ Generating all hardcore pages...")
        os.system("python3 scripts/generate_pages.py --page all --mode hc")
        print("✅ Hardcore pages generated")
        
        # Step 3: Update tracking data
        print("\n📊 Updating data tracking...")
        timestamp = datetime.now().strftime("GitHub_%Y%m%d_%H%M")
        os.system(f"python3 scripts/generate_pages.py --page dataupdate --snapshot-label '{timestamp}'")
        print("✅ Data tracking updated")
        
        print("\n🎉 All updates completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n💥 ERROR during automation: {e}")
        traceback.print_exc()
        return False


def run_pages_only():
    """
    Generate pages only (without API update) - useful for testing
    """
    print("📄 Generating pages from existing data...")
    
    try:
        # Generate softcore pages
        result1 = os.system("python3 scripts/generate_pages.py --page all --mode sc")
        
        # Generate hardcore pages
        result2 = os.system("python3 scripts/generate_pages.py --page all --mode hc")
        
        return result1 == 0 and result2 == 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Main entry point for GitHub automation"""
    
    # Check if we should skip API update (for testing)
    skip_api = "--skip-api" in sys.argv
    
    if skip_api:
        print("⚠️ Skipping API update (testing mode)")
        success = run_pages_only()
    else:
        success = run_full_update()
    
    if success:
        print("\n✅ GitHub automation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ GitHub automation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()