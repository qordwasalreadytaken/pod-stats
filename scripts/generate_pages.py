"""
Main Page Generator Script
Orchestrates the generation of all specialized pages using the modular system
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Store original paths before changing directory
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent  # This should be the pod-stats directory

# Add modules to path
sys.path.append(str(SCRIPT_DIR / 'modules'))

from modules.home_page import generate_home_page
from modules.items_equipment_page import generate_items_equipment_page
from modules.mercenary_page import generate_mercenary_page
from modules.fun_facts_page import generate_fun_facts_page
from modules.class_pages import generate_all_class_pages, generate_single_class_page
from modules.shared_utils import load_character_data, filter_characters_by_level

# Import API integration for data updates
import api_integration


def generate_all_pages(json_file_path="sc_ladder.json", is_hardcore=False, hc_level_filter=None):
    """
    Generate all pages using the modular system
    
    Args:
        json_file_path: Path to the character data JSON file (relative to root directory)
        is_hardcore: Whether this is hardcore mode data
        hc_level_filter: Minimum level filter for hardcore characters (e.g., 70)
    """
    
    # Resolve JSON file path relative to root directory
    if not os.path.isabs(json_file_path):
        json_file_path = ROOT_DIR / json_file_path
    
    # If the file doesn't exist, try looking in the current directory
    if not os.path.exists(json_file_path):
        # Try the current working directory
        alt_path = Path.cwd() / Path(json_file_path).name
        if os.path.exists(alt_path):
            json_file_path = alt_path
        # Try the script's parent directory
        elif os.path.exists(ROOT_DIR / Path(json_file_path).name):
            json_file_path = ROOT_DIR / Path(json_file_path).name
    
    print(f"Starting page generation from {json_file_path}")
    print(f"Mode: {'Hardcore' if is_hardcore else 'Softcore'}")
    if is_hardcore and hc_level_filter:
        print(f"Level filter: {hc_level_filter}+")
    
    # Load character data once for all pages
    all_characters = load_character_data(str(json_file_path))
    
    if not all_characters:
        print("ERROR: No character data loaded. Cannot generate pages.")
        return False
    
    print(f"Loaded {len(all_characters)} characters")
    
    # Apply level filtering if specified (for hardcore mode)
    if is_hardcore and hc_level_filter:
        all_characters = filter_characters_by_level(all_characters, hc_level_filter)
        if not all_characters:
            print(f"ERROR: No characters found at level {hc_level_filter}+ after filtering.")
            return False
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Determine file prefix for hardcore/softcore
    prefix = "hc" if is_hardcore else ""
    
    # Change to root directory for output generation
    original_cwd = os.getcwd()
    os.chdir(ROOT_DIR)
    
    try:
        # Generate Home Page
        print("Generating home page...")
        home_html = generate_home_page(json_file_path, is_hardcore, hc_level_filter)
        if home_html:
            home_filename = f"{prefix}Home.html" if prefix else "Home.html"
            with open(home_filename, 'w', encoding='utf-8') as f:
                f.write(home_html)
            print(f"✓ Home page saved as {home_filename}")
            
            # For GitHub Pages: Create index.html as default landing page
            if not is_hardcore:  # Only create index.html for softcore (main site)
                with open("index.html", 'w', encoding='utf-8') as f:
                    f.write(home_html)
                print("✓ GitHub Pages index.html created (copy of Home.html)")
        else:
            print("✗ Failed to generate home page")
            
        # Generate Items & Equipment Page
        print("Generating items & equipment page...")
        items_html = generate_items_equipment_page(all_characters, timestamp, is_hardcore, hc_level_filter)
        if items_html:
            items_filename = f"{prefix}Items.html"
            with open(items_filename, 'w', encoding='utf-8') as f:
                f.write(items_html)
            print(f"✓ Items & Equipment page saved as {items_filename}")
        else:
            print("✗ Failed to generate items & equipment page")
            
        # Generate Mercenary Page
        print("Generating mercenary page...")
        merc_html = generate_mercenary_page(all_characters, timestamp, is_hardcore, hc_level_filter)
        if merc_html:
            merc_filename = f"{prefix}Mercenaries.html"
            with open(merc_filename, 'w', encoding='utf-8') as f:
                f.write(merc_html)
            print(f"✓ Mercenary page saved as {merc_filename}")
        else:
            print("✗ Failed to generate mercenary page")
            
        # Generate Fun Facts Page
        print("Generating fun facts page...")
        facts_html = generate_fun_facts_page(all_characters, timestamp, is_hardcore, hc_level_filter)
        if facts_html:
            facts_filename = f"{prefix}FunFacts.html"
            with open(facts_filename, 'w', encoding='utf-8') as f:
                f.write(facts_html)
            print(f"✓ Fun Facts page saved as {facts_filename}")
        else:
            print("✗ Failed to generate fun facts page")
            
        # Generate Class Pages
        print("Generating class pages...")
        class_pages = generate_all_class_pages(all_characters, timestamp, is_hardcore, hc_level_filter)
        if class_pages:
            print(f"✓ Generated {len(class_pages)} class pages")
        else:
            print("✗ Failed to generate class pages")
            
        print(f"\n🎉 Page generation complete!")
        print(f"Generated pages for {len(all_characters)} characters")
        print(f"Timestamp: {timestamp}")
        
        return True
        
    except Exception as e:
        print(f"ERROR during page generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


def update_data_and_generate_tracking_pages(snapshot_label=None):
    """
    Perform full data update: fetch API data, update CSV, and generate tracking pages
    This runs independently of the main page generation system
    
    Args:
        snapshot_label: Optional custom label for this data snapshot
    """
    print("🚀 Starting data update and tracking page generation...")
    print("=" * 60)
    
    # Change to root directory for API integration
    original_cwd = os.getcwd()
    os.chdir(ROOT_DIR)
    
    try:
        # Run the full data update from api_integration.py
        api_integration.full_data_update(snapshot_label)
        
        print("\n✅ Data update and tracking page generation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during data update: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


def generate_single_page(page_type, json_file_path="sc_ladder.json", is_hardcore=False, hc_level_filter=None, class_name=None):
    """
    Generate a single page type
    
    Args:
        page_type: Type of page to generate ('home', 'items', 'mercenary', 'funfacts', 'class')
        json_file_path: Path to the character data JSON file (relative to root directory)
        is_hardcore: Whether this is hardcore mode data
        hc_level_filter: Minimum level filter for hardcore characters (e.g., 70)
        class_name: Required when page_type is 'class' (e.g., 'Barbarian', 'Sorceress')
    """
    
    # Resolve JSON file path relative to root directory
    if not os.path.isabs(json_file_path):
        json_file_path = ROOT_DIR / json_file_path
    
    # If the file doesn't exist, try looking in the current directory
    if not os.path.exists(json_file_path):
        # Try the current working directory
        alt_path = Path.cwd() / Path(json_file_path).name
        if os.path.exists(alt_path):
            json_file_path = alt_path
        # Try the script's parent directory
        elif os.path.exists(ROOT_DIR / Path(json_file_path).name):
            json_file_path = ROOT_DIR / Path(json_file_path).name
    
    # Load character data
    all_characters = load_character_data(str(json_file_path))
    
    if not all_characters:
        print("ERROR: No character data loaded. Cannot generate page.")
        return False
    
    # Apply level filtering if specified (for hardcore mode)
    if is_hardcore and hc_level_filter:
        all_characters = filter_characters_by_level(all_characters, hc_level_filter)
        if not all_characters:
            print(f"ERROR: No characters found at level {hc_level_filter}+ after filtering.")
            return False
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Determine file prefix
    prefix = "hc" if is_hardcore else ""
    
    # Change to root directory for output generation
    original_cwd = os.getcwd()
    os.chdir(ROOT_DIR)
    
    try:
        if page_type.lower() == 'home':
            print("Generating home page...")
            html_content = generate_home_page(json_file_path, is_hardcore, hc_level_filter)
            filename = f"{prefix}Home.html" if prefix else "Home.html"
            
        elif page_type.lower() == 'items':
            print("Generating items & equipment page...")
            html_content = generate_items_equipment_page(all_characters, timestamp, is_hardcore, hc_level_filter)
            filename = f"{prefix}ItemsEquipment.html"
            
        elif page_type.lower() == 'mercenary':
            print("Generating mercenary page...")
            html_content = generate_mercenary_page(all_characters, timestamp, is_hardcore, hc_level_filter)
            filename = f"{prefix}Mercenaries.html"
            
        elif page_type.lower() == 'funfacts':
            print("Generating fun facts page...")
            html_content = generate_fun_facts_page(all_characters, timestamp, is_hardcore, hc_level_filter)
            filename = f"{prefix}FunFacts.html"
            
        elif page_type.lower() == 'class':
            if not class_name:
                print("ERROR: Class name required for class page generation")
                print("Available classes: Barbarian, Druid, Amazon, Assassin, Necromancer, Paladin, Sorceress")
                return False
            print(f"Generating {class_name} class page...")
            result = generate_single_class_page(class_name, all_characters, timestamp, is_hardcore, hc_level_filter)
            if result:
                print(f"✓ {class_name} page saved as {result}")
                return True
            else:
                print(f"✗ Failed to generate {class_name} page")
                return False
            
        elif page_type.lower() == 'dataupdate':
            # Data update doesn't need character data - it fetches fresh data from API
            # Restore original working directory first since we changed it
            os.chdir(original_cwd)
            return update_data_and_generate_tracking_pages(snapshot_label=None)
            
        else:
            print(f"ERROR: Unknown page type '{page_type}'")
            print("Valid types: home, items, mercenary, funfacts, class, dataupdate")
            return False
        
        if html_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✓ Page saved as {filename}")
            return True
        else:
            print("✗ Failed to generate page content")
            return False
            
    except Exception as e:
        print(f"ERROR during page generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PoD analytics pages')
    parser.add_argument('--mode', choices=['sc', 'hc'], default='sc',
                      help='Game mode (sc=softcore, hc=hardcore)')
    parser.add_argument('--page', choices=['all', 'home', 'items', 'mercenary', 'funfacts', 'class', 'dataupdate'], 
                      default='all', help='Which page(s) to generate')
    parser.add_argument('--data', default='sc_ladder.json',
                      help='Path to character data JSON file (relative to root directory)')
    parser.add_argument('--class', dest='class_name',
                      help='Class name for class page generation (Barbarian, Druid, Amazon, Assassin, Necromancer, Paladin, Sorceress)')
    parser.add_argument('--hc-level-filter', type=int,
                      help='Minimum level filter for hardcore characters (e.g., 70)')
    parser.add_argument('--snapshot-label', 
                      help='Custom label for data snapshot (only used with --page dataupdate)')
    
    args = parser.parse_args()
    
    is_hardcore = args.mode == 'hc'
    hc_level_filter = args.hc_level_filter if is_hardcore else None
    
    # Auto-select the correct JSON file based on mode if using default
    data_file = args.data
    if args.data == 'sc_ladder.json' and is_hardcore:
        data_file = 'hc_ladder.json'
    
    if args.page == 'all':
        success = generate_all_pages(data_file, is_hardcore, hc_level_filter)
    elif args.page == 'dataupdate':
        success = update_data_and_generate_tracking_pages(args.snapshot_label)
    else:
        success = generate_single_page(args.page, data_file, is_hardcore, hc_level_filter, args.class_name)
    
    if success:
        print("\n✅ Generation completed successfully!")
    else:
        print("\n❌ Generation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()