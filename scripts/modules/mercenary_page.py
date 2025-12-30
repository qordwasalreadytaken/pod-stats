"""
Mercenary Analysis Module
Handles all mercenary-related analysis and HTML generation for the dedicated mercenary page
"""

from collections import Counter, defaultdict
from datetime import datetime
from .shared_utils import generate_standard_javascript


class MercenaryAnalyzer:
    def __init__(self, all_characters):
        self.all_characters = all_characters
        
    def analyze_mercenaries(self):
        """
        Analyze mercenary data from all characters
        Returns comprehensive mercenary analysis data
        """
        mercenary_counts = Counter()
        mercenary_equipment = defaultdict(lambda: defaultdict(Counter))
        mercenary_names = Counter()
        merc_users = defaultdict(list)  # Track which characters use which merc items
        merc_item_counters = {
            'runeword': Counter(),
            'unique': Counter(), 
            'set': Counter()
        }
        # Track runeword bases: runeword_name -> base_item -> [characters]
        merc_runeword_bases = defaultdict(lambda: defaultdict(list))
        # Track unique and set item users: item_name -> [characters]
        merc_unique_users = defaultdict(list)
        merc_set_users = defaultdict(list)
        
        for char_data in self.all_characters:
            if not isinstance(char_data, dict):
                continue
                
            mercenary_type = char_data.get("MercenaryType")
            if not mercenary_type:
                continue
                
            # Count mercenary types
            mercenary_counts[mercenary_type] += 1
            
            # Track mercenary names
            mercenary_name = char_data.get("MercenaryName")
            if mercenary_name:
                mercenary_names[mercenary_name] += 1
            
            # Analyze mercenary equipment - try multiple possible field names
            merc_equipped = char_data.get("mercenary_equipped", {})
            if not merc_equipped:
                merc_equipped = char_data.get("MercenaryEquipped", {})
            if not merc_equipped:
                merc_equipped = char_data.get("mercenary", {})
            
            char_info = {
                "name": char_data.get("Name", "Unknown"),
                "level": char_data.get("Stats", {}).get("Level", 0) if "Stats" in char_data else char_data.get("Level", 0),
                "class": char_data.get("Class", "Unknown")
            }
            
            # Handle different data structures
            if isinstance(merc_equipped, dict):
                for worn_category, item_data in merc_equipped.items():
                    if not isinstance(item_data, dict):
                        continue
                        
                    item_title = item_data.get("Title", "Unknown")
                    quality_code = item_data.get("QualityCode", "")
                    
                    # Track equipment by mercenary type and slot
                    mercenary_equipment[mercenary_type][worn_category][item_title] += 1
                    
                    # Track users of each mercenary item
                    merc_users[item_title.strip().lower()].append(char_info)
                    
                    # Update global item counters for mercenary items
                    if quality_code == "q_runeword":
                        merc_item_counters['runeword'][item_title] += 1
                        # Track base item for runewords
                        base_item = item_data.get("Tag") or item_data.get("TextTag") or "Unknown"
                        merc_runeword_bases[item_title][base_item].append(char_info)
                    elif quality_code == "q_unique":
                        merc_item_counters['unique'][item_title] += 1
                        merc_unique_users[item_title].append(char_info)
                    elif quality_code == "q_set":
                        merc_item_counters['set'][item_title] += 1
                        merc_set_users[item_title].append(char_info)
            elif isinstance(merc_equipped, list):
                # Handle list structure if that's what we have
                for i, item_data in enumerate(merc_equipped):
                    if not isinstance(item_data, dict):
                        continue
                        
                    item_title = item_data.get("Title", "Unknown")
                    quality_code = item_data.get("QualityCode", "")
                    worn_category = item_data.get("Worn", f"slot_{i}")  # Use actual Worn field, fallback to slot_i
                    
                    # Track equipment by mercenary type and slot
                    mercenary_equipment[mercenary_type][worn_category][item_title] += 1
                    
                    # Track users of each mercenary item
                    merc_users[item_title.strip().lower()].append(char_info)
                    
                    # Update global item counters for mercenary items
                    if quality_code == "q_runeword":
                        merc_item_counters['runeword'][item_title] += 1
                        # Track base item for runewords
                        base_item = item_data.get("Tag") or item_data.get("TextTag") or "Unknown"
                        merc_runeword_bases[item_title][base_item].append(char_info)
                    elif quality_code == "q_unique":
                        merc_item_counters['unique'][item_title] += 1
                        merc_unique_users[item_title].append(char_info)
                    elif quality_code == "q_set":
                        merc_item_counters['set'][item_title] += 1
                        merc_set_users[item_title].append(char_info)
        
        # Analyze socketable items
        socketable_data = self._analyze_mercenary_socketables()
        
        return {
            'mercenary_counts': mercenary_counts,
            'mercenary_equipment': mercenary_equipment,
            'mercenary_names': mercenary_names,
            'merc_users': merc_users,
            'merc_item_counters': merc_item_counters,
            'merc_runeword_bases': merc_runeword_bases,
            'merc_unique_users': merc_unique_users,
            'merc_set_users': merc_set_users,
            'socketable_data': socketable_data,
            'debug_info': {
                'total_chars_processed': len([char for char in self.all_characters if isinstance(char, dict)]),
                'chars_with_mercs': len([char for char in self.all_characters if isinstance(char, dict) and char.get("MercenaryType")]),
                'equipment_items_found': sum(len(categories) for categories in mercenary_equipment.values())
            }
        }
    
    def _analyze_mercenary_socketables(self):
        """Analyze what items are socketed in mercenary equipment"""
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
        
        # Process all characters' mercenary equipment
        for char in self.all_characters:
            if not isinstance(char, dict):
                continue
            
            # Get mercenary equipment - try multiple possible field names
            merc_equipped = char.get("mercenary_equipped", {})
            if not merc_equipped:
                merc_equipped = char.get("MercenaryEquipped", {})
            if not merc_equipped:
                merc_equipped = char.get("mercenary", {})
            
            # Process dict structure
            if isinstance(merc_equipped, dict):
                for worn_category, item in merc_equipped.items():
                    if not isinstance(item, dict):
                        continue
                    self._process_socketed_item(item, rune_names, just_socketed_runes, 
                                               just_socketed_excluding_runewords_runes,
                                               just_socketed_non_runes, just_socketed_magic,
                                               just_socketed_rare, just_socketed_facets,
                                               extract_element)
            # Process list structure
            elif isinstance(merc_equipped, list):
                for item in merc_equipped:
                    if not isinstance(item, dict):
                        continue
                    self._process_socketed_item(item, rune_names, just_socketed_runes,
                                               just_socketed_excluding_runewords_runes,
                                               just_socketed_non_runes, just_socketed_magic,
                                               just_socketed_rare, just_socketed_facets,
                                               extract_element)
        
        return {
            'just_socketed_runes': just_socketed_runes,
            'just_socketed_excluding_runewords_runes': just_socketed_excluding_runewords_runes,
            'just_socketed_non_runes': just_socketed_non_runes,
            'just_socketed_magic': just_socketed_magic,
            'just_socketed_rare': just_socketed_rare,
            'just_socketed_facets': just_socketed_facets
        }
    
    def _process_socketed_item(self, item, rune_names, just_socketed_runes,
                               just_socketed_excluding_runewords_runes,
                               just_socketed_non_runes, just_socketed_magic,
                               just_socketed_rare, just_socketed_facets,
                               extract_element):
        """Process a single socketed item from mercenary equipment"""
        if item.get('SocketCount', '0') == '0':
            return
        
        is_runeword = item.get('QualityCode') == 'q_runeword'
        
        # Process each socketed item
        for socketed_item in item.get('Sockets', []):
            title = socketed_item.get('Title', '')
            quality_code = socketed_item.get('QualityCode', '')
            
            if title in rune_names:
                # Count all runes (including those in runewords)
                just_socketed_runes[title] += 1
                
                # Count runes excluding runewords
                if not is_runeword:
                    just_socketed_excluding_runewords_runes[title] += 1
            else:
                # Non-rune items (only count if not in runewords)
                if not is_runeword:
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
    
    def get_mercenary_statistics(self, analysis_data):
        """Calculate additional mercenary statistics"""
        mercenary_counts = analysis_data['mercenary_counts']
        mercenary_equipment = analysis_data['mercenary_equipment']
        
        total_mercs = sum(mercenary_counts.values())
        total_chars_with_mercs = len([char for char in self.all_characters 
                                    if char.get("MercenaryType")])
        
        # Calculate equipment coverage by mercenary type
        equipment_stats = {}
        total_equipment_items = 0
        
        for merc_type, equipment in mercenary_equipment.items():
            slots_filled = {slot: sum(items.values()) for slot, items in equipment.items()}
            total_equipment_items += sum(slots_filled.values())
            
            equipment_stats[merc_type] = {
                'total_mercs': mercenary_counts[merc_type],
                'slots_filled': slots_filled,
                'unique_items': {slot: len(items) for slot, items in equipment.items()}
            }
        
        return {
            'total_mercs': total_mercs,
            'total_chars_with_mercs': total_chars_with_mercs,
            'total_equipment_items': total_equipment_items,
            'equipment_stats': equipment_stats
        }


