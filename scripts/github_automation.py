#!/usr/bin/env python3
"""
GitHub Automation Script
Simple orchestrator for GitHub Actions/cron jobs that runs the modular page generation system
"""

import sys
import os
from datetime import datetime
import traceback

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

import api_integration


def run_full_update():
    """
    Run the complete update process:
    1. Fetch fresh data via API
    2. Generate all pages for both SC and HC
    3. Update usage over time data
    """
    
    print("🚀 Starting GitHub automation script...")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Fetch fresh data and update CSV files
        print("\n📡 Fetching fresh data via API...")
        api_integration.full_data_update()
        print("✅ API data update completed")
        
        # Step 2: Generate all softcore pages
        print("\n🛡️ Generating softcore pages...")
        sc_result = os.system("python3 scripts/generate_pages.py --page all --mode sc")
        if sc_result == 0:
            print("✅ Softcore pages generated successfully")
        else:
            print("❌ Softcore page generation failed")
            return False
        
        # Step 3: Generate all hardcore pages
        print("\n⚔️ Generating hardcore pages...")
        hc_result = os.system("python3 scripts/generate_pages.py --page all --mode hc")
        if hc_result == 0:
            print("✅ Hardcore pages generated successfully")
        else:
            print("❌ Hardcore page generation failed")
            return False
        
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
    
    sc_result = os.system("python3 scripts/generate_pages.py --page all --mode sc")
    hc_result = os.system("python3 scripts/generate_pages.py --page all --mode hc")
    
    return sc_result == 0 and hc_result == 0


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