"""
Usage Examples for the Modular Page Generation System

This file demonstrates how to use the new modular system to generate pages

python3 scripts/generate_pages.py --mode hc --page all --data hc_ladder.json --hc-level-filter 70
python3 scripts/generate_pages.py --page all --mode sc

"""

from generate_pages import generate_all_pages, generate_single_page
from modules.shared_utils import load_character_data

def example_generate_all_softcore():
    """Example: Generate all softcore pages"""
    print("=== Generating All Softcore Pages ===")
    success = generate_all_pages("sc_ladder.json", is_hardcore=False)
    return success

def example_generate_all_hardcore():
    """Example: Generate all hardcore pages"""
    print("=== Generating All Hardcore Pages ===")
    success = generate_all_pages("hc_ladder.json", is_hardcore=True)
    return success

def example_generate_single_page():
    """Example: Generate just the items page"""
    print("=== Generating Single Page (Items) ===")
    success = generate_single_page("items", "sc_ladder.json", is_hardcore=False)
    return success

def example_custom_analysis():
    """Example: Use modules for custom analysis"""
    print("=== Custom Analysis Example ===")
    
    # Load data
    all_characters = load_character_data("sc_ladder.json")
    
    if not all_characters:
        print("No data loaded")
        return False
    
    # Use individual analyzers for custom work
    from modules.items_equipment_page import ItemsEquipmentAnalyzer
    from modules.mercenary_page import MercenaryAnalyzer
    from modules.fun_facts_page import FunFactsAnalyzer
    
    # Analyze items
    items_analyzer = ItemsEquipmentAnalyzer(all_characters)
    items_data = items_analyzer.analyze_all_items()
    
    print(f"Most popular runeword: {items_data['counters']['runeword'].most_common(1)}")
    
    # Analyze mercenaries
    merc_analyzer = MercenaryAnalyzer(all_characters)
    merc_data = merc_analyzer.analyze_mercenaries()
    
    print(f"Most popular mercenary: {merc_data['mercenary_counts'].most_common(1)}")
    
    # Analyze fun facts
    facts_analyzer = FunFactsAnalyzer(all_characters)
    facts_data = facts_analyzer.analyze_fun_facts()
    
    print(f"Total characters analyzed: {facts_data['character_count']}")
    print(f"Undead characters: {facts_data['undead_data']['count']}")
    
    return True

def main():
    """Run all examples"""
    print("🚀 PoD Analytics Modular System Examples\n")
    
    # Example 1: Generate all pages for softcore
    if example_generate_all_softcore():
        print("✅ Softcore pages generated successfully!\n")
    else:
        print("❌ Softcore page generation failed!\n")
    
    # Example 2: Generate single page
    if example_generate_single_page():
        print("✅ Single page generated successfully!\n")
    else:
        print("❌ Single page generation failed!\n")
    
    # Example 3: Custom analysis
    if example_custom_analysis():
        print("✅ Custom analysis completed successfully!\n")
    else:
        print("❌ Custom analysis failed!\n")

if __name__ == "__main__":
    main()