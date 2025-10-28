#!/usr/bin/env python3
"""
Test script for fetch_ladder_data.py
Quick test to ensure the data fetching works properly
"""

import sys
import os
import json
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.append(str(scripts_dir))

def test_ladder_fetch():
    """Test the ladder data fetching functionality"""
    print("🧪 Testing ladder data fetch...")
    
    # Change to scripts directory for execution
    original_cwd = os.getcwd()
    try:
        os.chdir("scripts")
        
        # Import and run the fetch
        from fetch_ladder_data import main
        main()
        
        # Check if files were created
        os.chdir("..")  # Back to root
        
        sc_file = Path("sc_ladder.json")
        hc_file = Path("hc_ladder.json")
        
        if sc_file.exists():
            with open(sc_file) as f:
                sc_data = json.load(f)
            print(f"✅ SC Ladder: {len(sc_data)} characters")
        else:
            print("❌ SC ladder file not found")
            
        if hc_file.exists():
            with open(hc_file) as f:
                hc_data = json.load(f)
            print(f"✅ HC Ladder: {len(hc_data)} characters")
        else:
            print("❌ HC ladder file not found")
            
        print("🎉 Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    test_ladder_fetch()