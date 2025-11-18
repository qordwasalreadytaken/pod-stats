#!/usr/bin/env python3
"""
Monthly Archive Cron Job
Auto-generated script for monthly archive creation
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.append('/home/derek/Desktop/new-analytics/scripts')

# Import archive functions
from api_integration import auto_monthly_archive

def main():
    """Main cron job function"""
    print(f"=== Monthly Archive Cron Job ===")
    print(f"Started: {datetime.now().isoformat()}")
    
    try:
        # Run automatic monthly archive
        result = auto_monthly_archive(
            target_day=28,
            base_path="/home/derek/Desktop/new-analytics",
            dry_run=False
        )
        
        if result["success"]:
            if result["triggered"]:
                print(f"✅ SUCCESS: {result['message']}")
                exit(0)
            else:
                print(f"ℹ️  NO ACTION: {result['message']}")
                exit(0)
        else:
            print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
            exit(1)
            
    except Exception as e:
        print(f"❌ CRON ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()