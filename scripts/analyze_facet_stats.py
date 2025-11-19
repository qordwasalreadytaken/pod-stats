#!/usr/bin/env python3
"""
Facet Stats Analyzer
Analyzes all Rainbow Facet stat combinations from character data.
Shows counts for each stat combination (3/3, 3/4, 4/3, etc.)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def extract_element(item):
    """Extract element type from facet properties"""
    element_types = ["fire", "cold", "lightning", "poison", "physical", "magic"]
    for element in element_types:
        for prop in item.get('PropertyList', []):
            if element in prop.lower():
                return element.capitalize()
    return "Unknown"

def extract_facet_stats(item):
    """
    Extract the two stat values from a facet.
    Returns (plus_stat, minus_stat) or (None, None) if not found.
    Example properties:
    - "+5% Increased Fire Damage"
    - "-5% to Enemy Fire Resistance"
    """
    properties = item.get('PropertyList', [])
    plus_stat = None
    minus_stat = None
    
    for prop in properties:
        # Look for +X% Increased <Element> Damage (the damage boost)
        if '+' in prop and 'Increased' in prop and 'Damage' in prop:
            # Extract number between + and %
            try:
                num_str = prop.split('+')[1].split('%')[0].strip()
                plus_stat = int(num_str)
            except (IndexError, ValueError):
                pass
        
        # Look for -X% to Enemy <Element> Resistance (the resistance reduction)
        if '-' in prop and 'Enemy' in prop and 'Resistance' in prop:
            # Extract number between - and %
            try:
                num_str = prop.split('-')[1].split('%')[0].strip()
                minus_stat = int(num_str)
            except (IndexError, ValueError):
                pass
    
    return plus_stat, minus_stat

def analyze_facets(character_data):
    """Analyze all facets from character data"""
    # Track facets by element and stat combination
    facet_stats = defaultdict(lambda: defaultdict(int))
    
    for char in character_data:
        if not isinstance(char, dict):
            continue
        
        # Check equipped items
        for item in char.get('Equipped', []):
            if not isinstance(item, dict):
                continue
            
            # Check sockets for facets
            for socketed_item in item.get('Sockets', []):
                if socketed_item.get('Title') == 'Rainbow Facet':
                    element = extract_element(socketed_item)
                    plus_stat, minus_stat = extract_facet_stats(socketed_item)
                    
                    if plus_stat and minus_stat:
                        stat_combo = f"{plus_stat}/{minus_stat}"
                        facet_stats[element][stat_combo] += 1
    
    return facet_stats

def print_facet_report(facet_stats):
    """Print formatted report of facet statistics"""
    print("\n" + "=" * 70)
    print("RAINBOW FACET STATISTICS BREAKDOWN")
    print("=" * 70)
    
    # Sort elements by total count
    element_totals = {}
    for element, stats in facet_stats.items():
        element_totals[element] = sum(stats.values())
    
    sorted_elements = sorted(element_totals.items(), key=lambda x: -x[1])
    
    for element, total in sorted_elements:
        stats = facet_stats[element]
        perfect_count = stats.get('5/5', 0)
        
        print(f"\n{element} Facets: {total} total ({perfect_count} perfect)")
        print("-" * 50)
        
        # Sort stat combinations (perfect first, then by total value descending)
        def combo_sort_key(item):
            combo, count = item
            plus_val, minus_val = map(int, combo.split('/'))
            total_val = plus_val + minus_val
            return (-total_val, -plus_val, -minus_val)  # Higher totals first
        
        sorted_stats = sorted(stats.items(), key=combo_sort_key)
        
        for stat_combo, count in sorted_stats:
            percentage = (count / total * 100) if total > 0 else 0
            perfect_indicator = " ⭐ PERFECT" if stat_combo == "5/5" else ""
            print(f"  {stat_combo}: {count:3d} ({percentage:5.1f}%)") # {perfect_indicator}")
    
    print("\n" + "=" * 70)
    print(f"TOTAL FACETS ANALYZED: {sum(element_totals.values())}")
    print("=" * 70 + "\n")

def main():
    """Main entry point"""
    # Determine which character file to load
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = 'sc'  # Default to softcore
    
    if mode not in ['sc', 'hc']:
        print("Usage: python analyze_facet_stats.py [sc|hc]")
        print("  sc = softcore (default)")
        print("  hc = hardcore")
        sys.exit(1)
    
    # Load character data
    char_file = f"{mode}_ladder.json"
    char_path = Path(char_file)
    
    if not char_path.exists():
        print(f"❌ Error: Character file not found: {char_file}")
        print(f"   Looking in: {char_path.absolute()}")
        sys.exit(1)
    
    print(f"📊 Loading {mode.upper()} character data from {char_file}...")
    
    try:
        with open(char_path, 'r') as f:
            character_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error reading JSON file: {e}")
        sys.exit(1)
    
    print(f"✓ Loaded {len(character_data)} characters")
    print("🔍 Analyzing facet stats...")
    

    # Analyze facets
    facet_stats = analyze_facets(character_data)
    
    if not facet_stats:
        print("⚠️  No facets found in character data")
        sys.exit(0)
    
    # Print report
    print_facet_report(facet_stats)

if __name__ == "__main__":
    main()

