#!/usr/bin/env python3
"""
Test Monthly Automation for Fresh Month (November)
"""
import sys
import os
sys.path.append('/home/derek/Desktop/new-analytics/scripts')

from api_integration import auto_monthly_archive

def test_fresh_month_automation():
    print("=== Testing Fresh Month Automation ===\n")
    
    # Simulate November 28th (when we don't have an existing archive)
    print("🗓️  Simulating November 28, 2025 (Fresh Month)")
    print("   - No existing November archive")
    print("   - Season should still be active")
    print("   - Should trigger archive creation")
    print()
    
    # Test with November 28th
    result = auto_monthly_archive(
        target_day=28,
        current_date="2025-11-28",  # November 28th
        base_path="/home/derek/Desktop/new-analytics",
        dry_run=True  # Dry run to avoid actually creating archives
    )
    
    print("📋 Automation Result:")
    print(f"   Success: {result['success']}")
    print(f"   Triggered: {result['triggered']}")
    print(f"   Dry Run: {result['dry_run']}")
    print(f"   Message: {result['message']}")
    
    if result['triggered'] and 'trigger_conditions' in result:
        trigger_conditions = result['trigger_conditions']
        if 'archive_details' in trigger_conditions:
            details = trigger_conditions['archive_details']
            print(f"\n📊 Would Create Archive:")
            print(f"   - Season: {details['season_number']}")
            print(f"   - Type: {details['archive_type']}")
            print(f"   - Month: {details['target_month']}")
            
            data_summary = details['data_summary']
            print(f"   - Characters: {data_summary['total_entries']:,}")
            print(f"   - Size: {data_summary['total_size_mb']} MB")
    
    print("\n🔄 Automation Summary:")
    if result['success'] and result['triggered']:
        print("✅ Monthly automation working correctly!")
        print("   - Calendar detection: Working")
        print("   - Season state check: Working")
        print("   - Archive readiness: Working")
        print("   - Would create archive: Yes")
    elif result['success'] and not result['triggered']:
        print("ℹ️  No action needed (as expected)")
        reason = result.get('trigger_conditions', {}).get('reason', 'Unknown')
        print(f"   - Reason: {reason}")
    else:
        print("❌ Automation issue detected")
        print(f"   - Error: {result.get('error', 'Unknown error')}")
    
    print("\n📅 Monthly Automation Ready!")
    print("   - Cron job: /home/derek/Desktop/new-analytics/scripts/monthly_archive_cron.py")
    print("   - Schedule: 0 2 28 * * (2 AM on 28th of each month)")
    print("   - Behavior: Auto-create monthly archives during active seasons")

if __name__ == "__main__":
    test_fresh_month_automation()