class MercenaryHTMLGenerator:
    """Generates HTML for the mercenary analysis page"""
    
    @staticmethod
    def generate_full_mercenary_page(analysis_data, stats_data, timestamp):
        """Generate the complete HTML for the mercenary analysis page"""
        
        mercenary_counts = analysis_data['mercenary_counts']
        mercenary_equipment = analysis_data['mercenary_equipment'] 
        mercenary_names = analysis_data['mercenary_names']
        merc_item_counters = analysis_data['merc_item_counters']
        merc_runeword_bases = analysis_data['merc_runeword_bases']
        merc_unique_users = analysis_data['merc_unique_users']
        merc_set_users = analysis_data['merc_set_users']
        socketable_data = analysis_data['socketable_data']
        
        # Generate individual sections
        type_counts_html = MercenaryHTMLGenerator._generate_type_counts_section(mercenary_counts)
        names_html = MercenaryHTMLGenerator._generate_names_section(mercenary_names)
        equipment_html = MercenaryHTMLGenerator._generate_equipment_section(mercenary_equipment)
        popular_items_html = MercenaryHTMLGenerator._generate_popular_items_section(merc_item_counters, merc_runeword_bases, merc_unique_users, merc_set_users)
        socketable_html = MercenaryHTMLGenerator._generate_socketable_section(socketable_data)
        stats_html = MercenaryHTMLGenerator._generate_statistics_section(stats_data)
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PoD Mercenary Analysis</title>
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

                <div class="banner" style="top:50px; left:10%; width:80%;">
                    ⚠️ This is a test site for PoD's Trends site. Please direct any feedback to Qord. ⚠️
                </div>

                <div class="main page-intro">
                    <h1>PoD MERCENARY ANALYSIS</h1>
                    <h2>Comprehensive analysis of mercenary usage and equipment patterns</h2>
                    
                    {stats_html}
                    
                    <hr>

                    {popular_items_html}

                    <hr>
                    
                    {socketable_html}

                    <hr> 
                                        
                    {type_counts_html}
                    
                    <hr>
                    
                    {names_html}
                    
                    <hr>
                    
                    {equipment_html}
                    
                    <hr>
                   
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
    def _generate_statistics_section(stats_data):
        """Generate overview statistics section"""
        total_chars_with_mercs = stats_data['total_chars_with_mercs']
        total_equipment_items = stats_data['total_equipment_items']
        equipment_stats = stats_data['equipment_stats']
        
        return f"""
        <h2 id="mercenary-overview">
            Mercenary Overview Statistics
            <a href="#mercenary-overview" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Total Characters with Mercenaries: {total_chars_with_mercs}</h3>
                <h3>Total Mercenary Equipment Items: {total_equipment_items}</h3>
            </div>
<!--            <div class="fun-facts-column">
                <h3>Equipment Coverage by Type:</h3>
                <ul>
                    {_generate_equipment_coverage_list(equipment_stats)}
                </ul>
            </div> -->
        </div>
        """

    @staticmethod
    def _generate_type_counts_section(mercenary_counts):
        """Generate mercenary type counts section"""
        counts_html = ''.join(
            f'<li>{merc_type}: {count}</li>' 
            for merc_type, count in mercenary_counts.most_common()
        )
        
        return f"""
        <h2 id="mercenary-types">
            Mercenary Type Distribution
            <a href="#mercenary-types" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible">
            <img src="icons/Merc_click.png" alt="Open" class="icon open-icon hidden">
            <img src="icons/Merc.png" alt="Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <ul>{counts_html}</ul>
        </div>
        """

    @staticmethod  
    def _generate_names_section(mercenary_names):
        """Generate popular mercenary names section"""
        names_html = ''.join(
            f'<li>{name}: {count}</li>' 
            for name, count in mercenary_names.most_common(20)
        )
        
        return f"""
        <h2 id="mercenary-names">
            Most Popular Mercenary Names
            <a href="#mercenary-names" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible">
            <img src="icons/Merc_click.png" alt="Open" class="icon open-icon hidden">
            <img src="icons/Merc.png" alt="Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <ul>{names_html}</ul>
        </div>
        """

    @staticmethod
    def _generate_equipment_section(mercenary_equipment):
        """Generate equipment analysis by mercenary type"""
        equipment_html = ""
        
        for mercenary, categories in mercenary_equipment.items():
            readable_mercenary = MercenaryHTMLGenerator._map_readable_mercenary_name(mercenary)
            
            category_html = ""
            for worn_category, items in categories.items():
                readable_worn = MercenaryHTMLGenerator._map_readable_slot_name(worn_category)
                
                items_list = ''.join(
                    f'<li>{item}: {count}</li>' 
                    for item, count in items.most_common(10)
                )
                
                if items_list:
                    category_html += f"""
                    <div class="column">
                        <h4>{readable_worn}</h4>
                        <ul>{items_list}</ul>
                    </div>
                    """
            
            if category_html:
                equipment_html += f"""
                <h3>{readable_mercenary}</h3>
                <div class="container">
                    {category_html}
                </div>
                """
        
        return f"""
        <h2 id="mercenary-equipment">
            Equipment by Mercenary Type
            <a href="#mercenary-equipment" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible">
            <img src="icons/Merc_click.png" alt="Open" class="icon open-icon hidden">
            <img src="icons/Merc.png" alt="Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            {equipment_html}
        </div>
        """

    @staticmethod
    def _generate_popular_items_section(merc_item_counters, merc_runeword_bases, merc_unique_users, merc_set_users):
        """Generate most popular mercenary items section with expandable lists and character details"""
        
        # Generate expandable runewords list with base items
        all_runewords = merc_item_counters['runeword'].most_common()
        runewords_html = MercenaryHTMLGenerator._generate_merc_runeword_list(all_runewords, merc_runeword_bases)
        
        # Generate expandable uniques and sets lists with character details
        all_uniques = merc_item_counters['unique'].most_common()
        uniques_html = MercenaryHTMLGenerator._generate_merc_item_list(all_uniques, merc_unique_users)
        
        all_sets = merc_item_counters['set'].most_common()
        sets_html = MercenaryHTMLGenerator._generate_merc_item_list(all_sets, merc_set_users)
        
        return f"""
        <h2 id="popular-merc-items">
            Mercenary Items Usage
            <a href="#popular-merc-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        
        <h3 id="merc-runewords">Runewords on Mercenaries</h3>
        <button type="button" class="collapsible">
            <img src="icons/Runewords_click.png" alt="Runewords Open" class="icon open-icon hidden">
            <img src="icons/Runewords.png" alt="Runewords Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="merc-runewords-list">
                {runewords_html if runewords_html else '<p>No runewords found on mercenaries</p>'}
            </div>
        </div>
        
        <h3 id="merc-uniques">Unique Items on Mercenaries</h3>
        <button type="button" class="collapsible">
            <img src="icons/Uniques_click.png" alt="Uniques Open" class="icon open-icon hidden">
            <img src="icons/Uniques.png" alt="Uniques Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="merc-uniques-list">
                {uniques_html if uniques_html else '<p>No unique items found on mercenaries</p>'}
            </div>
        </div>
        
        <h3 id="merc-sets">Set Items on Mercenaries</h3>
        <button type="button" class="collapsible">
            <img src="icons/Sets_click.png" alt="Sets Open" class="icon open-icon hidden">
            <img src="icons/Sets.png" alt="Sets Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="merc-sets-list">
                {sets_html if sets_html else '<p>No set items found on mercenaries</p>'}
            </div>
        </div>
        """

    @staticmethod
    def _generate_merc_runeword_list(runewords, runeword_bases):
        """Generate expandable list of runewords with base item breakdown"""
        items_html = ""
        
        for runeword_name, count in runewords:
            slug = runeword_name.lower().replace(" ", "-").replace("'", "").replace('"', "")
            
            base_items = runeword_bases.get(runeword_name, {})
            
            # Generate base item breakdown
            base_html = ""
            for base_item, characters in sorted(base_items.items(), key=lambda kv: len(kv[1]), reverse=True):
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
                    <strong>{base_item} ({len(characters)} uses)</strong>
                </button>
                <div class="content" style="display: none;" id="{base_slug}">
                    {characters_html if characters else "<p>No characters using this base.</p>"}
                </div>
                """
            
            items_html += f"""
            <button class="collapsible" id="{slug}">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>{runeword_name} ({count} total)</strong>
            </button>
            <div class="content" style="display: none;">
                {base_html if base_html else "<p>No base item data available.</p>"}
            </div>
            """
        
        return items_html

    @staticmethod
    def _generate_merc_item_list(items, item_users):
        """Generate expandable list for unique/set items with character details"""
        items_html = ""
        
        for item_name, count in items:
            slug = item_name.lower().replace(" ", "-").replace("'", "").replace('"', "")
            
            # Get characters using this item
            characters = item_users.get(item_name, [])
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
            
            items_html += f"""
            <button class="collapsible" id="{slug}">
                <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
                <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>{item_name} ({count} uses)</strong>
            </button>
            <div class="content" style="display: none;">
                {characters_html if characters else "<p>No character data available.</p>"}
            </div>
            """
        
        return items_html

    @staticmethod
    def _generate_socketable_section(socketable_data):
        """Generate HTML for mercenary socketable items section"""
        just_socketed_runes = socketable_data['just_socketed_runes']
        just_socketed_excluding_runewords_runes = socketable_data['just_socketed_excluding_runewords_runes']
        just_socketed_non_runes = socketable_data['just_socketed_non_runes']
        just_socketed_magic = socketable_data['just_socketed_magic']
        just_socketed_rare = socketable_data['just_socketed_rare']
        just_socketed_facets = socketable_data['just_socketed_facets']
        
        # Format rune lists
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
        
        other_items_html = '<ul>' + '\n'.join(f"<li>{item}</li>" for item in all_other_items) + '</ul>' if all_other_items else '<p>No non-rune items found in sockets</p>'
        
        html = f"""
        <h2 id="socketable-reporting">
            Mercenary Socketable Reporting
            <a href="#socketable-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>What are people putting in mercenary equipment sockets</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Synth Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Synth Close" class="icon close-icon">
        </button>  
        <div class="content" style="display: none;">  
            <h2>Socketed Runes Count</h2>
            <h3>Mercenary Equipment Only</h3>
            <div id="special" class="container">
                <br>
                <div class="column">
                    <!-- Left Column -->
                    <h2>Most Common Runes <br>(Including Runewords)</h2>
                    <ul id="sorted_just_socketed_runes">
                        {sorted_just_socketed_runes if sorted_just_socketed_runes else '<li>No runes found</li>'}
                    </ul>
                </div>

                <!-- Right Column -->
                <div class="column">
                    <h2>Most Common Runes <br>(Excluding Runewords)</h2>
                    <ul id="sorted_just_socketed_excluding_runewords_runes">
                        {sorted_just_socketed_excluding_runewords_runes if sorted_just_socketed_excluding_runewords_runes else '<li>No runes found</li>'}
                    </ul>
                </div>
            </div>

            <div>
                <h2>Other Items Found in Sockets</h2>
                <h3>Mercenary Equipment Only</h3>
                {other_items_html}
            </div>
        </div>
        <br>"""
        
        return html

    @staticmethod
    def _map_readable_mercenary_name(mercenary_type):
        """Map internal mercenary names to readable names"""
        mercenary_mapping = {
            "Desert Mercenary": "Act 2 Desert Mercenary",
            "Rogue Scout": "Act 1 Rogue Scout", 
            "Eastern Sorceror": "Act 3 Eastern Sorceror",
            "Barbarian": "Act 5 Barbarian"
        }
        return mercenary_mapping.get(mercenary_type, mercenary_type)

    @staticmethod
    def _map_readable_slot_name(worn_category):
        """Map internal slot names to readable names"""
        worn_mapping = {
            "body": "Armor",
            "helmet": "Helmet",  
            "weapon1": "Weapon",
            "weapon2": "Shield/Offhand",
            # Handle any unmapped slot_X patterns
            "slot_0": "Slot 0",
            "slot_1": "Slot 1", 
            "slot_2": "Slot 2",
            "slot_3": "Slot 3"
        }
        return worn_mapping.get(worn_category, worn_category.title())


def _generate_equipment_coverage_list(equipment_stats):
    """Helper function to generate equipment coverage statistics"""
    coverage_items = []
    for merc_type, stats in equipment_stats.items():
        total_slots = sum(stats['slots_filled'].values())
        total_mercs = stats['total_mercs']
        coverage_pct = (total_slots / total_mercs * 100) if total_mercs > 0 else 0
        coverage_items.append(f'<li>{merc_type}: {coverage_pct:.1f}% equipment coverage</li>')
    
    return ''.join(coverage_items)


def generate_mercenary_page(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """Main function to generate the complete mercenary analysis page
    
    Note: Level filtering is now applied in the main script before calling this function,
    but we keep the parameters for consistency and future use.
    """
    
    # Analyze mercenary data
    analyzer = MercenaryAnalyzer(all_characters)
    analysis_data = analyzer.analyze_mercenaries()
    stats_data = analyzer.get_mercenary_statistics(analysis_data)
    
    # Generate HTML
    html_generator = MercenaryHTMLGenerator()
    html_content = html_generator.generate_full_mercenary_page(analysis_data, stats_data, timestamp)
    
    return html_content