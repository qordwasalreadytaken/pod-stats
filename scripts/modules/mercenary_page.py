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
                "Name": char_data.get("name", "Unknown"),
                "Level": char_data.get("level", 0),
                "Class": char_data.get("class", "Unknown")
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
                    elif quality_code == "q_unique":
                        merc_item_counters['unique'][item_title] += 1
                    elif quality_code == "q_set":
                        merc_item_counters['set'][item_title] += 1
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
                    elif quality_code == "q_unique":
                        merc_item_counters['unique'][item_title] += 1
                    elif quality_code == "q_set":
                        merc_item_counters['set'][item_title] += 1
        
        return {
            'mercenary_counts': mercenary_counts,
            'mercenary_equipment': mercenary_equipment,
            'mercenary_names': mercenary_names,
            'merc_users': merc_users,
            'merc_item_counters': merc_item_counters,
            'debug_info': {
                'total_chars_processed': len([char for char in self.all_characters if isinstance(char, dict)]),
                'chars_with_mercs': len([char for char in self.all_characters if isinstance(char, dict) and char.get("MercenaryType")]),
                'equipment_items_found': sum(len(categories) for categories in mercenary_equipment.values())
            }
        }
    
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
        
        # Generate individual sections
        type_counts_html = MercenaryHTMLGenerator._generate_type_counts_section(mercenary_counts)
        names_html = MercenaryHTMLGenerator._generate_names_section(mercenary_names)
        equipment_html = MercenaryHTMLGenerator._generate_equipment_section(mercenary_equipment)
        popular_items_html = MercenaryHTMLGenerator._generate_popular_items_section(merc_item_counters)
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
                    ⚠️ This is a test preview of next season's display. Please direct any feedback to Qord. ⚠️
                </div>

                <div class="main page-intro">
                    <h1>PoD MERCENARY ANALYSIS</h1>
                    <h2>Comprehensive analysis of mercenary usage and equipment patterns</h2>
                    
                    {stats_html}
                    
                    <hr>

                    {popular_items_html}

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
    def _generate_popular_items_section(merc_item_counters):
        """Generate most popular mercenary items section"""
        
        runewords_html = ''.join(
            f'<li>{item}: {count}</li>' 
            for item, count in merc_item_counters['runeword'].most_common(15)
        )
        
        uniques_html = ''.join(
            f'<li>{item}: {count}</li>' 
            for item, count in merc_item_counters['unique'].most_common(15)
        )
        
        sets_html = ''.join(
            f'<li>{item}: {count}</li>' 
            for item, count in merc_item_counters['set'].most_common(15)
        )
        
        return f"""
        <h2 id="popular-merc-items">
            Most Popular Mercenary Items
            <a href="#popular-merc-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <div class="container">
            <div class="column">
                <h3>Top Runewords on Mercenaries</h3>
                <ul>{runewords_html if runewords_html else '<li>No runewords found</li>'}</ul>
            </div>
            <div class="column">
                <h3>Top Unique Items on Mercenaries</h3>
                <ul>{uniques_html if uniques_html else '<li>No unique items found</li>'}</ul>
            </div>
            <div class="column">
                <h3>Top Set Items on Mercenaries</h3>
                <ul>{sets_html if sets_html else '<li>No set items found</li>'}</ul>
            </div>
        </div>
        """

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