"""
Items and Equipment Analysis Module
Handles all item-related analysis and HTML generation for the dedicated items page
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to access items_list.py
sys.path.append(str(Path(__file__).parent.parent.parent))

from collections import Counter, defaultdict
import json
from datetime import datetime
import statistics
import items_list
from .shared_utils import generate_standard_javascript


class ItemsEquipmentAnalyzer:
    def __init__(self, all_characters):
        self.all_characters = all_characters
        
    def analyze_all_items(self):
        """
        Main function to process all character data and extract item information
        Returns all item counters and user data needed for the items page
        """
        # Initialize counters
        runeword_counter = Counter()
        unique_counter = Counter() 
        set_counter = Counter()
        synth_counter = Counter()
        crafted_counters = defaultdict(Counter)
        magic_counters = defaultdict(Counter)
        rare_counters = defaultdict(Counter)
        
        # Initialize user tracking
        runeword_users = defaultdict(lambda: defaultdict(list))  # runeword_name -> base_item -> [characters]
        unique_users = defaultdict(list)
        set_users = defaultdict(list)
        synth_users = defaultdict(list)
        synth_sources = defaultdict(list)  # Track what items were used to synthesize other items
        crafted_users = defaultdict(lambda: defaultdict(list))
        magic_users = defaultdict(lambda: defaultdict(list))
        rare_users = defaultdict(lambda: defaultdict(list))
        
        # Initialize mercenary tracking
        merc_users = defaultdict(list)  # Track which characters' mercs use each item
        
        all_equipped_items = []
        item_summary_by_category = defaultdict(Counter)
        
        # Process each character
        for char_data in self.all_characters:
            if not isinstance(char_data, dict):
                continue
                
            char_info = {
                "name": char_data.get("Name", "Unknown"),
                "level": char_data.get("Stats", {}).get("Level", 0), 
                "class": char_data.get("Class", "Unknown")
            }
            
            # Process equipped items - note capital E for "Equipped"
            equipped_items = char_data.get("Equipped", [])
                
            self._process_character_items(
                equipped_items, char_info,
                runeword_counter, unique_counter, set_counter, synth_counter,
                crafted_counters, magic_counters, rare_counters,
                runeword_users, unique_users, set_users, synth_users, synth_sources,
                crafted_users, magic_users, rare_users,
                all_equipped_items, item_summary_by_category
            )
        
        # Generate socket analysis
        socketed_runes_html = self._generate_socketable_analysis()
        
        # Track character-only items BEFORE adding mercenary items
        char_used_runewords = {item[0] for item in runeword_counter.most_common()}
        char_used_uniques = {item[0] for item in unique_counter.most_common()}
        char_used_set_items = {item[0] for item in set_counter.most_common()}
        
        # Now analyze mercenaries and add their items to the counters
        self._analyze_mercenaries(runeword_counter, unique_counter, set_counter, merc_users)
        
        # Extract all items used by mercenaries (make case-insensitive for comparison)
        merc_used_items = {item.strip().lower() for item in merc_users.keys()}
        
        # Unused items analysis - based on CHARACTER usage only (not including mercs)
        try:
            all_the_items = items_list.all_the_items
            unused_runewords = {rw.strip().lower() for rw in all_the_items["all_the_runewords"]} - {rw.strip().lower() for rw in char_used_runewords}
            unused_uniques = {rw.strip().lower() for rw in all_the_items["all_the_uniques"]} - {rw.strip().lower() for rw in char_used_uniques}
            unused_set_items = {rw.strip().lower() for rw in all_the_items["all_the_sets"]} - {rw.strip().lower() for rw in char_used_set_items}
        except (AttributeError, KeyError):
            unused_runewords = unused_uniques = unused_set_items = set()
        
        # Generate weapon analysis
        weapon_analysis_html = self._generate_weapon_analysis(all_equipped_items)
        
        # Generate loadout analysis
        loadout_data = self._analyze_weapon_loadouts()
        
        # Generate build enabling items analysis
        build_enabling_data = self._analyze_build_enabling_items()
        
        return {
            'counters': {
                'runeword': runeword_counter,
                'unique': unique_counter,
                'set': set_counter,
                'synth': synth_counter,
                'crafted': crafted_counters,
                'magic': magic_counters,
                'rare': rare_counters
            },
            'users': {
                'runeword': runeword_users,
                'unique': unique_users,
                'set': set_users,
                'synth': synth_users,
                'crafted': crafted_users,
                'magic': magic_users,
                'rare': rare_users
            },
            'all_equipped_items': all_equipped_items,
            'item_summary_by_category': item_summary_by_category,
            'socketable_data': {
                'socketed_runes_html': socketed_runes_html
            },
            'unused_items': {
                'unused_runewords': unused_runewords,
                'unused_uniques': unused_uniques,
                'unused_set_items': unused_set_items,
                'merc_used_items': merc_used_items,
                'merc_users': merc_users
            },
            'synth_sources': synth_sources,
            'weapon_analysis_html': weapon_analysis_html,
            'loadout_data': loadout_data,
            'build_enabling_data': build_enabling_data
        }
    
    def _process_character_items(self, equipped_items, char_info, 
                                runeword_counter, unique_counter, set_counter, synth_counter,
                                crafted_counters, magic_counters, rare_counters,
                                runeword_users, unique_users, set_users, synth_users, synth_sources,
                                crafted_users, magic_users, rare_users,
                                all_equipped_items, item_summary_by_category):
        """Process items for a single character"""
        
        def categorize_worn_slot(worn_category, text_tag):
            """Categorize worn slots to match original implementation"""
            if worn_category in ["sweapon1", "weapon1", "sweapon2", "weapon2"]:
                if text_tag == "Arrows":
                    return "Arrows"
                elif text_tag == "Bolts":
                    return "Bolts"
                else:
                    return "Weapons and Shields"

            worn_category_map = {
                "ring1": "Rings", "ring2": "Rings",
                "body": "Armor",
                "gloves": "Gloves",
                "belt": "Belts",
                "helmet": "Helmets",
                "boots": "Boots",
                "amulet": "Amulets",
            }

            return worn_category_map.get(worn_category, "Other")
        
        # equipped_items is a list of item dictionaries
        for item_data in equipped_items:
            if not isinstance(item_data, dict):
                continue
                
            quality_code = item_data.get("QualityCode")
            item_title = item_data.get("Title", "Unknown")
            worn_slot = item_data.get("Worn", "unknown")
            text_tag = item_data.get("TextTag", "")
            
            # Use categorized worn slot for magic, rare, and crafted items
            categorized_slot = categorize_worn_slot(worn_slot, text_tag)
            
            # Track all equipped items
            all_equipped_items.append(item_data)
            
            # Categorize by slot and quality for item summary
            base_type = item_data.get("TextTag", "")
            if quality_code == "q_unique":
                summary_key = item_title
            elif quality_code == "q_set":
                summary_key = item_title
            elif quality_code == "q_runeword":
                summary_key = item_title
            elif quality_code == "q_crafted":
                summary_key = "Crafted"
            elif quality_code == "q_rare":
                summary_key = "Rare"
            elif quality_code == "q_magic":
                summary_key = "Magic"
            else:
                summary_key = f"Normal {base_type}"
            
            item_summary_by_category[categorized_slot][summary_key] += 1
            
            # Process by item quality code
            if quality_code == "q_runeword":
                base_item = item_data.get("Tag", "Unknown Base")
                runeword_counter[item_title] += 1
                runeword_users[item_title][base_item].append(char_info)
            
            elif quality_code == "q_unique":
                unique_counter[item_title] += 1
                unique_users[item_title].append(char_info)
                
            elif quality_code == "q_set":
                set_counter[item_title] += 1
                set_users[item_title].append(char_info)
                
            # Check for synth items (by quality code OR by tag/textTag containing "synth")
            if (quality_code == "q_synth" or 
                "synth" in item_data.get("Tag", "").lower() or 
                "synth" in item_data.get("TextTag", "").lower()):
                
                synth_counter[item_title] += 1
                synth_users[item_title].append(char_info)
                
                # Process SynthesizedFrom property to track source items
                synthesized_from = item_data.get("SynthesisedFrom", [])  # Note: could be "SynthesisedFrom" or "SynthesizedFrom"
                if not synthesized_from:
                    synthesized_from = item_data.get("SynthesizedFrom", [])
                    
                all_related_items = [item_title] + synthesized_from
                for source_item in all_related_items:
                    synth_sources[source_item].append({
                        "name": char_info["name"],
                        "class": char_info["class"], 
                        "level": char_info["level"],
                        "synthesized_item": item_title
                    })
                
            elif quality_code == "q_crafted":
                crafted_counters[categorized_slot][item_title] += 1
                crafted_users[categorized_slot][item_title].append(char_info)
                
            elif quality_code == "q_magic":
                magic_counters[categorized_slot][item_title] += 1
                magic_users[categorized_slot][item_title].append(char_info)
                
            elif quality_code == "q_rare":
                rare_counters[categorized_slot][item_title] += 1
                rare_users[categorized_slot][item_title].append(char_info)
    
    def _analyze_mercenaries(self, runeword_counter, unique_counter, set_counter, merc_users):
        """Analyze mercenary equipment and track which characters' mercs use which items"""
        for char_data in self.all_characters:
            if not isinstance(char_data, dict):
                continue
            
            mercenary_type = char_data.get("MercenaryType")
            if not mercenary_type:
                continue
            
            # Get character info for tracking
            char_info = {
                "Name": char_data.get("Name", "Unknown"),
                "Class": char_data.get("Class", "Unknown"),
                "Level": char_data.get("Stats", {}).get("Level", "N/A")
            }
            
            # Process mercenary equipped items
            for item in char_data.get("MercenaryEquipped", []):
                if not isinstance(item, dict):
                    continue
                
                title = item.get("Title", "Unknown")
                quality = item.get("QualityCode", "default")
                
                # Add mercenary items to global counters
                if quality == "q_runeword":
                    runeword_counter[title] += 1
                elif quality == "q_unique":
                    unique_counter[title] += 1
                elif quality == "q_set":
                    set_counter[title] += 1
                
                # Track which characters' mercenaries are using each item (case-insensitive)
                merc_users[title.strip().lower()].append(char_info)

    def analyze_socketable_items(self):
        """Analyze what items are being socketed"""
        # This would contain the socket_html logic from your original code
        # I'll implement this if you want to move it here
        pass
        
    def analyze_unused_items(self, used_items):
        """Compare used items against master lists to find unused items"""
        try:
            all_the_items = items_list.all_the_items
            
            used_runewords = {item.strip().lower() for item in used_items['runewords']}
            used_uniques = {item.strip().lower() for item in used_items['uniques']}
            used_set_items = {item.strip().lower() for item in used_items['sets']}
            
            unused_runewords = {rw.strip().lower() for rw in all_the_items["all_the_runewords"]} - used_runewords
            unused_uniques = {rw.strip().lower() for rw in all_the_items["all_the_uniques"]} - used_uniques
            unused_set_items = {rw.strip().lower() for rw in all_the_items["all_the_sets"]} - used_set_items
            
            return {
                'unused_runewords': unused_runewords,
                'unused_uniques': unused_uniques, 
                'unused_set_items': unused_set_items
            }
        except (AttributeError, KeyError) as e:
            print("Error analyzing unused items:", e)
            return {
                'unused_runewords': set(),
                'unused_uniques': set(),
                'unused_set_items': set()
            }

    def _generate_socketable_analysis(self):
        """Generate comprehensive socketable analysis matching the original format exactly"""
        just_socketed = []  # All socketed items
        just_socketed_excluding_runewords = []  # Socketed items excluding runewords
        just_socketed_runes = Counter()  # All runes (including in runewords)
        just_socketed_excluding_runewords_runes = Counter()  # Runes excluding runewords
        just_socketed_non_runes = Counter()  # Non-rune items
        just_socketed_magic = defaultdict(int)  # Magic jewels with default 0
        just_socketed_rare = defaultdict(int)  # Rare jewels with default 0
        just_socketed_facets = defaultdict(lambda: {"count": 0, "perfect": 0})  # Rainbow facets
        
        rune_names = {
            "El Rune", "Eld Rune", "Tir Rune", "Nef Rune", "Eth Rune", "Ith Rune", "Tal Rune", "Ral Rune", 
            "Ort Rune", "Thul Rune", "Amn Rune", "Sol Rune", "Shael Rune", "Dol Rune", "Hel Rune", "Io Rune", 
            "Lum Rune", "Ko Rune", "Fal Rune", "Lem Rune", "Pul Rune", "Um Rune", "Mal Rune", "Ist Rune",
            "Gul Rune", "Vex Rune", "Ohm Rune", "Lo Rune", "Sur Rune", "Ber Rune", "Jah Rune", "Cham Rune", "Zod Rune"
        }
        
        def extract_element(item):
            if item.get('Title') == 'Rainbow Facet':
                element_types = ["fire", "cold", "lightning", "poison", "physical", "magic"]
                for element in element_types:
                    for prop in item.get('PropertyList', []):
                        if element in prop.lower():
                            return element.capitalize()
            return item.get('Title', 'Unknown')
        
        # Process all characters
        for char in self.all_characters:
            for item in char.get('Equipped', []):
                if item.get('SocketCount', '0') != '0':
                    just_socketed.append(item)
                    
                    # Add items that aren't runewords to excluding list
                    if item.get('QualityCode') != 'q_runeword':
                        just_socketed_excluding_runewords.append(item)
                    
                    # Process each socketed item
                    for socketed_item in item.get('Sockets', []):
                        title = socketed_item.get('Title', '')
                        quality_code = socketed_item.get('QualityCode', '')
                        
                        if title in rune_names:
                            # Count all runes (including those in runewords)
                            just_socketed_runes[title] += 1
                            
                            # Count runes excluding runewords
                            if item.get('QualityCode') != 'q_runeword':
                                just_socketed_excluding_runewords_runes[title] += 1
                        else:
                            # Non-rune items (only count if not in runewords)
                            if item.get('QualityCode') != 'q_runeword':
                                if title == 'Rainbow Facet':
                                    element = extract_element(socketed_item)
                                    just_socketed_facets[element]["count"] += 1
                                    
                                    # Check for perfect facets - look for +5 and -5 (without % signs)
                                    properties = socketed_item.get('PropertyList', [])
                                    
                                    has_plus_five = any('+5' in prop for prop in properties)
                                    has_minus_five = any('-5' in prop for prop in properties)
                                    if has_plus_five and has_minus_five:
                                        just_socketed_facets[element]["perfect"] += 1
                                elif quality_code == "q_magic":
                                    # Count magic jewels and analyze properties
                                    just_socketed_magic['Misc. Magic Jewels'] += 1
                                    properties = socketed_item.get('PropertyList', [])
                                    prop_text = ' '.join(properties).lower()
                                    
                                    # Check for splash (look for "splash" in any property)
                                    if 'splash' in prop_text:
                                        just_socketed_magic['splash'] += 1
                                    # Check for attack speed (look for "increased attack speed")
                                    if 'increased attack speed' in prop_text:
                                        just_socketed_magic['attack speed'] += 1
                                    # Check for enhanced damage 
                                    if 'enhanced damage' in prop_text or 'damage to' in prop_text:
                                        just_socketed_magic['enhanced damage'] += 1
                                    # Combination checks
                                    if 'splash' in prop_text and 'increased attack speed' in prop_text:
                                        just_socketed_magic['iassplash'] += 1
                                    if 'increased attack speed' in prop_text and ('enhanced damage' in prop_text or 'damage to' in prop_text):
                                        just_socketed_magic['iased'] += 1
                                elif quality_code == "q_rare":
                                    just_socketed_rare['Misc. Rare Jewels'] += 1
                                    properties = socketed_item.get('PropertyList', [])
                                    prop_text = ' '.join(properties).lower()
                                    
                                    if 'splash' in prop_text:
                                        just_socketed_rare['splash'] += 1
                                    if 'enhanced damage' in prop_text or 'damage to' in prop_text:
                                        just_socketed_rare['enhanced damage'] += 1
                                else:
                                    just_socketed_non_runes[title] += 1
        
        # Format the HTML exactly like the original
        sorted_just_socketed_runes = '\n'.join(f"<li>{item}: {count}</li>" for item, count in just_socketed_runes.most_common())
        sorted_just_socketed_excluding_runewords_runes = '\n'.join(f"<li>{item}: {count}</li>" for item, count in just_socketed_excluding_runewords_runes.most_common())
        
        # Build other items list and sort by count in descending order
        all_other_items_with_counts = []
        
        # Non-rune items with their counts
        for item, count in just_socketed_non_runes.items():
            all_other_items_with_counts.append((count, f"{item}: {count}"))
        
        # Magic jewels with detailed breakdown
        if just_socketed_magic['Misc. Magic Jewels'] > 0:
            magic_count = just_socketed_magic['Misc. Magic Jewels']
            magic_detail = f"Misc. Magic Jewels: {magic_count} ({just_socketed_magic['splash']} include melee splash, {just_socketed_magic['attack speed']} include IAS, {just_socketed_magic['enhanced damage']} include ED; of those, there are {just_socketed_magic['iassplash']} IAS/Splash and {just_socketed_magic['iased']} IAS/ED)"
            all_other_items_with_counts.append((magic_count, magic_detail))
        
        # Rare jewels with breakdown  
        if just_socketed_rare['Misc. Rare Jewels'] > 0:
            rare_count = just_socketed_rare['Misc. Rare Jewels']
            rare_detail = f"Misc. Rare Jewels: {rare_count} ({just_socketed_rare['splash']} include melee splash, {just_socketed_rare['enhanced damage']} include ED)"
            all_other_items_with_counts.append((rare_count, rare_detail))
        
        # Rainbow facets
        for element, counts in just_socketed_facets.items():
            facet_count = counts['count']
            facet_text = f"Rainbow Facet ({element}): {facet_count} ({counts['perfect']} are perfect)"
            all_other_items_with_counts.append((facet_count, facet_text))
        
        # Sort by count descending, then format as HTML
        all_other_items_with_counts.sort(key=lambda x: x[0], reverse=True)
        all_other_items = [item_text for _, item_text in all_other_items_with_counts]
        
        other_items_html = '<ul>' + '\n'.join(f"<li>{item}</li>" for item in all_other_items) + '</ul>'
        
        html = f"""
        <h2 id="socketable-reporting">
            Socketable reporting
            <a href="#socketable-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>What are people putting in sockets</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <h2>Socketed Runes Count</h2>
            <h3>Includes Only Character Data, No Mercs</h3>
            <div id="special" class="container">
                <br>
                <div class="column">
                    <!-- Left Column -->
                    <h2>Most Common Runes <br>(Including Runewords)</h2>
                    <ul id="sorted_just_socketed_runes">
                        {sorted_just_socketed_runes}
                    </ul>
                </div>

                <!-- Right Column -->
                <div class="column">
                    <h2>Most Common Runes <br>(Excluding Runewords)</h2>
                    <ul id="sorted_just_socketed_excluding_runewords_runes">
                        {sorted_just_socketed_excluding_runewords_runes}
                    </ul>
                </div>
            </div>

            <div>
                <h2>Other Items Found in Sockets</h2>
                <h3>Includes Only Character Data, No Mercs</h3>
                {other_items_html}
            </div>
        </div>
        <br>"""
        
        return html

    def _generate_weapon_analysis(self, all_equipped_items):
        """Generate comprehensive weapon analysis"""
        try:
            from items_list import all_the_items as items_data
            two_handed_bases = set(items_data.get("two_handed_bases", []))
            bow_bases = set(items_data.get("bow_bows", []) + items_data.get("zon_bows", []) + items_data.get("cross_bows", []))
            one_or_two_hand = set(items_data.get("one_or_two_hand", []))
        except (ImportError, AttributeError):
            # Fallback if items_data not available
            two_handed_bases = {"Maul", "War Hammer", "Sledge Hammer", "Ogre Maul", "Thunder Maul"}
            bow_bases = {"Short Bow", "Long Bow", "Composite Bow"}
            one_or_two_hand = {"Battle Axe", "Broad Axe", "Large Axe"}
        
        two_handed_weapons = Counter()
        bow_weapons = Counter()
        
        for item in all_equipped_items:
            worn = item.get("Worn", "")
            if worn in ["weapon1", "weapon2", "sweapon1", "sweapon2"]:
                title = item.get("Title", "Unknown")
                tag = item.get("Tag", "").strip()
                quality = item.get("QualityCode", "")
                
                # Two-handed weapons
                if tag in two_handed_bases:
                    if quality == "q_runeword":
                        label = f"{title} ({tag})"
                    elif quality == "q_magic" and " of Teleportation" in title:
                        # Normalize all magic staves of teleportation
                        label = "Magic Staff of Teleportation"
                    else:
                        label = title
                    two_handed_weapons[label] += 1
                
                # Bows and crossbows
                elif tag in bow_bases:
                    if quality == "q_runeword":
                        label = f"{title} ({tag})"
                    else:
                        label = title
                    bow_weapons[label] += 1
        
        # Generate HTML for each section
        one_or_two_html = self._analyze_one_or_two_handed_usage(one_or_two_hand)
        two_handed_html = self._generate_two_handed_weapon_html(two_handed_weapons)
        bow_html = self._generate_bow_weapon_html(bow_weapons)
        
        return {
            'one_or_two_html': one_or_two_html,
            'two_handed_html': two_handed_html,
            'bow_html': bow_html
        }
    
    def _analyze_one_or_two_handed_usage(self, one_or_two_hand_list):
        """Analyze usage of one-or-two-handed weapons when used two-handed"""
        item_data = defaultdict(lambda: {"total": 0, "bases": defaultdict(list)})

        for char in self.all_characters:
            equipped = {item["Worn"]: item for item in char.get("Equipped", [])}

            for slot1, slot2 in [("weapon1", "weapon2"), ("sweapon1", "sweapon2")]:
                weapon = equipped.get(slot1)
                offhand = equipped.get(slot2)

                if not weapon or offhand:
                    continue  # Either missing weapon or dual wielding

                base = weapon.get("Tag", "")
                if base not in one_or_two_hand_list:
                    continue

                title = weapon.get("Title", "Unknown")
                char_info = {
                    "name": char.get("Name", "Unknown"),
                    "class": char.get("Class", "Unknown"),
                }

                item_data[title]["total"] += 1
                item_data[title]["bases"][base].append(char_info)

        # Sort by total descending
        sorted_items = sorted(item_data.items(), key=lambda x: -x[1]["total"])

        html_output = [
            "<h2>One or Two-Handed Items (Used Two-Handed)</h2>",
            "<div style='column-count: 2; column-gap: 2em;'>",
            "<ul style='margin: 0; padding: 0;'>"
        ]

        for title, data in sorted_items:
            html_output.append(f"<li><strong>{title}: {data['total']}</strong>")

            for base, chars in sorted(data["bases"].items(), key=lambda x: (-len(x[1]), x[0])):
                base_name = base or "(unknown base)"
                base_id = self._slugify(f"{title}-{base_name}")

                html_output.append(f"""
                    <ul style="margin: 0;">
                        <li style="padding-left: 1.5em">
                            <button class="collapsible">
                                <img src="icons/open-grey.png" alt="Expand" class="icon-small open-icon hidden">
                                <img src="icons/closed-grey.png" alt="Collapse" class="icon-small close-icon">
                                <strong>
                                    <a href="#item-{base_id}" class="anchor-link">
                                        {base_name}: {len(chars)}
                                    </a>
                                </strong>
                            </button>
                            <div class="content" id="item-{base_id}">
                                {''.join(f'''
                                    <div class="character-info">
                                        <div class="character-link">
                                            <a href="https://beta.pathofdiablo.com/armory?name={c["name"]}" target="_blank">
                                                {c["name"]}
                                            </a>
                                        </div>
                                        <div>{c["class"]}</div>
                                        <div class="hover-trigger" data-character-name="{c["name"]}"></div>
                                    </div>
                                    <div class="character">
                                        <div class="popup hidden"></div>
                                    </div>
                                ''' for c in chars)}
                            </div>
                        </li>
                    </ul>
                """)

            html_output.append("</li>")

        html_output.append("</ul></div>")
        return "\n".join(html_output)
    
    def _generate_two_handed_weapon_html(self, two_handed_counter):
        """Generate HTML for two-handed weapons analysis"""
        # First, aggregate base breakdowns for runewords
        aggregated_data = defaultdict(lambda: {"total": 0, "bases": Counter()})
        
        for label, count in two_handed_counter.items():
            if " (" in label and label.endswith(")"):
                # Runeword with base, e.g., "Memory (Cedar Staff)"
                name, base = label[:-1].split(" (", 1)
                aggregated_data[name]["total"] += count
                aggregated_data[name]["bases"][base] += count
            else:
                # Normal item
                aggregated_data[label]["total"] += count

        # Sort aggregated data by total count, descending
        sorted_items = sorted(aggregated_data.items(), key=lambda x: x[1]["total"], reverse=True)

        # Generate HTML
        html_output = [
            "<h2>Most Common Melee Weapons That Require two Hands</h2>",
            "<div style='column-count: 2; column-gap: 2em;'>",
            "<ul style='margin: 0; padding: 0;'>"
        ]

        for name, data in sorted_items:
            total = data["total"]
            bases = data["bases"]

            if bases:
                html_output.append(f"<li><strong>{name}: {total}</strong><ul>")
                for base_name, base_count in bases.most_common():
                    html_output.append(f"<li class='base-item'>{base_name}: {base_count}</li>")
                html_output.append("</ul></li>")
            else:
                html_output.append(f"<li>{name}: {total}</li>")

        html_output.append("</ul></div>")
        return "\n".join(html_output)

    def _generate_bow_weapon_html(self, bow_counter):
        """Generate HTML for bow and crossbow analysis"""
        # First, aggregate base breakdowns for runewords
        aggregated_data = defaultdict(lambda: {"total": 0, "bases": Counter()})
        
        for label, count in bow_counter.items():
            if " (" in label and label.endswith(")"):
                # Runeword with base, e.g., "Brand (Grand Matron Bow)"
                name, base = label[:-1].split(" (", 1)
                aggregated_data[name]["total"] += count
                aggregated_data[name]["bases"][base] += count
            else:
                # Normal item
                aggregated_data[label]["total"] += count

        # Sort aggregated data by total count, descending
        sorted_items = sorted(aggregated_data.items(), key=lambda x: x[1]["total"], reverse=True)

        # Generate HTML
        html_output = [
            "<h2>Most Commonly Seen Bows and Crossbows</h2>",
            "<div style='column-count: 2; column-gap: 2em;'>",
            "<ul style='margin: 0; padding: 0;'>"
        ]

        for name, data in sorted_items:
            total = data["total"]
            bases = data["bases"]

            if bases:
                html_output.append(f"<li><strong>{name}: {total}</strong><ul>")
                for base_name, base_count in bases.most_common():
                    html_output.append(f"<li class='base-item'>{base_name}: {base_count}</li>")
                html_output.append("</ul></li>")
            else:
                html_output.append(f"<li>{name}: {total}</li>")

        html_output.append("</ul></div>")
        return "\n".join(html_output)
    
    def _slugify(self, name):
        """Convert a name to a URL-friendly slug"""
        return name.lower().replace(" ", "-").replace("'", "").replace('"', "")
    
    def _analyze_weapon_loadouts(self):
        """Analyze weapon loadouts for characters"""
        try:
            from items_list import all_the_items as items_data
            bow_bases = {b.lower() for b in items_data.get("zon_bows", []) + items_data.get("bow_bows", [])}
            xbow_bases = {x.lower() for x in items_data.get("cross_bows", [])}
            one_or_two_hand = set(items_data.get("one_or_two_hand", []))
            two_handed_bases = set(items_data.get("two_handed_bases", []))
        except (ImportError, AttributeError):
            # Fallback if items_data not available
            bow_bases = {"short bow", "long bow", "composite bow"}
            xbow_bases = {"light crossbow", "crossbow", "heavy crossbow"}
            one_or_two_hand = {"battle axe", "broad axe", "large axe"}
            two_handed_bases = {"maul", "war hammer", "sledge hammer"}

        loadout_counts = defaultdict(int)
        total_loadouts = 0

        def is_weapon(item):
            return isinstance(item, dict) and "DamageMinimum" in item and "DamageMaximum" in item

        def is_shield(item):
            return isinstance(item, dict) and "Block" in item and "Defense" in item

        def classify_loadout(w1, w2):
            if not w1 and not w2:
                return None  # Skip

            tag1 = w1.get("Tag", "").lower() if w1 else ""
            tag2 = w2.get("Tag", "").lower() if w2 else ""

            tags = {tag1, tag2}

            # Bow + Arrows
            if (tag1 in bow_bases or tag2 in bow_bases) and any("arrow" in t for t in tags):
                return "Bow + Arrows"
            if tag1 in bow_bases or tag2 in bow_bases:
                return "Bow Only (Missing Arrows)"
            if any("arrow" in t for t in tags):
                return "Arrows Only (Missing Bow)"

            # Crossbow + Bolts
            if (tag1 in xbow_bases or tag2 in xbow_bases) and any("bolt" in t for t in tags):
                return "Crossbow + Bolts"
            if tag1 in xbow_bases or tag2 in xbow_bases:
                return "Crossbow Only (Missing Bolts)"
            if any("bolt" in t for t in tags):
                return "Bolts Only (Missing Crossbow)"

            # Two-handed melee weapon (solo)
            if w1 and not w2 and is_weapon(w1):
                base = w1.get("Tag", "")
                if base in one_or_two_hand or base in two_handed_bases:
                    return "A Single Two-Handed Weapon"

            if w2 and not w1 and is_weapon(w2):
                base = w2.get("Tag", "")
                if base in one_or_two_hand or base in two_handed_bases:
                    return "A Single Two-Handed Weapon"

            # Weapon + Shield
            if (is_weapon(w1) and is_shield(w2)) or (is_shield(w1) and is_weapon(w2)):
                return "Weapon + Shield"

            # Dual wield
            if is_weapon(w1) and is_weapon(w2):
                return "Dual Wield"

            # Single One-Handed Weapon
            if (w1 and not w2 and is_weapon(w1)) or (w2 and not w1 and is_weapon(w2)):
                base = (w1 or w2).get("Tag", "")
                if base not in one_or_two_hand and base not in two_handed_bases:
                    return "Single One-Handed Weapon (Missing Shield or Second Weapon)"

            # Shield only
            if is_shield(w1) and not w2:
                return "Shield Only (Missing Weapon)"
            if is_shield(w2) and not w1:
                return "Shield Only (Missing Weapon)"

            # Two-handed
            tag = tag1 or tag2
            if tag in two_handed_bases:
                return "A Single Two-Handed Weapon"

            return "Other"

        empty_loadout_count = 0
        partially_empty_set_count = 0
        
        for char in self.all_characters:
            equipped = {item["Worn"]: item for item in char.get("Equipped", []) if isinstance(item, dict)}
            # Check if weapon1/weapon2 or sweapon1/sweapon2 are both missing
            has_set1 = equipped.get("weapon1") or equipped.get("weapon2")
            has_set2 = equipped.get("sweapon1") or equipped.get("sweapon2")

            if not has_set1 and not has_set2:
                empty_loadout_count += 1
            elif not has_set1 or not has_set2:
                partially_empty_set_count += 1

            sets_categorized = 0

            for set1, set2 in [("weapon1", "weapon2"), ("sweapon1", "sweapon2")]:
                w1 = equipped.get(set1)
                w2 = equipped.get(set2)

                category = classify_loadout(w1, w2)
                if category:
                    loadout_counts[category] += 1
                    total_loadouts += 1
                    sets_categorized += 1

            if sets_categorized == 0:
                empty_loadout_count += 1

        return {
            'loadout_counts': loadout_counts,
            'total_loadouts': total_loadouts,
            'empty_loadout_count': empty_loadout_count,
            'partially_empty_set_count': partially_empty_set_count
        }

    def _analyze_build_enabling_items(self):
        """Analyze items that enable specific builds based on item names and properties"""
        build_enabling_data = defaultdict(list)
        
        # Define build enabling criteria
        build_criteria = {
            "Ball Lightning Build": {
                "items": ["Ondal's Wisdom"],
                "properties": ["to Ball Lightning"]  # Will match "+20 to Ball Lightning", etc.
            },
            "Magic Arrow Build": {
                "items": [],
                "properties": ["to Magic Arrow"] #, "Fires Magic Arrows"]  # Cover both property types
            },
            "Beast Werebear Build": {
                "items": ["Beast"],
                "properties": []
            },
            "Templar's Charge Build": {
                "items": ["Templar's Might"],
                "properties": []
            },
            "Dragonscale Hydra Build": {
                "items": ["Dragonscale"],
                "properties": []
            }
        }
        
        # Process each character
        for char in self.all_characters:
            if not isinstance(char, dict):
                continue
                
            char_info = {
                "name": char.get("Name", "Unknown"),
                "level": char.get("Stats", {}).get("Level", 0),
                "class": char.get("Class", "Unknown")
            }
            
            equipped_items = char.get("Equipped", [])
            character_builds = set()  # Track which builds this character enables
            
            # Check each equipped item
            for item in equipped_items:
                if not isinstance(item, dict):
                    continue
                    
                item_title = item.get("Title", "")
                item_properties = item.get("PropertyList", [])
                
                # Check each build criteria
                for build_name, criteria in build_criteria.items():
                    build_enabled = False
                    enabling_reason = ""
                    
                    # Check if item name matches
                    if item_title in criteria["items"]:
                        build_enabled = True
                        enabling_reason = f"wearing {item_title}"
                    
                    # Check if item has enabling properties
                    if not build_enabled and criteria["properties"]:
                        for prop in item_properties:
                            if isinstance(prop, str):
                                for enabling_prop in criteria["properties"]:
                                    if enabling_prop in prop:
                                        build_enabled = True
                                        enabling_reason = f"item with property '{prop}' ({item_title})"
                                        break
                                if build_enabled:
                                    break
                    
                    # Add character to build if enabled and not already added
                    if build_enabled and build_name not in character_builds:
                        character_builds.add(build_name)
                        char_with_reason = char_info.copy()
                        char_with_reason["enabling_reason"] = enabling_reason
                        build_enabling_data[build_name].append(char_with_reason)
        
        return build_enabling_data


