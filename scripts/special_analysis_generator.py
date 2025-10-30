#!/usr/bin/env python3
"""
Special Analysis Generator - Master Script
Runs all three special analysis page generators:
1. Notazons (Non-Amazon bow users)
2. Unique Projectiles (Unique arrows and bolts)
3. Dual Aura Items (Characters with 2+ offensive aura items)
"""

import sys
import os

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.notazons_analysis import analyze_notazons
from modules.unique_projectiles_analysis import analyze_unique_projectiles
from modules.dual_aura_analysis import analyze_dual_aura_items

def run_all_special_analyses():
    """Run all three special analysis scripts for both leagues"""
    
    print("🔍 Starting Special Analysis Generation...")
    print("="*60)
    
    # Track results
    results = {}
    
    try:
        # 1. Notazons Analysis
        print("\n📊 Generating Notazons Analysis...")
        sc_notazons = analyze_notazons("sc")
        hc_notazons = analyze_notazons("hc")
        results['notazons'] = {'sc': sc_notazons, 'hc': hc_notazons}
        print(f"✅ Notazons complete - SC: {sc_notazons}, HC: {hc_notazons}")
        
    except Exception as e:
        print(f"❌ Notazons analysis failed: {e}")
        results['notazons'] = {'error': str(e)}
    
    try:
        # 2. Unique Projectiles Analysis
        print("\n🏹 Generating Unique Projectiles Analysis...")
        sc_projectiles = analyze_unique_projectiles("sc")
        hc_projectiles = analyze_unique_projectiles("hc")
        results['projectiles'] = {'sc': sc_projectiles, 'hc': hc_projectiles}
        print(f"✅ Unique Projectiles complete - SC: {sc_projectiles}, HC: {hc_projectiles}")
        
    except Exception as e:
        print(f"❌ Unique Projectiles analysis failed: {e}")
        results['projectiles'] = {'error': str(e)}
    
    try:
        # 3. Dual Aura Items Analysis
        print("\n⚔️ Generating Dual Aura Items Analysis...")
        sc_aura = analyze_dual_aura_items("sc")
        hc_aura = analyze_dual_aura_items("hc")
        results['aura'] = {'sc': sc_aura, 'hc': hc_aura}
        print(f"✅ Dual Aura Items complete - SC: {sc_aura}, HC: {hc_aura}")
        
    except Exception as e:
        print(f"❌ Dual Aura Items analysis failed: {e}")
        results['aura'] = {'error': str(e)}
    
    # Summary report
    print("\n" + "="*60)
    print("📈 SPECIAL ANALYSIS SUMMARY")
    print("="*60)
    
    for analysis_type, data in results.items():
        if 'error' in data:
            print(f"❌ {analysis_type.title()}: FAILED - {data['error']}")
        else:
            print(f"✅ {analysis_type.title()}: SC={data['sc']}, HC={data['hc']}")
    
    print("\n🎉 Special analysis generation complete!")
    return results

def run_single_analysis(analysis_type, league="both"):
    """Run a single analysis type"""
    
    if analysis_type.lower() in ['notazons', 'notazon', 'bow']:
        print(f"🔍 Running Notazons analysis for {league} league(s)...")
        if league.lower() in ['both', 'all']:
            sc_count = analyze_notazons("sc")
            hc_count = analyze_notazons("hc")
            print(f"✅ Notazons: SC={sc_count}, HC={hc_count}")
        elif league.lower() in ['sc', 'softcore']:
            count = analyze_notazons("sc")
            print(f"✅ Notazons SC: {count}")
        elif league.lower() in ['hc', 'hardcore']:
            count = analyze_notazons("hc")
            print(f"✅ Notazons HC: {count}")
            
    elif analysis_type.lower() in ['projectiles', 'arrows', 'bolts', 'unique']:
        print(f"🏹 Running Unique Projectiles analysis for {league} league(s)...")
        if league.lower() in ['both', 'all']:
            sc_count = analyze_unique_projectiles("sc")
            hc_count = analyze_unique_projectiles("hc")
            print(f"✅ Unique Projectiles: SC={sc_count}, HC={hc_count}")
        elif league.lower() in ['sc', 'softcore']:
            count = analyze_unique_projectiles("sc")
            print(f"✅ Unique Projectiles SC: {count}")
        elif league.lower() in ['hc', 'hardcore']:
            count = analyze_unique_projectiles("hc")
            print(f"✅ Unique Projectiles HC: {count}")
            
    elif analysis_type.lower() in ['aura', 'dual', '2aura', 'auras']:
        print(f"⚔️ Running Dual Aura Items analysis for {league} league(s)...")
        if league.lower() in ['both', 'all']:
            sc_count = analyze_dual_aura_items("sc")
            hc_count = analyze_dual_aura_items("hc")
            print(f"✅ Dual Aura Items: SC={sc_count}, HC={hc_count}")
        elif league.lower() in ['sc', 'softcore']:
            count = analyze_dual_aura_items("sc")
            print(f"✅ Dual Aura Items SC: {count}")
        elif league.lower() in ['hc', 'hardcore']:
            count = analyze_dual_aura_items("hc")
            print(f"✅ Dual Aura Items HC: {count}")
    else:
        print(f"❌ Unknown analysis type: {analysis_type}")
        print("Available types: notazons, projectiles, aura")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run all analyses
        run_all_special_analyses()
    elif len(sys.argv) == 2:
        # Single argument - analysis type only
        run_single_analysis(sys.argv[1])
    elif len(sys.argv) == 3:
        # Two arguments - analysis type and league
        run_single_analysis(sys.argv[1], sys.argv[2])
    else:
        print("Usage:")
        print("  python special_analysis_generator.py                    # Run all analyses")
        print("  python special_analysis_generator.py <type>             # Run specific analysis (both leagues)")
        print("  python special_analysis_generator.py <type> <league>    # Run specific analysis for specific league")
        print()
        print("Types: notazons, projectiles, aura")
        print("Leagues: sc, hc, both")