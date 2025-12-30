"""
Comprehensive Charm Analysis and Page Generation Module
Analyzes all charms from ladder data and generates the HTML page
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
import re

from .charm_analysis_page import CharmAnalysisHTMLGenerator


def is_charm_active(item):
    """Check if charm is in active area (bottom 4 rows, y: 5-8)"""
    position = item.get("Position", {})
    y_pos = position.get("y", 0)
    return 5 <= y_pos <= 8


def categorize_charm_type(tag):
    """Determine if charm is small, large, or grand"""
    tag_lower = tag.lower()
    if "small charm" in tag_lower:
        return "small"
    elif "large charm" in tag_lower:
        return "large"
    elif "grand charm" in tag_lower:
        return "grand"
    return None


def is_unique_charm(item):
    """Check if this is a unique charm (Torch, Anni, Gheed's)"""
    quality_code = item.get("QualityCode", "")
    tag = item.get("Tag", "")
    return quality_code == "q_unique" and "charm" in tag.lower()


def is_skiller(item):
    """Check if item is a +1 skill tree grand charm"""
    if item.get("Tag", "") != "Grand Charm":
        return False
    
    props = item.get("PropertyList", [])
    for prop in props:
        # Look for +1 to skill tree properties
        # Some trees have "Skills" in the name, some don't (Curses, Traps, etc.)
        if "+1 to" in prop and "Only)" in prop:
            # Exclude item-specific bonuses like "+1 to All Skills"
            if "All Skills" not in prop:
                return True
    return False


def extract_numeric_value(prop_text, pattern=None):
    """Extract numeric value from property text"""
    if pattern:
        match = re.search(pattern, prop_text)
        if match:
            return int(match.group(1))
    else:
        match = re.search(r'[+\-]?(\d+)', prop_text)
        if match:
            return int(match.group(1))
    return None


def check_charm_space_availability(inventory):
    """
    Check if there's space for torch (2x4 large charm) and anni (1x1 small charm) in charm area
    Returns dict with has_torch_space and has_anni_space booleans
    """
    # Charm area is 10 wide (x: 0-9) and 4 tall (y: 5-8)
    # Create a 10x4 grid to track occupied spaces
    grid = [[False for _ in range(10)] for _ in range(4)]
    
    # Mark occupied spaces from existing charms
    for item in inventory:
        if not isinstance(item, dict):
            continue
        
        position = item.get("Position", {})
        y_pos = position.get("y", 0)
        x_pos = position.get("x", 0)
        
        # Only check charm area
        if 5 <= y_pos <= 8:
            # Map y coordinate to grid row (y=5 -> row 0, y=8 -> row 3)
            grid_y = y_pos - 5
            
            # Determine item size based on tag
            tag = item.get("Tag", "").lower()
            if "small charm" in tag:
                # Small charm: 1x1
                if grid_y < 4 and x_pos < 10:
                    grid[grid_y][x_pos] = True
            elif "large charm" in tag:
                # Large charm (torch): 2x4 (2 wide, 4 tall)
                for dy in range(4):
                    for dx in range(2):
                        if grid_y + dy < 4 and x_pos + dx < 10:
                            grid[grid_y + dy][x_pos + dx] = True
            elif "grand charm" in tag:
                # Grand charm: 1x1
                if grid_y < 4 and x_pos < 10:
                    grid[grid_y][x_pos] = True
    
    # Check if there's space for a torch (2x4)
    has_torch_space = False
    for start_y in range(1):  # Can only start at y=0 (needs 4 rows)
        for start_x in range(9):  # Can start at x=0 to x=8 (needs 2 columns)
            # Check if this 2x4 area is free
            is_free = True
            for dy in range(4):
                for dx in range(2):
                    if grid[start_y + dy][start_x + dx]:
                        is_free = False
                        break
                if not is_free:
                    break
            if is_free:
                has_torch_space = True
                break
        if has_torch_space:
            break
    
    # Check if there's space for an anni (1x1) and count total empty spaces
    has_anni_space = False
    empty_spaces = 0
    for y in range(4):
        for x in range(10):
            if not grid[y][x]:
                has_anni_space = True
                empty_spaces += 1
    
    return {
        'has_torch_space': has_torch_space,
        'has_anni_space': has_anni_space,
        'empty_spaces': empty_spaces
    }


def analyze_all_charms(characters):
    """Comprehensive charm analysis"""
    
    # Overview counters
    total_chars = len(characters)
    chars_with_charms = 0
    small_count = 0
    large_count = 0
    grand_count = 0
    total_charms = 0
    
    # Per-character tracking
    char_data = {}  # char_name -> {stats}
    
    # Charm tracking
    all_small_charms = []
    all_large_charms = []
    all_grand_charms = []
    all_skillers = []
    
    # Property counters
    small_properties = Counter()
    small_combos = Counter()
    large_properties = Counter()
    large_combos = Counter()
    grand_properties = Counter()
    grand_combos = Counter()
    
    # Skiller tracking
    skiller_by_class = Counter()
    skiller_by_tree = Counter()
    
    # Unique charm tracking
    gheeds_charms = []
    torch_charms = []
    anni_charms = []
    
    # Character tracking for torch/anni ownership
    chars_with_torch = set()
    chars_without_torch = set()
    chars_with_anni = set()
    chars_without_anni = set()
    chars_by_class_with_torch = defaultdict(set)
    chars_by_class_without_torch = defaultdict(set)
    chars_by_class_with_anni = defaultdict(set)
    chars_by_class_without_anni = defaultdict(set)
    
    # Track characters without torch/anni who have JUST enough space (likely sharing)
    # Torch is 2x4 = 8 spaces, so look for chars with torch space and <=10 empty spaces
    # Anni is 1x1 = 1 space, so look for chars with anni space and <=3 empty spaces
    chars_without_torch_with_just_enough_space = set()
    chars_without_anni_with_just_enough_space = set()
    empty_space_counts_without_torch = []
    empty_space_counts_without_anni = []
    
    # Track characters using a torch that doesn't match their class
    chars_with_wrong_class_torch = []  # List of dicts with char info and torch class
    
    # Rare finds
    high_poison_charms = []
    
    # Perfect charm tracking
    perfect_3_20_20_small = []  # 3 max dmg, 20 AR, 20 life
    perfect_20_16_small = []  # 20 life, 17 mana
    perfect_45_life_skillers = []  # Skillers with 45 life
    perfect_10_76_40_grand = []  # 10 max dmg, 76 AR, 40 life
    
    for char in characters:
        if not isinstance(char, dict):
            continue
        
        char_name = char.get("Name", "Unknown")
        char_class = char.get("Class", "Unknown")
        char_level = char.get("Stats", {}).get("Level", 0)
        
        # Initialize tracking for this character (will update if they have torch/anni)
        has_torch_this_char = False
        has_anni_this_char = False
        
        inventory = char.get("Inventory", [])
        if not isinstance(inventory, list):
            continue
        
        # Initialize character tracking
        if char_name not in char_data:
            char_data[char_name] = {
                'name': char_name,
                'class': char_class,
                'level': char_level,
                'total_life': 0,
                'total_mana': 0,
                'total_resists': 0,
                'total_max_dmg': 0,
                'total_ar': 0,
                'total_mf': 0,
                'fire_res': 0,
                'cold_res': 0,
                'light_res': 0,
                'poison_res': 0,
                'charm_count': 0
            }
        
        char_has_charms = False
        
        for item in inventory:
            if not isinstance(item, dict):
                continue
            
            tag = item.get("Tag", "")
            charm_type = categorize_charm_type(tag)
            props = item.get("PropertyList", [])
            
            # Track unique charms (Gheed's, Torch, Anni)
            if is_unique_charm(item) and is_charm_active(item):
                # Identify charm type by properties
                charm_data = {
                    'char_name': char_name,
                    'char_class': char_class,
                    'char_level': char_level,
                    'properties': props
                }
                
                # Gheed's Fortune (Grand Charm with gold find and vendor prices)
                has_gold_find = any("Extra Gold from Monsters" in p for p in props)
                has_vendor = any("Reduces all Vendor Prices" in p for p in props)
                if has_gold_find and has_vendor:
                    # Extract values
                    for prop in props:
                        if "Extra Gold from Monsters" in prop:
                            charm_data['gold_find'] = extract_numeric_value(prop)
                        elif "Reduces all Vendor Prices" in prop:
                            charm_data['vendor_discount'] = extract_numeric_value(prop)
                        elif "Better Chance of Getting Magic Items" in prop:
                            charm_data['mf'] = extract_numeric_value(prop)
                    gheeds_charms.append(charm_data)
                
                # Hellfire Torch (Large Charm with +3 to class skills)
                has_class_skills = any("+3 to" in p and "Skill Levels" in p for p in props)
                if has_class_skills:
                    torch_class = None
                    for prop in props:
                        if "+3 to" in prop and "Skill Levels" in prop:
                            charm_data['class_bonus'] = prop
                            # Extract the class name from the property
                            # Format is like "+3 to Barbarian Skill Levels"
                            torch_class = prop.replace("+3 to ", "").replace(" Skill Levels", "").strip()
                        elif "to all Attributes" in prop:
                            charm_data['attributes'] = extract_numeric_value(prop)
                        elif "All Resistances" in prop:
                            charm_data['all_res'] = extract_numeric_value(prop)
                        elif "Experience Gained" in prop:
                            charm_data['exp_gain'] = extract_numeric_value(prop)
                    
                    # Check if torch class matches character class
                    if torch_class and torch_class != char_class:
                        chars_with_wrong_class_torch.append({
                            'char_name': char_name,
                            'char_class': char_class,
                            'torch_class': torch_class,
                            'torch_stats': f"{charm_data.get('attributes', 0)}/{charm_data.get('all_res', 0)}"
                        })
                    
                    torch_charms.append(charm_data)
                    has_torch_this_char = True
                
                # Annihilus (Small Charm with +1 to all skills and experience)
                has_all_skills = any("+1 to All Skills" in p for p in props)
                has_exp = any("Experience Gained" in p for p in props)
                if has_all_skills and has_exp:
                    for prop in props:
                        if "to all Attributes" in prop:
                            charm_data['attributes'] = extract_numeric_value(prop)
                        elif "All Resistances" in prop:
                            charm_data['all_res'] = extract_numeric_value(prop)
                        elif "Experience Gained" in prop:
                            charm_data['exp_gain'] = extract_numeric_value(prop)
                    anni_charms.append(charm_data)
                    has_anni_this_char = True
                
                # Add resist totals to character
                for prop in props:
                    if "All Resistances" in prop:
                        val = extract_numeric_value(prop)
                        if val:
                            char_data[char_name]['total_resists'] += val * 4
                            char_data[char_name]['fire_res'] += val
                            char_data[char_name]['cold_res'] += val
                            char_data[char_name]['light_res'] += val
                            char_data[char_name]['poison_res'] += val
                continue
            
            if not charm_type or not is_charm_active(item):
                continue
            
            char_has_charms = True
            char_data[char_name]['charm_count'] += 1
            total_charms += 1
            
            # Process properties
            prop_combo = []
            for prop in props:
                # Track life
                if "to Life" in prop and "after each Kill" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_life'] += val
                
                # Track mana
                elif "to Mana" in prop and "after each Kill" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_mana'] += val
                
                # Track max damage
                elif "to Maximum Damage" in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_max_dmg'] += val
                
                # Track AR
                elif "to Attack Rating" in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_ar'] += val
                
                # Track MF
                elif "Better Chance of Getting Magic Items" in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_mf'] += val
                
                # Track resists
                elif "Fire Resist" in prop and "All Resistances" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['fire_res'] += val
                        char_data[char_name]['total_resists'] += val
                
                elif "Cold Resist" in prop and "All Resistances" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['cold_res'] += val
                        char_data[char_name]['total_resists'] += val
                
                elif "Lightning Resist" in prop and "All Resistances" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['light_res'] += val
                        char_data[char_name]['total_resists'] += val
                
                elif "Poison Resist" in prop and "All Resistances" not in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['poison_res'] += val
                        char_data[char_name]['total_resists'] += val
                
                elif "All Resistances" in prop:
                    val = extract_numeric_value(prop)
                    if val:
                        char_data[char_name]['total_resists'] += val * 4
                        char_data[char_name]['fire_res'] += val
                        char_data[char_name]['cold_res'] += val
                        char_data[char_name]['light_res'] += val
                        char_data[char_name]['poison_res'] += val
                
                # Check for high poison damage
                if "poison damage over" in prop.lower():
                    match = re.search(r'\+(\d+)\s+poison damage over', prop, re.IGNORECASE)
                    if match:
                        poison_dmg = int(match.group(1))
                        if poison_dmg > 200:
                            high_poison_charms.append({
                                'char': char_name,
                                'class': char_class,
                                'level': char_level,
                                'poison_dmg': poison_dmg,
                                'property': prop,
                                'charm_type': charm_type
                            })
            
            # Process by charm type
            if charm_type == "small":
                small_count += 1
                all_small_charms.append({'props': props, 'char': char_name})
                
                # Check for perfect 3-20-20 small charm
                has_3_max = any("+3 to Maximum Damage" in p for p in props)
                has_20_ar = any("+20 to Attack Rating" in p for p in props)
                has_20_life = any("+20 to Life" in p for p in props)
                if has_3_max and has_20_ar and has_20_life:
                    perfect_3_20_20_small.append({
                        'char': char_name,
                        'class': char_class,
                        'props': props
                    })
                
                # Check for perfect 20 life / 16 mana small charm
                has_20_life_2 = any("+20 to Life" in p for p in props)
                has_16_mana = any("+17 to Mana" in p for p in props)
                if has_20_life_2 and has_16_mana:
                    perfect_20_16_small.append({
                        'char': char_name,
                        'class': char_class,
                        'props': props
                    })
                
                for prop in props:
                    small_properties[prop] += 1
                    prop_combo.append(prop)
                # Only count as combo if 2+ properties
                if len(prop_combo) >= 2:
                    combo_key = " | ".join(sorted(prop_combo))
                    small_combos[combo_key] += 1
            
            elif charm_type == "large":
                large_count += 1
                all_large_charms.append({'props': props, 'char': char_name})
                for prop in props:
                    large_properties[prop] += 1
                    prop_combo.append(prop)
                # Only count as combo if 2+ properties
                if len(prop_combo) >= 2:
                    combo_key = " | ".join(sorted(prop_combo))
                    large_combos[combo_key] += 1
            
            elif charm_type == "grand":
                if is_skiller(item):
                    # Track skiller
                    for prop in props:
                        if "+1 to" in prop and "Only)" in prop and "All Skills" not in prop:
                            skiller_by_tree[prop] += 1
                            # Extract class from property
                            if "Amazon" in prop:
                                skiller_by_class["Amazon"] += 1
                            elif "Assassin" in prop:
                                skiller_by_class["Assassin"] += 1
                            elif "Barbarian" in prop:
                                skiller_by_class["Barbarian"] += 1
                            elif "Druid" in prop:
                                skiller_by_class["Druid"] += 1
                            elif "Necromancer" in prop:
                                skiller_by_class["Necromancer"] += 1
                            elif "Paladin" in prop:
                                skiller_by_class["Paladin"] += 1
                            elif "Sorceress" in prop:
                                skiller_by_class["Sorceress"] += 1
                    
                    # Check for perfect 45 life skiller
                    has_45_life = any("+45 to Life" in p for p in props)
                    if has_45_life:
                        perfect_45_life_skillers.append({
                            'char': char_name,
                            'class': char_class,
                            'props': props
                        })
                    
                    all_skillers.append({'props': props, 'char': char_name, 'class': char_class})
                else:
                    # Non-skiller grand charm
                    grand_count += 1
                    all_grand_charms.append({'props': props, 'char': char_name})
                    
                    # Check for perfect 10 max dmg, 76 AR, 40 life grand charm
                    has_10_max = any("+10 to Maximum Damage" in p for p in props)
                    has_76_ar = any("+76 to Attack Rating" in p for p in props)
                    has_40_life = any("+40 to Life" in p for p in props)
                    if has_10_max and has_76_ar and has_40_life:
                        perfect_10_76_40_grand.append({
                            'char': char_name,
                            'class': char_class,
                            'props': props
                        })
                    
                    for prop in props:
                        grand_properties[prop] += 1
                        prop_combo.append(prop)
                    # Only count as combo if 2+ properties
                    if len(prop_combo) >= 2:
                        combo_key = " | ".join(sorted(prop_combo))
                        grand_combos[combo_key] += 1
        
        if char_has_charms:
            chars_with_charms += 1
        
        # Check for available charm space
        inventory = char.get("Inventory", [])
        space_check = check_charm_space_availability(inventory)
        
        # Track torch/anni ownership for this character
        if has_torch_this_char:
            chars_with_torch.add(char_name)
            chars_by_class_with_torch[char_class].add(char_name)
        else:
            chars_without_torch.add(char_name)
            chars_by_class_without_torch[char_class].add(char_name)
            # Track empty space stats for chars without torch
            empty_count = space_check.get('empty_spaces', 0)
            empty_space_counts_without_torch.append(empty_count)
            # Check if they have JUST enough space for a torch (<=10 empty spaces)
            # Torch is 2x4 = 8 spaces, so <=10 suggests they're reserving that spot
            if space_check['has_torch_space'] and empty_count <= 10:
                chars_without_torch_with_just_enough_space.add(char_name)
        
        if has_anni_this_char:
            chars_with_anni.add(char_name)
            chars_by_class_with_anni[char_class].add(char_name)
        else:
            chars_without_anni.add(char_name)
            chars_by_class_without_anni[char_class].add(char_name)
            # Track empty space stats for chars without anni
            empty_count = space_check.get('empty_spaces', 0)
            empty_space_counts_without_anni.append(empty_count)
            # Check if they have JUST enough space for an anni (<=3 empty spaces)
            # Anni is 1x1 = 1 space, so <=3 suggests they're reserving that spot
            if space_check['has_anni_space'] and empty_count <= 3:
                chars_without_anni_with_just_enough_space.add(char_name)
    
    # Sort character lists by various metrics
    char_list = list(char_data.values())
    
    top_by_life = sorted(char_list, key=lambda x: x['total_life'], reverse=True)
    top_by_resists = sorted(char_list, key=lambda x: x['total_resists'], reverse=True)
    top_by_max_dmg = sorted(char_list, key=lambda x: x['total_max_dmg'], reverse=True)
    top_by_ar = sorted(char_list, key=lambda x: x['total_ar'], reverse=True)
    top_by_mf = sorted(char_list, key=lambda x: x['total_mf'], reverse=True)
    
    # Format interesting finds
    interesting_finds = []
    
    # High poison damage charms
    if high_poison_charms:
        high_poison_charms.sort(key=lambda x: x['poison_dmg'], reverse=True)
        highest = high_poison_charms[0]
        count_313 = sum(1 for c in high_poison_charms if c['poison_dmg'] == 313)
        if count_313 > 0:
            chars_with_313 = [c['char'] for c in high_poison_charms if c['poison_dmg'] == 313]
            interesting_finds.append(
                f"<strong>Highest Poison Damage Small Charm:</strong> +313 poison damage over 11 seconds "
                f"({count_313} found, used by {', '.join(chars_with_313[:3])})"
            )
    
    # Most common small charm combo
    if small_combos:
        most_common_combo, count = small_combos.most_common(1)[0]
        interesting_finds.append(
            f"<strong>Most Popular Small Charm Combo:</strong> {most_common_combo} - {count:,} in use"
        )
    
    # Character with most charms
    if char_list:
        most_charms_char = max(char_list, key=lambda x: x['charm_count'])
        if most_charms_char['charm_count'] > 0:
            interesting_finds.append(
                f"<strong>Most Charms on Single Character:</strong> {most_charms_char['name']} "
                f"({most_charms_char['class']}) with {most_charms_char['charm_count']} active charms"
            )
    
    # Most common property
    if small_properties:
        most_common_prop, prop_count = small_properties.most_common(1)[0]
        interesting_finds.append(
            f"<strong>Most Common Small Charm Property:</strong> \"{most_common_prop}\" "
            f"appears on {prop_count:,} small charms"
        )
    
    # Most popular skiller
    if skiller_by_tree:
        most_popular_skiller, skiller_count = skiller_by_tree.most_common(1)[0]
        interesting_finds.append(
            f"<strong>Most Popular Skiller:</strong> {most_popular_skiller} - {skiller_count:,} in use"
        )
    
    # Perfect charm counts
    if perfect_3_20_20_small:
        interesting_finds.append(
            f"<strong>Perfect 3/20/20 Small Charms:</strong> {len(perfect_3_20_20_small):,} found "
            f"(+3 max dmg, +20 AR, +20 life)"
        )
    
    if perfect_20_16_small:
        interesting_finds.append(
            f"<strong>Perfect 20/17 Small Charms:</strong> {len(perfect_20_16_small):,} found "
            f"(+20 life, +17 mana)"
        )
    
    if perfect_45_life_skillers:
        interesting_finds.append(
            f"<strong>Perfect 45 Life Skillers:</strong> {len(perfect_45_life_skillers):,} found"
        )
    
    if perfect_10_76_40_grand:
        interesting_finds.append(
            f"<strong>Perfect 10/76/40 Grand Charms:</strong> {len(perfect_10_76_40_grand):,} found "
            f"(+10 max dmg, +76 AR, +40 life)"
        )
    
    return {
        'overview': {
            'total_characters': total_chars,
            'chars_with_charms': chars_with_charms,
            'total_charms': total_charms,
            'small_count': small_count,
            'large_count': large_count,
            'grand_count': grand_count + len(all_skillers)
        },
        'top_characters': {
            'most_life': [
                {
                    'name': c['name'],
                    'class': c['class'],
                    'level': c['level'],
                    'total_life': c['total_life']
                }
                for c in top_by_life[:5] if c['total_life'] > 0
            ],
            'most_resists': [
                {
                    'name': c['name'],
                    'class': c['class'],
                    'level': c['level'],
                    'total_resists': c['total_resists']
                }
                for c in top_by_resists[:5] if c['total_resists'] > 0
            ],
            'most_max_damage': [
                {
                    'name': c['name'],
                    'class': c['class'],
                    'level': c['level'],
                    'total_max_dmg': c['total_max_dmg'],
                    'total_ar': c['total_ar']
                }
                for c in top_by_max_dmg[:5] if c['total_max_dmg'] > 0
            ],
            'most_ar': [
                {
                    'name': c['name'],
                    'class': c['class'],
                    'level': c['level'],
                    'total_ar': c['total_ar'],
                    'total_max_dmg': c['total_max_dmg']
                }
                for c in top_by_ar[:5] if c['total_ar'] > 0
            ],
            'most_mf': [
                {
                    'name': c['name'],
                    'class': c['class'],
                    'level': c['level'],
                    'total_mf': c['total_mf']
                }
                for c in top_by_mf[:5] if c['total_mf'] > 0
            ],
        },
        'skillers': {
            'total_skillers': sum(skiller_by_class.values()),
            'by_class': dict(skiller_by_class),
            'by_tree': skiller_by_tree.most_common(21)
        },
        'small_charms': {
            'total_count': small_count,
            'top_combos': small_combos.most_common(20),
            'top_properties': small_properties.most_common(20)
        },
        'large_charms': {
            'total_count': large_count,
            'top_combos': large_combos.most_common(15),
            'top_properties': large_properties.most_common(15)
        },
        'grand_charms': {
            'total_count': grand_count,
            'top_combos': grand_combos.most_common(20),
            'top_properties': grand_properties.most_common(20)
        },
        'unique_charms': {
            'gheeds': {
                'total_count': len(gheeds_charms),
                'charms': sorted(gheeds_charms, key=lambda x: x.get('mf', 0), reverse=True),
                'perfect_40mf_count': sum(1 for g in gheeds_charms if g.get('mf', 0) == 40)
            },
            'torches': {
                'total_count': len(torch_charms),
                'chars_with_torch': len(chars_with_torch),
                'chars_without_torch': len(chars_without_torch),
                'chars_without_torch_with_just_enough_space': len(chars_without_torch_with_just_enough_space),
                'avg_empty_spaces_without_torch': sum(empty_space_counts_without_torch) / len(empty_space_counts_without_torch) if empty_space_counts_without_torch else 0,
                'chars_with_wrong_class_torch': chars_with_wrong_class_torch,
                'by_class_with': {cls: len(names) for cls, names in chars_by_class_with_torch.items()},
                'by_class_without': {cls: len(names) for cls, names in chars_by_class_without_torch.items()},
                'perfect_20_20_count': sum(1 for t in torch_charms if t.get('attributes', 0) == 20 and t.get('all_res', 0) == 20),
                'avg_attributes': sum(t.get('attributes', 0) for t in torch_charms) / len(torch_charms) if torch_charms else 0,
                'avg_all_res': sum(t.get('all_res', 0) for t in torch_charms) / len(torch_charms) if torch_charms else 0,
                'charms': sorted(torch_charms, key=lambda x: x.get('all_res', 0), reverse=True),
                'by_class': Counter([c['class_bonus'] for c in torch_charms if 'class_bonus' in c])
            },
            'annis': {
                'total_count': len(anni_charms),
                'chars_with_anni': len(chars_with_anni),
                'chars_without_anni': len(chars_without_anni),
                'chars_without_anni_with_just_enough_space': len(chars_without_anni_with_just_enough_space),
                'avg_empty_spaces_without_anni': sum(empty_space_counts_without_anni) / len(empty_space_counts_without_anni) if empty_space_counts_without_anni else 0,
                'by_class_with': {cls: len(names) for cls, names in chars_by_class_with_anni.items()},
                'by_class_without': {cls: len(names) for cls, names in chars_by_class_without_anni.items()},
                'perfect_20_20_10_count': sum(1 for a in anni_charms if a.get('attributes', 0) == 20 and a.get('all_res', 0) == 20 and a.get('exp_gain', 0) == 10),
                'anti_perfect_10_10_5_count': sum(1 for a in anni_charms if a.get('attributes', 0) == 10 and a.get('all_res', 0) == 10 and a.get('exp_gain', 0) == 5),
                'avg_attributes': sum(a.get('attributes', 0) for a in anni_charms) / len(anni_charms) if anni_charms else 0,
                'avg_all_res': sum(a.get('all_res', 0) for a in anni_charms) / len(anni_charms) if anni_charms else 0,
                'avg_exp_gain': sum(a.get('exp_gain', 0) for a in anni_charms) / len(anni_charms) if anni_charms else 0,
                'charms': sorted(anni_charms, key=lambda x: x.get('all_res', 0), reverse=True)
            }
        },
        'rare_finds': {
            'interesting_finds': interesting_finds
        }
    }


def generate_charm_page(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """
    Generate charm analysis HTML page
    
    Args:
        all_characters: List of character data dictionaries
        timestamp: Timestamp string for the page footer
        is_hardcore: Whether this is hardcore ladder data
        hc_level_filter: Minimum level filter (not used currently, for consistency)
    
    Returns:
        HTML string for the charm analysis page
    """
    print(f"Analyzing charms for {'hardcore' if is_hardcore else 'softcore'} ladder...")
    
    # Analyze charms
    analysis_data = analyze_all_charms(all_characters)
    
    # Generate HTML
    ladder_type = 'hc' if is_hardcore else 'sc'
    html_content = CharmAnalysisHTMLGenerator.generate_full_charm_page(
        analysis_data,
        ladder_type,
        timestamp
    )
    
    return html_content