class ItemsEquipmentHTMLGenerator:
    """Generates HTML for the items and equipment page"""
    
    @staticmethod
    def generate_full_items_page(analysis_data, timestamp):
        """Generate the complete HTML for the items and equipment page"""
        
        # Get data from analysis
        counters = analysis_data['counters']
        users = analysis_data['users']
        
        # Generate individual sections
        runewords_html = ItemsEquipmentHTMLGenerator._generate_runewords_section(
            counters['runeword'], users['runeword']
        )
        
        uniques_html = ItemsEquipmentHTMLGenerator._generate_uniques_section(
            counters['unique'], users['unique']
        )
        
        sets_html = ItemsEquipmentHTMLGenerator._generate_sets_section(
            counters['set'], users['set']
        )
        
        # Generate other sections...
        crafted_html = ItemsEquipmentHTMLGenerator._generate_crafted_section(
            counters['crafted'], users['crafted']
        )
        
        magic_html = ItemsEquipmentHTMLGenerator._generate_magic_section(
            counters['magic'], users['magic']
        )
        
        rare_html = ItemsEquipmentHTMLGenerator._generate_rare_section(
            counters['rare'], users['rare']
        )
        
        # Generate additional sections
        synth_html = ItemsEquipmentHTMLGenerator._generate_synth_section(
            counters['synth'], users['synth'], analysis_data.get('synth_sources', {})
        )
        
        socketable_html = analysis_data.get('socketable_data', {}).get('socketed_runes_html', '')
        
        unused_items_html = ItemsEquipmentHTMLGenerator._generate_unused_items_section(
            analysis_data.get('unused_items', {})
        )
        
        weapon_analysis_data = analysis_data.get('weapon_analysis_html', {})
        weapon_analysis_html = ItemsEquipmentHTMLGenerator._generate_weapon_analysis_section(weapon_analysis_data)
        
        item_summary_html = ItemsEquipmentHTMLGenerator._generate_item_summary_section(
            analysis_data.get('item_summary_by_category', {})
        )
        
        # Generate loadout sections
        loadout_data = analysis_data.get('loadout_data', {})
        loadout_intro_html = ItemsEquipmentHTMLGenerator._generate_loadout_intro_section(loadout_data)
        incomplete_loadouts_html = ItemsEquipmentHTMLGenerator._generate_incomplete_loadouts_section(loadout_data)
        
        # Generate build enabling items section
        build_enabling_html = ItemsEquipmentHTMLGenerator._generate_build_enabling_section(
            analysis_data.get('build_enabling_data', {})
        )
        
        # Combine into full page
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PoD Items & Equipment Analysis</title>
            <link rel="shortcut icon" type="image/x-icon" href="icons/pod.ico">
            <link rel="stylesheet" type="text/css" href="./css/test-css.css">
        </head>
        <body class="special-background">
            <div class="is-clipped">
                <div id="navbar-placeholder"></div>
                <script>
                fetch("templates/navbar.html")
                    .then(res => res.text())
                    .then(html => {{
                    document.getElementById("navbar-placeholder").innerHTML = html;
                    }});
                </script>

                <div class="hamburger" onclick="toggleMenu()">
                    <div class="line"></div>
                    <div class="line"></div>
                    <div class="line"></div>
                </div>
                
                <div class="top-buttons">
                    <a href="Home" class="top-button home-button" onclick="setActive('Home')"></a>
                    <a href="#" id="SC_HC" class="top-button"> </a>
                    <a href="Amazon" id="Amazon" class="top-button amazon-button"></a>
                    <a href="Assassin" id="Assassin" class="top-button assassin-button"></a>
                    <a href="Barbarian" id="Barbarian" class="top-button barbarian-button"></a>
                    <a href="Druid" id="Druid" class="top-button druid-button"></a>
                    <a href="Necromancer" id="Necromancer" class="top-button necromancer-button"></a>
                    <a href="Paladin" id="Paladin" class="top-button paladin-button"></a>
                    <a href="Sorceress" id="Sorceress" class="top-button sorceress-button"></a>
                    <a href="https://github.com/qordwasalreadytaken/pod-stats/blob/main/README.md" class="top-button about-button" target="_blank"></a>
                </div>

                <div class="main page-intro">
                    <h1>PoD ITEMS & EQUIPMENT ANALYSIS</h1>
                    <h2>Comprehensive analysis of item usage patterns from ladder characters</h2>
                    
                    {loadout_intro_html}
                    
                    <hr>
                    
                    {runewords_html}
                    
                    <hr>
                    
                    {uniques_html}
                    
                    <hr>
                    
                    {sets_html}
                    
                    <hr>
                    
                    {crafted_html}
                    
                    <hr>
                    
                    {magic_html}
                    
                    <hr>
                    
                    {rare_html}
                    
                    <hr>
                    
                    {synth_html}
                    
                    <hr>
                    
                    {socketable_html}
                    
                    <hr>
                    
                    {unused_items_html}
                    
                    <hr>
                    
                    {weapon_analysis_html}
                    
                    <hr>
                    
                    {build_enabling_html}
                    
                    <hr>
                    
                    {item_summary_html}
                    
                    <hr>
                    
                    {incomplete_loadouts_html}
                    
                    <!-- Add other sections here -->
                    
                </div>
                
                <div class="footer">
                    <p>PoD data current as of {timestamp}</p>
                </div>
            </div>
            
            {generate_standard_javascript()}
        </body>
        </html>
        """
        
        return html_content
    
    @staticmethod
    def _generate_runewords_section(runeword_counter, runeword_users):
        """Generate HTML for runewords section"""
        most_common = runeword_counter.most_common(10)
        least_common = runeword_counter.most_common()[:-11:-1]
        all_runewords = runeword_counter.most_common(150)
        
        most_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in most_common)
        least_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in least_common)
        all_runewords_html = ItemsEquipmentHTMLGenerator._generate_all_list_items(all_runewords, runeword_users)
        
        return f"""
        <h2 id="runeword-usage">
            Runeword Usage Analysis
            <a href="#runeword-usage" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible runewords-button">
            <img src="icons/Runewords_click.png" alt="Runewords Open" class="icon open-icon hidden">
            <img src="icons/Runewords.png" alt="Runewords Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="runewords" class="container">
                <div class="column">
                    <h3>Most Used Runewords:</h3>
                    <ul>{most_popular_html}</ul>
                </div>
                <div class="column">
                    <h3>Least Used Runewords:</h3>
                    <ul>{least_popular_html}</ul>
                </div>
            </div>

            <button type="button" class="collapsible small-collapsible">
                <img src="icons/open.png" alt="All Runewords Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Runewords Close" class="icon-small close-icon">
                <strong>ALL Runewords</strong>
            </button>

            <div class="content" style="display: none;">
                <div id="allrunewords">
                    {all_runewords_html}
                </div>
            </div>
        </div>
        """
    
    @staticmethod  
    def _generate_uniques_section(unique_counter, unique_users):
        """Generate HTML for uniques section"""
        # Similar structure to runewords
        most_common = unique_counter.most_common(10)
        least_common = unique_counter.most_common()[:-11:-1]
        all_uniques = unique_counter.most_common(450)
        
        most_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in most_common)
        least_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in least_common)
        all_uniques_html = ItemsEquipmentHTMLGenerator._generate_all_list_items(all_uniques, unique_users)
        
        return f"""
        <h2 id="unique-usage">
            Unique Item Usage Analysis
            <a href="#unique-usage" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible uniques-button">
            <img src="icons/Uniques_click.png" alt="Uniques Open" class="icon open-icon hidden">
            <img src="icons/Uniques.png" alt="Uniques Close" class="icon close-icon">
        </button>    
        <div class="content" style="display: none;">   
            <div id="uniques" class="container">
                <div class="column">
                    <h3>Most Used Uniques:</h3>
                    <ul>{most_popular_html}</ul>
                </div>
                <div class="column">
                    <h3>Least Used Uniques:</h3>
                    <ul>{least_popular_html}</ul>
                </div>
            </div>
            
            <button type="button" class="collapsible small-collapsible">
                <img src="icons/open.png" alt="All Uniques Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Uniques Close" class="icon-small close-icon">
                <strong>ALL Uniques</strong>
            </button>

            <div class="content" style="display: none;">
                <div id="alluniques">
                    {all_uniques_html}
                </div>
            </div>
        </div>
        """

    @staticmethod
    def _generate_sets_section(set_counter, set_users):
        """Generate HTML for set items section"""
        # Similar to uniques and runewords
        most_common = set_counter.most_common(10)
        least_common = set_counter.most_common()[:-11:-1] 
        all_sets = set_counter.most_common(150)
        
        most_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in most_common)
        least_popular_html = ''.join(f'<li>{name}: {count}</li>' for name, count in least_common)
        all_sets_html = ItemsEquipmentHTMLGenerator._generate_all_list_items(all_sets, set_users)
        
        return f"""
        <h2 id="set-usage">
            Set Item Usage Analysis
            <a href="#set-usage" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Sets_click.png" alt="Sets Open" class="icon open-icon hidden">
            <img src="icons/Sets.png" alt="Sets Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="sets" class="container">
                <div class="column">
                    <h3>Most Used Set Items:</h3>
                    <ul>{most_popular_html}</ul>
                </div>
                <div class="column">
                    <h3>Least Used Set Items:</h3>
                    <ul>{least_popular_html}</ul>
                </div>
            </div>
            
            <button type="button" class="collapsible small-collapsible">
                <img src="icons/open.png" alt="All Set Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Set Close" class="icon-small close-icon">
                <strong>ALL Set Items</strong>
            </button>

            <div class="content" style="display: none;">
                <div id="allset">
                    {all_sets_html}
                </div>
            </div>
        </div>
        """

    @staticmethod
    def _generate_crafted_section(crafted_counters, crafted_users):
        """Generate HTML for crafted items section"""
        craft_user_count = sum(len(users) for users in crafted_users.values())
        
        items_html = ""
        for worn_category, counter in crafted_counters.items():
            if not counter:
                continue
                
            # Collect all characters for this category (across all specific items)
            all_category_users = []
            for item_name in counter.keys():
                users_for_item = crafted_users.get(worn_category, {}).get(item_name, [])
                all_category_users.extend(users_for_item)
            
            # Generate character list HTML for all users in this category
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]}</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in all_category_users
            )
            
            # Create collapsible category section
            category_slug = worn_category.lower().replace(' ', '-')
            items_html += f"""
            <button class="collapsible">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Crafted {worn_category.title()} ({sum(counter.values())} items, {len(all_category_users)} users)</strong>
            </button>
            <div class="content" style="display: none;" id="crafted-{category_slug}">
                {character_list_html if all_category_users else "<p>No character data available.</p>"}
            </div>
            """
        
        return f"""
        <h2 id="craft-reporting">
            Crafted Items Analysis
            <a href="#craft-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>        
        <h3>{craft_user_count} Characters with crafted items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Crafted Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Crafted Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="crafted">
                {items_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_magic_section(magic_counters, magic_users):
        """Generate HTML for magic items section"""
        magic_user_count = sum(len(users) for users in magic_users.values())
        
        items_html = ""
        for worn_category, counter in magic_counters.items():
            if not counter:
                continue
                
            # Collect all characters for this category (across all specific items)
            all_category_users = []
            for item_name in counter.keys():
                users_for_item = magic_users.get(worn_category, {}).get(item_name, [])
                all_category_users.extend(users_for_item)
            
            # Generate character list HTML for all users in this category
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]}</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in all_category_users
            )
            
            # Create collapsible category section
            category_slug = worn_category.lower().replace(' ', '-')
            items_html += f"""
            <button class="collapsible">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Magic {worn_category.title()} ({sum(counter.values())} items, {len(all_category_users)} users)</strong>
            </button>
            <div class="content" style="display: none;" id="magic-{category_slug}">
                {character_list_html if all_category_users else "<p>No character data available.</p>"}
            </div>
            """
        
        return f"""
        <h2 id="magic-reporting">
            Magic Items Analysis
            <a href="#magic-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>        
        <h3>{magic_user_count} Characters with magic items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Magic Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Magic Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="magic">
                {items_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_rare_section(rare_counters, rare_users):
        """Generate HTML for rare items section"""
        rare_user_count = sum(len(users) for users in rare_users.values())
        
        items_html = ""
        for worn_category, counter in rare_counters.items():
            if not counter:
                continue
                
            # Collect all characters for this category (across all specific items)
            all_category_users = []
            for item_name in counter.keys():
                users_for_item = rare_users.get(worn_category, {}).get(item_name, [])
                all_category_users.extend(users_for_item)
            
            # Generate character list HTML for all users in this category
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]}</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in all_category_users
            )
            
            # Create collapsible category section
            category_slug = worn_category.lower().replace(' ', '-')
            items_html += f"""
            <button class="collapsible">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Rare {worn_category.title()} ({sum(counter.values())} items, {len(all_category_users)} users)</strong>
            </button>
            <div class="content" style="display: none;" id="rare-{category_slug}">
                {character_list_html if all_category_users else "<p>No character data available.</p>"}
            </div>
            """
        
        return f"""
        <h2 id="rare-reporting">
            Rare Items Analysis
            <a href="#rare-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>        
        <h3>{rare_user_count} Characters with rare items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Rare Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Rare Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="rare">
                {items_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_synth_section(synth_counter, synth_users, synth_sources):
        """Generate HTML for synthesized items sections exactly like the original"""
        synth_user_count = sum(len(users) for users in synth_users.values()) if synth_users else 0
        synth_source_user_count = sum(len(users) for users in synth_sources.values()) if synth_sources else 0
        
        # Generate synth items list (all_synth equivalent)
        all_synth_html = ""
        for item, count in sorted(synth_counter.items(), key=lambda x: (-x[1], x[0])):
            users = synth_users.get(item, [])
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]}</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in users
            )
            
            item_slug = item.lower().replace(' ', '-').replace("'", "").replace('"', "")
            all_synth_html += f"""
            <button class="collapsible">
                <img src="icons/open-grey.png" alt="Expand" class="icon-small open-icon hidden">
                <img src="icons/closed-grey.png" alt="Collapse" class="icon-small close-icon">
                <strong>
                    <a href="#{item_slug}" class="anchor-link">
                        {item}: {count}
                    </a>
                </strong>
            </button>
            <div class="content" style="display: none;" id="{item_slug}">
                {character_list_html}
            </div>
            """
        
        # Generate synth source list (synth_source_data equivalent)
        synth_source_data_html = ""
        for source_item, characters in sorted(synth_sources.items(), key=lambda x: (-len(x[1]), x[0])):
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]} (synthesized into {char["synthesized_item"]})</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in characters
            )
            
            source_slug = source_item.lower().replace(' ', '-').replace("'", "").replace('"', "")
            synth_source_data_html += f"""
            <button class="collapsible">
                <img src="icons/open-grey.png" alt="Expand" class="icon-small open-icon hidden">
                <img src="icons/closed-grey.png" alt="Collapse" class="icon-small close-icon">
                <strong>
                    <a href="#{source_slug}-source" class="anchor-link">
                        {source_item}: {len(characters)}
                    </a>
                </strong>
            </button>
            <div class="content" style="display: none;" id="{source_slug}-source">
                {character_list_html}
            </div>
            """
        
        # Generate the complete HTML exactly like the original format
        return f"""
        <h2>Synth reporting</h2>
        <h2 id="synth-items">
            {synth_user_count} Characters with Synthesized items equipped
            <a href="#synth-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>

        <h3>This is base synthesized items</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="special">
                {all_synth_html}
            </div>
        </div>

        <h2 id="synth-from">
            {synth_source_user_count} Synthesized FROM listings
            <a href="#synth-from" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>This shows where properties from an item are showing up in other items. If you wanted to see where the slow from Kelpie or the Ball light from Ondal's had popped up, this is where to look</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="special">
                {synth_source_data_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_socketable_section(socketable_data):
        """Generate HTML for socketable items section"""
        return f"""
        <h2 id="socketable-reporting">
            Socketable reporting
            <a href="#socketable-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>What are people putting in sockets</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Socketable Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Socketable Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="socketable">
                <p>Socketable analysis will be implemented here</p>
            </div>
        </div>
        """

    @staticmethod
    def _generate_unused_items_section(unused_items_data):
        """Generate HTML for unused items section matching original format exactly"""
        
        # Get mercenary data
        merc_used_items = unused_items_data.get('merc_used_items', set())
        merc_users = unused_items_data.get('merc_users', {})
        
        def format_unused_items_list(items, merc_used_items, merc_users):
            """Format a set of unused items as an HTML list with mercenary usage info"""
            if not items:
                return "<p>No unused items found.</p>"
            
            html_output = "<ul>"
            
            for item in sorted(items):
                formatted_item = item.strip().lower()
                is_merc_only = formatted_item in merc_used_items
                merc_list = merc_users.get(formatted_item, [])
                
                # Capitalize first letter for display
                display_item = item.title()
                
                # Generate character list HTML for merc users
                merc_character_html = "".join(
                    f"""
                    <div class="character-info">
                        <div class="character-link">
                            <a href="https://beta.pathofdiablo.com/armory?name={char["Name"]}" target="_blank">
                                {char["Name"]}
                            </a>
                        </div>
                        <div>Level {char["Level"]} {char["Class"]}</div>
                        <div class="hover-trigger" data-character-name="{char["Name"]}"></div>
                    </div>
                    <div class="character">
                        <div class="popup hidden"></div>
                    </div>
                    """
                    for char in merc_list
                )
                
                # Add collapsible button for mercs if any exist
                merc_html_section = ""
                if merc_list:
                    merc_html_section = f"""
                    <button class="collapsible">
                        <img src="icons/open-grey.png" alt="Expand Mercenaries" class="icon-small open-icon hidden">
                        <img src="icons/closed-grey.png" alt="Collapse Mercenaries" class="icon-small close-icon">
                        <p>Characters whose mercs use {display_item}</p>
                    </button>
                    <div class="content" style="display: none;">
                        {merc_character_html if merc_character_html else "<p>No mercenaries using this item.</p>"}
                    </div>
                    """
                
                # Add item to list with (only used on mercenaries) if applicable
                html_output += f"""
                <li>
                    <strong>{display_item} </strong>
                    <span style='color:gray;'>{'(only used on mercenaries)' if is_merc_only else ''}</span>
                    {merc_html_section}
                </li>
                """
            
            html_output += "</ul>"
            return html_output
        
        # Get the unused items data
        unused_runewords = unused_items_data.get('unused_runewords', set())
        unused_uniques = unused_items_data.get('unused_uniques', set())
        unused_set_items = unused_items_data.get('unused_set_items', set())
        
        # Format each category with mercenary data
        unused_runewords_html = format_unused_items_list(unused_runewords, merc_used_items, merc_users)
        unused_uniques_html = format_unused_items_list(unused_uniques, merc_used_items, merc_users)
        unused_set_items_html = format_unused_items_list(unused_set_items, merc_used_items, merc_users)
        
        return f"""
        <h2 id="unused-items">Unused Items
            <a href="#unused-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>Some items get no love at the top of the ladder *</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">
            <!-- Runewords -->
            <button class="collapsible"> 
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Unused Runewords</strong>
            </button>
            <div class="content" style="display: none;">{unused_runewords_html}</div>

            <!-- Uniques -->
            <button class="collapsible"> 
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Unused Unique Items</strong>
            </button>
            <div class="content" style="display: none;">{unused_uniques_html}</div>

            <!-- Set Items -->
            <button class="collapsible"> 
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>Unused Set Items</strong>
            </button>
            <div class="content" style="display: none;">{unused_set_items_html}</div>
        </div>
        <br>
        <em>*Items declared unused by comparing to a list of ALL items. Reference list used for all runewords, uniques, and set items can be found <a href="https://github.com/GreenDude120/builds_data/blob/main/items_list.py">here</a></em>
        <br>
        """

    @staticmethod
    def _generate_weapon_analysis_section(weapon_data):
        """Generate HTML for weapon analysis sections matching original format exactly"""
        
        # Get the data from the weapon analysis
        one_or_two_html = weapon_data.get('one_or_two_html', '<p>No data available</p>')
        two_handed_html = weapon_data.get('two_handed_html', '<p>No data available</p>')
        bow_html = weapon_data.get('bow_html', '<p>No data available</p>')
        
        return f"""
        <h2 id="one-two-handed">Characters Weilding 2-Handed Swords
            <a href="#one-two-handed" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">
            {one_or_two_html}
        </div>
        <hr>
        <h2 id="two-handed">Melee Weapons That Require Two Hands
            <a href="#two-handed" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">
            {two_handed_html}
        </div>
        <hr>
        <h2 id="all-bows">Bows and Crossbows
            <a href="#all-bows" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">
            {bow_html}
        </div>
        <h2>Non-Amazon Bow Users</h2>
        <a href="Notazons"> <img src="icons/Special.png" alt="Non-Amazon Bow Users" style="width:300px;height:50px;" class="collapsible icon"></a>
        <h2>Unique Arrows & Bolts</h2>
        <a href="Unique_Bolts_and_Arrows"> <img src="icons/Special.png" alt="Unique Arrows & Bolts" style="width:300px;height:50px;" class="collapsible icon"></a>
        <hr>
        <h2>Dual Offensive Aura Items Equipped</h2>
        <a href="2AuraItems"> <img src="icons/Special.png" alt="Dual Offensive Aura Items Equipped" style="width:300px;height:50px;" class="collapsible icon"></a>

        """

    @staticmethod
    def _generate_build_enabling_section(build_enabling_data):
        """Generate HTML for the build enabling items section"""
        if not build_enabling_data:
            return """
            <h2 id="build-enabling-items">
                Build Enabling Items
                <a href="#build-enabling-items" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>
            </h2>
            <p>No build enabling items found in the current data.</p>
            """
        
        # Calculate total characters using build enabling items
        total_build_users = sum(len(characters) for characters in build_enabling_data.values())
        
        # Generate HTML for each build
        builds_html = ""
        for build_name, characters in sorted(build_enabling_data.items(), key=lambda x: (-len(x[1]), x[0])):
            build_slug = build_name.lower().replace(" ", "-").replace("'", "")
            
            # Generate character list HTML
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]} ({char["enabling_reason"]})</div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in characters
            )
            
            builds_html += f"""
            <button class="collapsible">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>
                    <a href="#{build_slug}" class="anchor-link">
                        {build_name}: {len(characters)} characters
                    </a>
                </strong>
            </button>
            <div class="content" style="display: none;" id="{build_slug}">
                {character_list_html if characters else "<p>No characters found for this build.</p>"}
            </div>
            """
        
        return f"""
        <h2 id="build-enabling-items">
            Build Enabling Items
            <a href="#build-enabling-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>{total_build_users} Characters with items that enable specific builds</h3>
        <p>These characters are using items that enable or support specific build archetypes through unique item names or special properties.</p>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Build Enabling Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Build Enabling Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="build-enabling">
                {builds_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_loadout_intro_section(loadout_data):
        """Generate HTML for the weapon loadout intro section"""
        complete_categories = {
            "Weapon + Shield",
            "Dual Wield",
            "Bow + Arrows",
            "Crossbow + Bolts",
            "A Single Two-Handed Weapon",
        }
        
        loadout_counts = loadout_data.get('loadout_counts', {})
        total = loadout_data.get('total_loadouts', 1)
        
        html = "<h2>Overall Weapon Usage Stats, Characters Equipped with:</h2><ul>"
        for category, count in sorted(loadout_counts.items(), key=lambda x: -x[1]):
            if category in complete_categories:
                percentage = f"{(count / total * 100):.1f}%"
                html += f"<li><strong>{category}:</strong> {count} ({percentage})</li>"
        html += "</ul>"
        
        return html
    
    @staticmethod
    def _generate_incomplete_loadouts_section(loadout_data):
        """Generate HTML for the incomplete loadouts section"""
        incomplete_categories = {
            "Single One-Handed Weapon (Missing Shield or Second Weapon)",
            "Shield Only (Missing Weapon)",
            "Bow Only (Missing Arrows)",
            "Arrows Only (Missing Bow)",
            "Crossbow Only (Missing Bolts)",
            "Bolts Only (Missing Crossbow)",
        }
        
        loadout_counts = loadout_data.get('loadout_counts', {})
        total = loadout_data.get('total_loadouts', 1)
        empty_loadout_count = loadout_data.get('empty_loadout_count', 0)
        partially_empty_set_count = loadout_data.get('partially_empty_set_count', 0)
        
        # Incomplete section inside collapsible
        collapsible_html = f'''
        <h2 id="incomplete-loadouts">Incomplete Character Loadouts
            <a href="#incomplete-loadouts" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="Incomplete Loadouts Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Incomplete Loadouts Close" class="icon-small close-icon">
            <strong>Incomplete Loadouts</strong>
        </button>
        <div class="content" style="display: none;">
            <div id="incompletes">
                <p>These character builds are incomplete and missing items:</p>
                <ul>
        '''

        for category, count in sorted(loadout_counts.items(), key=lambda x: -x[1]):
            if category in incomplete_categories:
                percentage = f"{(count / total * 100):.1f}%"
                collapsible_html += f"<li><strong>{category}:</strong> {count} ({percentage})</li>"

        collapsible_html += "</ul></div></div>"
        summary_html = f"""
            <p><strong>Characters with no weapons in either weapon slot:</strong> {empty_loadout_count}</p>
            <p><strong>Characters with no weapons on swap:</strong> {partially_empty_set_count}</p><br>
        """

        return collapsible_html + "<br>" + summary_html

    @staticmethod
    def _generate_item_summary_section(item_summary_data):
        """Generate HTML for item popularity by slot section"""
        if not item_summary_data:
            items_html = "<p>No item summary data available.</p>"
        else:
            items_html = ""
            for category, counter in item_summary_data.items():
                sorted_items = counter.most_common()
                items_list = "".join(
                    f"<div>{name}: {count}</div>" for name, count in sorted_items
                )

                items_html += f"""
                <button class="collapsible">
                    <img src="icons/open-grey.png" class="icon-small open-icon hidden">
                    <img src="icons/closed-grey.png" class="icon-small close-icon">
                    <strong>{category} ({sum(counter.values())} items)</strong>
                </button>
                <div class="content" style="display: none;">
                    {items_list if items_list else "<p>No items found in this category.</p>"}
                </div>
                """
        
        return f"""
        <h2 id="item-popularity-slot">
            Item Popularity by Slot
            <a href="#item-popularity-slot" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>Items categorized by equipment slot and quality type</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Item Summary Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Item Summary Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <div id="item-summary">
                {items_html}
            </div>
        </div>
        """

    @staticmethod
    def _generate_all_list_items(counter, character_data):
        """Generate expandable list with character details for each item"""
        if not isinstance(character_data, dict):
            return ""

        items_html = ""
        for item, count in counter:
            name = item
            
            # Handle special cases
            if item == "2693":
                name = "Delirium"
            elif item == "-26":
                name = "Pattern2"
                
            slug = name.lower().replace(" ", "-").replace("'", "").replace('"', "")
            
            character_info = character_data.get(item)
            
            # Check if this item has nested dicts (base → [characters]) - indicates runewords
            if isinstance(character_info, dict):
                # This is a runeword with base item breakdown
                base_html = ""
                for base_item, characters in sorted(character_info.items(), key=lambda kv: len(kv[1]), reverse=True):
                    characters_html = "".join(
                        f"""
                        <div class="character-info">
                            <div class="character-link">
                                <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                                    {char["name"]}
                                </a>
                            </div>
                            <div>Level {char["level"]} {char["class"]}</div>
                            <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                        </div>
                        <div class="character">
                            <div class="popup hidden"></div>
                        </div>
                        """ for char in characters
                    )
                    
                    base_slug = f"{slug}-{base_item.lower().replace(' ', '-')}"
                    base_html += f"""
                    <button class="collapsible">
                        <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                        <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                        <strong>{base_item} ({len(characters)} users)</strong>
                    </button>
                    <div class="content" style="display: none;" id="{base_slug}">
                        {characters_html if characters else "<p>No characters using this base.</p>"}
                    </div>
                    """
                
                items_html += f"""
                <button class="collapsible" id="{slug}">
                    <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                    <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                    <strong>{name} ({count} users)</strong>
                </button>
                <div class="content" style="display: none;">
                    {base_html if base_html else "<p>No characters using this item.</p>"}
                </div>
                """
            else:
                # Flat list for uniques, sets, etc.
                users = character_info or []
                character_list_html = "".join(
                    f"""
                    <div class="character-info">
                        <div class="character-link">
                            <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                                {char["name"]}
                            </a>
                        </div>
                        <div>Level {char["level"]} {char["class"]}</div>
                        <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                    </div>
                    <div class="character">
                        <div class="popup hidden"></div>
                    </div>
                    """ for char in users
                )
                
                items_html += f"""
                <button class="collapsible" id="{slug}">
                    <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                    <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                    <strong>{name} ({count} users)</strong>
                </button>
                <div class="content" style="display: none;">
                    {character_list_html if users else "<p>No character data available.</p>"}
                </div>
                """

        return items_html


def generate_items_equipment_page(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """Main function to generate the complete items and equipment page
    
    Note: Level filtering is now applied in the main script before calling this function,
    but we keep the parameters for consistency and future use.
    """
    
    # Analyze all items
    analyzer = ItemsEquipmentAnalyzer(all_characters)
    analysis_data = analyzer.analyze_all_items()
    
    # Generate HTML
    html_generator = ItemsEquipmentHTMLGenerator()
    html_content = html_generator.generate_full_items_page(analysis_data, timestamp)
    
    return html_content