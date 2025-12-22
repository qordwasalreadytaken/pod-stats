"""
Usage Examples for the Modular Page Generation System

This file demonstrates how to use the new modular system to generate pages

Basic page generation:
python3 scripts/generate_pages.py --mode hc --page all --data hc_ladder.json --hc-level-filter 70
python3 scripts/generate_pages.py --page all --mode sc
python3 scripts/generate_pages.py --page funfacts --mode sc

Force regeneration (skip caching and ignore season freeze):
python3 scripts/generate_pages.py --page all --mode sc --data sc_ladder.json --force
python3 scripts/generate_pages.py --page dataupdate #--mode sc --data sc_ladder.json --force
python3 scripts/generate_pages.py --page class --class Barbarian --mode hc --data hc_ladder.json --force
python3 scripts/generate_pages.py --page class --class Druid --mode sc --data sc_ladder.json --force
python3 scripts/generate_pages.py --page all --mode sc --force
python3 scripts/generate_pages.py --page charms --mode sc --force
python3 scripts/generate_pages.py --mode hc --page all --data hc_ladder.json --hc-level-filter 70 --force

Manual archive generation:
python3 scripts/api_integration.py archive monthly
python3 scripts/api_integration.py archive final --force
python3 scripts/api_integration.py archive monthly --force

Running examples:
python3 scripts/usage_examples.py        # Run all code examples
python3 scripts/usage_examples.py demo   # Show command line examples only

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

def example_force_page_generation():
    """Example: Force regeneration of pages (bypassing season freeze and any caching)"""
    print("=== Force Regenerating All Pages ===")
    
    # Force regenerate all softcore pages
    print("Forcing softcore page regeneration...")
    success_sc = generate_all_pages("sc_ladder.json", is_hardcore=False, force=True)
    
    # Force regenerate all hardcore pages  
    print("Forcing hardcore page regeneration...")
    success_hc = generate_all_pages("hc_ladder.json", is_hardcore=True, force=True)
    
    return success_sc and success_hc

def example_manual_archive_generation():
    """Example: Manually trigger archive generation"""
    print("=== Manual Archive Generation ===")
    
    try:
        # Import archive functions
        from api_integration import create_monthly_archive, create_final_archive
        
        # Generate monthly archive for current season
        print("Creating monthly archive...")
        monthly_result = create_monthly_archive()
        
        if monthly_result.get("success"):
            print(f"✅ Monthly archive created: {monthly_result.get('archive_path')}")
            
            # Optional: Create final archive (with force if needed)
            print("Creating final archive (forced)...")
            final_result = create_final_archive(force=True)
            
            if final_result.get("success"):
                print(f"✅ Final archive created: {final_result.get('archive_path')}")
                return True
            else:
                print(f"❌ Final archive failed: {final_result.get('error')}")
                return False
        else:
            print(f"❌ Monthly archive failed: {monthly_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Archive generation error: {e}")
        return False

def example_custom_archive_with_options():
    """Example: Create archive with custom options"""
    print("=== Custom Archive Generation ===")
    
    try:
        from api_integration import generate_archive
        
        # Generate archive for specific season with options
        result = generate_archive(
            archive_type="monthly",  # or "final"
            season_number=13,        # specific season
            base_path="/home/derek/Desktop/new-analytics",
            force=False             # set to True to override safety checks
        )
        
        if result.get("success"):
            print(f"✅ Custom archive created: {result.get('archive_path')}")
            print(f"📊 Processing results: {result.get('processing_results')}")
            return True
        else:
            print(f"❌ Custom archive failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Custom archive error: {e}")
        return False

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
    
    # Example 3: Force page regeneration
    if example_force_page_generation():
        print("✅ Force page regeneration completed successfully!\n")
    else:
        print("❌ Force page regeneration failed!\n")
    
    # Example 4: Manual archive generation
    if example_manual_archive_generation():
        print("✅ Manual archive generation completed successfully!\n")
    else:
        print("❌ Manual archive generation failed!\n")
    
    # Example 5: Custom archive with options
    if example_custom_archive_with_options():
        print("✅ Custom archive generation completed successfully!\n")
    else:
        print("❌ Custom archive generation failed!\n")
    
    # Example 6: Custom analysis
    if example_custom_analysis():
        print("✅ Custom analysis completed successfully!\n")
    else:
        print("❌ Custom analysis failed!\n")

def demo_command_line_usage():
    """Demonstrate command line usage examples"""
    print("🖥️  Command Line Usage Examples:")
    print()
    
    print("📄 Basic Page Generation:")
    print("   python3 scripts/generate_pages.py --mode sc --page all")
    print("   python3 scripts/generate_pages.py --mode hc --page all --hc-level-filter 70")
    print("   python3 scripts/generate_pages.py --page class --class Barbarian --mode sc")
    print()
    
    print("🔄 Force Page Regeneration (Override Season Freeze):")
    print("   python3 scripts/generate_pages.py --page all --mode sc --force")
    print("   python3 scripts/generate_pages.py --page home --mode hc --force")
    print("   python3 scripts/generate_pages.py --page class --class Barbarian --mode sc --force")
    print("   python3 scripts/generate_pages.py --page all --mode hc --hc-level-filter 70 --force")
    print()
    
    print("📦 Manual Archive Generation:")
    print("   # Via command line (if implemented):")
    print("   python3 scripts/api_integration.py archive monthly")
    print("   python3 scripts/api_integration.py archive final --force")
    print()
    print("   # Via Python code:")
    print("   python3 -c \"from scripts.api_integration import create_monthly_archive; create_monthly_archive()\"")
    print("   python3 -c \"from scripts.api_integration import create_final_archive; create_final_archive(force=True)\"")
    print()
    
    print("🎛️  Advanced Archive Options:")
    print("   python3 -c \"from scripts.api_integration import generate_archive; generate_archive('monthly', season_number=13, force=False)\"")
    print("   python3 -c \"from scripts.api_integration import generate_archive; generate_archive('final', season_number=12, force=True)\"")
    print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Show command line examples without running them
        demo_command_line_usage()
    else:
        # Run all examples
        main()