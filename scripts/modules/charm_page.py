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
        if "+1 to" in prop and "Only)" in prop:
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
    
    # Rare finds
    high_poison_charms = []
    
    for char in characters:
        if not isinstance(char, dict):
            continue
        
        char_name = char.get("Name", "Unknown")
        char_class = char.get("Class", "Unknown")
        char_level = char.get("Stats", {}).get("Level", 0)
        
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
            
            # Check for Anni/Torch for resist totals
            if is_unique_charm(item):
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
                        if "+1 to" in prop and "Only)" in prop:
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
                    all_skillers.append({'props': props, 'char': char_name, 'class': char_class})
                else:
                    # Non-skiller grand charm
                    grand_count += 1
                    all_grand_charms.append({'props': props, 'char': char_name})
                    for prop in props:
                        grand_properties[prop] += 1
                        prop_combo.append(prop)
                    # Only count as combo if 2+ properties
                    if len(prop_combo) >= 2:
                        combo_key = " | ".join(sorted(prop_combo))
                        grand_combos[combo_key] += 1
        
        if char_has_charms:
            chars_with_charms += 1
    
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
            'by_tree': skiller_by_tree.most_common(20)
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
