"""
Fun Facts Analysis Module
Handles all fun facts analysis and HTML generation for the dedicated fun facts page
"""

import statistics
import requests
from collections import defaultdict, Counter
from datetime import datetime
from modules.home_page import fetch_1k_ladder_characters, analyze_api_class_distribution, HomePageGenerator


class FunFactsAnalyzer:
    def __init__(self, all_characters):
        self.all_characters = all_characters
        
    def analyze_fun_facts(self):
        """
        Analyze character data for interesting statistics and fun facts
        Returns comprehensive fun facts data
        """
        # Initialize collections for median calculations
        mf_values = []
        gf_values = []
        life_values = []
        mana_values = []
        
        # Get character count
        character_count = len(self.all_characters)
        
        # Initialize totals
        total_mf = 0
        total_gf = 0
        total_life = 0
        total_mana = 0
        
        # Process each character for basic stats
        for char in self.all_characters:
            if not isinstance(char, dict):
                continue
                
            # Get stats from Stats object
            stats = char.get("Stats", {})
            bonus = char.get("Bonus", {})
            
            # Magic Find and Gold Find are likely in Bonus section
            mf = bonus.get("MagicFind", 0)
            gf = bonus.get("GoldFind", 0) 
            life = stats.get("Life", 0)
            mana = stats.get("Mana", 0)
            
            total_mf += mf
            total_gf += gf
            total_life += life
            total_mana += mana
            
            mf_values.append(mf)
            gf_values.append(gf)
            life_values.append(life)
            mana_values.append(mana)
        
        # Calculate averages and medians
        averages = {
            'mf': total_mf / character_count if character_count > 0 else 0,
            'gf': total_gf / character_count if character_count > 0 else 0,
            'life': total_life / character_count if character_count > 0 else 0,
            'mana': total_mana / character_count if character_count > 0 else 0
        }
        
        medians = {
            'mf': statistics.median(mf_values) if mf_values else 0,
            'gf': statistics.median(gf_values) if gf_values else 0,
            'life': statistics.median(life_values) if life_values else 0,
            'mana': statistics.median(mana_values) if mana_values else 0
        }
        
        # Get top characters for various stats
        top_stats = self._get_top_characters_all_stats()
        
        # Analyze undead characters
        undead_data = self._analyze_undead_characters()
        
        # Analyze Cannot Be Frozen characters
        cbf_data = self._analyze_cannot_be_frozen()
        
        # Analyze top accounts (this fetches fresh API data)
        top_accounts_data = self.analyze_top_accounts()
        
        # Analyze respec leaderboard
        respec_data = self.analyze_respec_leaderboard(is_hardcore=self.is_hardcore)
        
        return {
            'character_count': character_count,
            'averages': averages,
            'medians': medians,
            'top_stats': top_stats,
            'undead_data': undead_data,
            'cbf_data': cbf_data,
            'top_accounts_data': top_accounts_data,
            'respec_data': respec_data
        }
    
    def _get_top_characters_all_stats(self):
        """Get top 5 characters for all tracked statistics"""
        
        def get_stat_value(char, stat_name):
            """Helper function to get stat value from correct location"""
            if not isinstance(char, dict):
                return 0
            
            # Stats like Strength, Dexterity, Vitality, Energy, Life, Mana are in Stats
            if stat_name in ['Strength', 'Dexterity', 'Vitality', 'Energy', 'Life', 'Mana']:
                return char.get("Stats", {}).get(stat_name, 0)
            # MagicFind and GoldFind are in Bonus
            elif stat_name in ['MagicFind', 'GoldFind']:
                return char.get("Bonus", {}).get(stat_name, 0)
            else:
                return char.get(stat_name, 0)
        
        stats_to_track = [
            'Strength', 'Dexterity', 'Vitality', 'Energy',
            'Life', 'Mana', 'MagicFind', 'GoldFind'
        ]
        
        top_stats = {}
        
        for stat_name in stats_to_track:
            # Sort characters by the stat in descending order
            sorted_chars = sorted(
                self.all_characters,
                key=lambda char: get_stat_value(char, stat_name),
                reverse=True
            )
            
            # Get top 5
            top_5 = []
            for char in sorted_chars[:5]:
                if isinstance(char, dict):
                    name = char.get("Name", "Unknown")  # Fixed: 'Name' not 'name'
                    level = char.get("Stats", {}).get("Level", 0) if isinstance(char.get("Stats"), dict) else 0  # Fixed: Stats.Level structure
                    char_class = char.get("Class", "Unknown")  # Fixed: 'Class' not 'class'
                    stat_value = get_stat_value(char, stat_name)  # Use helper function
                    
                    top_5.append({
                        'name': name,
                        'level': level,
                        'class': char_class,
                        'value': stat_value
                    })
            
            top_stats[stat_name] = top_5
        
        return top_stats
    
    def _analyze_undead_characters(self):
        """Analyze characters who have never died (undead)"""
        undead_characters = []
        
        for char in self.all_characters:
            if not isinstance(char, dict):
                continue
                
            # Check if character has never died - use IsDead field
            is_dead = char.get("IsDead", True)  # Default to True if not specified
            if not is_dead:  # Character is not dead (undead)
                undead_characters.append({
                    'name': char.get("Name", "Unknown"),  # Fixed: 'Name' not 'name'
                    'level': char.get("Stats", {}).get("Level", 0) if isinstance(char.get("Stats"), dict) else 0,  # Fixed: Stats.Level structure
                    'class': char.get("Class", "Unknown"),  # Fixed: 'Class' not 'class'
                    'account': char.get("Account", "Unknown")  # Fixed: likely 'Account' not 'account'
                })
        
        return {
            'count': len(undead_characters),
            'characters': undead_characters
        }
    
    def _analyze_cannot_be_frozen(self):
        """
        Analyze characters achieving Cannot Be Frozen through multiple Half Freeze Duration sources
        Based on the working implementation from github-home-parts.py
        """
        from collections import Counter
        
        character_counts = Counter()
        source_counts = Counter()
        cbf_absent_count = 0
        cbf_absent_characters = []  # Track characters who lack CBF

        for char_data in self.all_characters:
            if not isinstance(char_data, dict):
                continue

            half_freeze_sources = 0
            has_cbf = False

            for item in char_data.get("Equipped", []):
                title = item.get("Title", "Unknown")
                item_tagged = False

                for prop in item.get("PropertyList", []):
                    prop_lower = prop.lower()
                    if "half freeze duration" in prop_lower:
                        half_freeze_sources += 1
                        source_counts[title] += 1
                        item_tagged = True
                        break
                    if "cannot be frozen" in prop_lower:
                        has_cbf = True

                if not item_tagged:
                    for socket in item.get("Sockets", []):
                        socket_title = socket.get("Title", "Unknown")
                        for prop in socket.get("PropertyList", []):
                            prop_lower = prop.lower()
                            if "half freeze duration" in prop_lower:
                                half_freeze_sources += 1
                                source_counts[socket_title] += 1
                                item_tagged = True
                                break
                            if "cannot be frozen" in prop_lower:
                                has_cbf = True
                        if item_tagged:
                            break

            if half_freeze_sources == 1:
                character_counts["1_source"] += 1
            elif half_freeze_sources >= 2:
                character_counts["2_or_more_sources"] += 1
                if not has_cbf:
                    cbf_absent_count += 1
                    name = char_data.get("Name", "Unknown")
                    account = char_data.get("Account", char_data.get("account", ""))
                    level = char_data.get("Stats", {}).get("Level", "N/A")
                    char_class = char_data.get("Class", "Unknown")
                    cbf_absent_characters.append((name, account, level, char_class))

        return {
            'character_counts': character_counts,
            'source_counts': source_counts,
            'cbf_absent_count': cbf_absent_count,
            'cbf_absent_characters': cbf_absent_characters
        }
    
    def analyze_level_distribution(self):
        """Analyze level distribution patterns"""
        level_ranges = {
            '80-85': 0, '86-90': 0, '91-95': 0, '96-99': 0, '99': 0
        }
        
        for char in self.all_characters:
            if not isinstance(char, dict):
                continue
                
            level = char.get("level", 0)
            
            if 80 <= level <= 85:
                level_ranges['80-85'] += 1
            elif 86 <= level <= 90:
                level_ranges['86-90'] += 1
            elif 91 <= level <= 95:
                level_ranges['91-95'] += 1
            elif 96 <= level <= 98:
                level_ranges['96-99'] += 1
            elif level == 99:
                level_ranges['99'] += 1
        
        return level_ranges
    
    def analyze_top_accounts(self):
        """
        Analyze top accounts and their character distribution patterns.
        Fetches fresh data from the API to analyze the top 1000 ladder characters.
        """
        def get_top_accounts_with_class(account_class_counts, class_code, min_count=2, top_n=5):
            return [
                (acct, counts)
                for acct, counts in sorted(account_class_counts.items(), key=lambda x: x[1].get(class_code, 0), reverse=True)
                if counts.get(class_code, 0) >= min_count
            ][:top_n]

        def fetch_1kladder_characters(base_ladder_url, start_page=1, end_page=5):
            """Fetch all characters from a range of ladder pages, skipping page 0 by default."""
            all_characters = []
            for page in range(start_page, end_page + 1):  # Inclusive range
                ladder_url = f"{base_ladder_url}{page}"
                print(f"Fetching {ladder_url}")
                try:
                    response = requests.get(ladder_url)
                    if response.status_code == 200:
                        ladder_data = response.json()
                        all_characters.extend(ladder_data.get("ladder", []))
                    else:
                        print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Error fetching page {page}: {e}")
            return all_characters

        # Fetch fresh ladder data from API
        base_ladder_url = "https://beta.pathofdiablo.com/api/ladder/13/0/0/"
        
        try:
            all_characters = fetch_1kladder_characters(base_ladder_url, start_page=1, end_page=5)
            all_characters = [char for char in all_characters if char.get('account')]
        except Exception as e:
            print(f"Failed to fetch ladder data: {e}")
            return {}

        if not all_characters:
            print("No character data available for top account analysis")
            return {}

        level_counter = Counter(char['level'] for char in all_characters)

        # Level 99 account analysis
        level99_accounts = defaultdict(int)
        for char in all_characters:
            if char['level'] == 99:
                level99_accounts[char['account']] += 1

        top_99s = sorted(level99_accounts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Account class distribution analysis
        account_class_counts = defaultdict(lambda: defaultdict(int))
        for char in all_characters:
            acct = char['account']
            class_code = char['charClass']  # e.g., "sor"
            account_class_counts[acct][class_code] += 1

        # Get top accounts for each class
        most_zons = get_top_accounts_with_class(account_class_counts, "ama")
        most_sins = get_top_accounts_with_class(account_class_counts, "asn")
        most_barbs = get_top_accounts_with_class(account_class_counts, "bar")
        most_druids = get_top_accounts_with_class(account_class_counts, "dru")
        most_necros = get_top_accounts_with_class(account_class_counts, "nec")
        most_pallys = get_top_accounts_with_class(account_class_counts, "pal")
        most_sorcs = get_top_accounts_with_class(account_class_counts, "sor")

        # All 7 classes analysis
        CLASS_CODES = {"ama", "asn", "bar", "dru", "nec", "pal", "sor"}
        account_class_sets = defaultdict(set)

        for char in all_characters:
            acct = char['account']
            char_class = char['charClass']
            account_class_sets[acct].add(char_class)

        complete_class_accounts = [acct for acct, classes in account_class_sets.items() if CLASS_CODES.issubset(classes)]

        # Account statistics (XP, levels, count)
        account_stats = defaultdict(lambda: {'count': 0, 'levels': 0, 'xp': 0})

        for char in all_characters:
            acct = char.get('account')
            if not acct:
                continue
            account_stats[acct]['count'] += 1
            account_stats[acct]['levels'] += char.get('level', 0)
            account_stats[acct]['xp'] += char.get('exp', 0)

        # Sort by different metrics
        sorted_by_xp = sorted(account_stats.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
        sorted_by_levels = sorted(account_stats.items(), key=lambda x: x[1]['levels'], reverse=True)[:5]
        sorted_by_count = sorted(account_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]

        return {
            'level_counter': level_counter,
            'top_99s': top_99s,
            'most_zons': most_zons,
            'most_sins': most_sins,
            'most_barbs': most_barbs,
            'most_druids': most_druids,
            'most_necros': most_necros,
            'most_pallys': most_pallys,
            'most_sorcs': most_sorcs,
            'complete_class_accounts': complete_class_accounts,
            'sorted_by_xp': sorted_by_xp,
            'sorted_by_levels': sorted_by_levels,
            'sorted_by_count': sorted_by_count
        }
    
    def analyze_rare_builds(self):
        """Identify rare or unusual build patterns"""
        # This could analyze skill combinations, unusual item combinations, etc.
        # Placeholder for future implementation
        return {}
    
    def analyze_respec_leaderboard(self, is_hardcore=False):
        """
        Fetch and analyze the respec leaderboard data from GitHub.
        Filters characters by hardcore/softcore mode using the API.
        """
        respec_url = "https://raw.githubusercontent.com/qordwasalreadytaken/PoD-History-Builder/main/respec_leaderboard.json"
        
        try:
            print(f"Fetching respec leaderboard from {respec_url}")
            response = requests.get(respec_url, timeout=10)
            response.raise_for_status()
            respec_data = response.json()
        except requests.RequestException as e:
            print(f"⚠️ Failed to fetch respec leaderboard: {e}")
            return {'characters': [], 'total_characters': 0}
        
        leaderboard = respec_data.get('leaderboard', [])
        filtered_characters = []
        
        # Check each character to determine if they're hardcore or softcore
        for entry in leaderboard:
            char_name = entry.get('character')
            if not char_name:
                continue
            
            # Query the API to get character mode
            try:
                api_url = f"https://beta.pathofdiablo.com/api/characters/{char_name}/summary"
                char_response = requests.get(api_url, timeout=5)
                
                if char_response.status_code == 200:
                    char_data = char_response.json()
                    char_is_hardcore = char_data.get('hardcore', False)
                    
                    # Include character if mode matches
                    if char_is_hardcore == is_hardcore:
                        filtered_characters.append({
                            'name': char_name,
                            'rank': entry.get('rank'),
                            'total_respecs': entry.get('total_respecs', 0),
                            'total_points_removed': entry.get('total_points_removed', 0),
                            'total_stats_removed': entry.get('total_stats_removed', 0),
                            'char_class': char_data.get('charClass', 'Unknown'),
                            'level': char_data.get('level', 0)
                        })
                        print(f"✓ Added {char_name} ({'HC' if is_hardcore else 'SC'})")
                else:
                    print(f"⚠️ Character {char_name} not found in API (status {char_response.status_code})")
            except Exception as e:
                print(f"⚠️ Error checking character {char_name}: {e}")
                continue
        
        print(f"✓ Found {len(filtered_characters)} {'hardcore' if is_hardcore else 'softcore'} characters with respecs")
        
        return {
            'characters': filtered_characters,
            'total_characters': len(filtered_characters)
        }


class FunFactsHTMLGenerator:
    """Generates HTML for the fun facts page"""
    
    @staticmethod
    def generate_full_fun_facts_page(analysis_data, timestamp, is_hardcore=False, hc_level_filter=None):
        """Generate the complete HTML for the fun facts page"""
        
        # Set up mode information
        mode = "Hardcore" if is_hardcore else "Softcore"
        mode_prefix = "hc_" if is_hardcore else "sc_"
        level_filter_text = f" (Level {hc_level_filter}+)" if hc_level_filter and is_hardcore else ""
        
        # Generate individual sections
        overview_html = FunFactsHTMLGenerator._generate_overview_section(analysis_data)
        class_1k_html = FunFactsHTMLGenerator._generate_1k_class_distribution_section(mode, mode_prefix, level_filter_text)
        top_accounts_html = FunFactsHTMLGenerator._generate_top_accounts_section(analysis_data.get('top_accounts_data', {}))
        respec_html = FunFactsHTMLGenerator._generate_respec_leaderboard_section(analysis_data.get('respec_data', {}))
        top_stats_html = FunFactsHTMLGenerator._generate_top_stats_section(analysis_data['top_stats'])
        averages_html = FunFactsHTMLGenerator._generate_averages_section(
            analysis_data['averages'], analysis_data['medians']
        )
        undead_html = FunFactsHTMLGenerator._generate_undead_section(analysis_data['undead_data'])
        cbf_html = FunFactsHTMLGenerator._generate_cbf_section(analysis_data['cbf_data'])
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PoD Fun Facts & Statistics</title>
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
                    <h1>PoD FUN FACTS & STATISTICS</h1>
                    <h2>Interesting statistics and patterns from ladder characters</h2>

                    {class_1k_html}
                    
                    <hr>
                                        
                    {overview_html}
                    
                    <hr>
                    
                    {top_accounts_html}
                    
                    <hr>
                    
                    {respec_html}
                    
                    <hr>
                  
                    {undead_html}
                    
                    <hr>
                    
                    {cbf_html}
                    
                    <hr>
                    
                    {top_stats_html}
                    
                    <hr>
                    
                    {averages_html}
                    
                </div>
                
                <div class="footer">
                    <p>PoD data current as of {timestamp}</p>
                </div>
            </div>
            
            <!-- Include your existing JavaScript -->
            <script src="js/collapsible.js"></script>
            <script src="js/navigation.js"></script>
            <script src="js/armory-popup.js"></script>
        </body>
        </html>
        """
        
        return html_content

    @staticmethod
    def _generate_overview_section(analysis_data):
        """Generate overview statistics section"""
        character_count = analysis_data['character_count']
        
        return f"""
        <h2 id="overview">
            Ladder Statistics Overview
            <a href="#overview" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Total Characters Analyzed: {character_count:,}</h3>
                <p>The analysis below includes data from all ranked ladder characters</p>
            </div>
        </div>
        """

    @staticmethod
    def _generate_1k_class_distribution_section(mode="Softcore", mode_prefix="sc_", level_filter_text=""):
        """Generate the 1K class distribution section moved from home page"""
        return f"""
        <h2 id="top-1k-class-distribution">
            Top 1,000 Ladder Class Distribution
            <a href="#top-1k-class-distribution" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>Looking at the class distribution for the ladders top 1,000 characters shows which classes are played for longer, a measure of which classes are more popular in the endgame{level_filter_text}</h3>
        <div>
            <img src="charts/{mode_prefix}1kclass_distribution.png">
        </div>
        """

    @staticmethod
    def _generate_undead_section(undead_data):
        """Generate undead characters section"""
        undead_count = undead_data['count']
        undead_characters = undead_data['characters']
        
        character_list_html = "".join(
            f"""
            <div class="character-info">
                <div class="character-link">
                    <a href="https://beta.pathofdiablo.com/armory?name={char['name']}" target="_blank">
                        {char['name']}
                    </a>
                </div>
                <div>Level {char['level']} {char['class']}</div>
                <div class="hover-trigger" data-character-name="{char['name']}"></div>
            </div>
            <div class="character">
                <div class="popup hidden"></div>
            </div>
            """ for char in undead_characters
        )
        
        return f"""
        <h2 id="undead-characters">
            Undead Characters
            <a href="#undead-characters" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>{undead_count} Characters have not died</h3>
        <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="Undead Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Undead Close" class="icon-small close-icon">
            <strong>View Undead Characters</strong>
        </button>
        <div class="content" style="display: none;">  
            <div id="undead">{character_list_html}</div>
        </div>
        """

    @staticmethod 
    def _generate_cbf_section(cbf_data):
        """Generate Cannot Be Frozen analysis section"""
        cbf_absent_count = cbf_data['cbf_absent_count']
        cbf_absent_characters = cbf_data['cbf_absent_characters']
        
        cbf_absent_html = "".join(
            f"""
            <div class="character-info">
                <div class="character-link">
                    <a href="https://beta.pathofdiablo.com/armory?name={char[0]}" target="_blank">{char[0]}</a>
                </div>
                <div>Level {char[2]} {char[3]}</div>
                <div class="hover-trigger" data-character-name="{char[0]}"></div>
            </div>
            <div class="character">
                <div class="popup hidden"></div>
            </div>
            """ for char in cbf_absent_characters
        )
        
        return f"""
        <h2 id="cbf-analysis">
            Cannot Be Frozen Analysis
            <a href="#cbf-analysis" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>{cbf_absent_count} Characters achieve Cannot Be Frozen through 2 or more sources of Half Freeze Duration</h3>
        <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="CBF Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="CBF Close" class="icon-small close-icon">
            <strong>View Characters with CBF from Multiple Sources</strong>
        </button>
        <div class="content" style="display: none;">
            <div id="cbf-missing">{cbf_absent_html}</div>
        </div>
        """

    @staticmethod
    def _generate_top_stats_section(top_stats):
        """Generate top characters by various stats section"""
        
        def generate_top_list(stat_data):
            return ''.join(
                f"""<li><a href="https://beta.pathofdiablo.com/armory?name={char['name']}" target="_blank">
                {char['name']}</a> - Level {char['level']} {char['class']} ({char['value']:,})</li>"""
                for char in stat_data
            )
        
        return f"""
        <h2 id="top-characters">
            Top Characters by Statistics
            <a href="#top-characters" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        
        <!-- Strength & Dexterity Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 Characters with the most Strength:</h3>
                <ul>{generate_top_list(top_stats.get('Strength', []))}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 Characters with the most Dexterity:</h3>
                <ul>{generate_top_list(top_stats.get('Dexterity', []))}</ul>
            </div>
        </div>

        <!-- Vitality & Energy Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 Characters with the most Vitality:</h3>
                <ul>{generate_top_list(top_stats.get('Vitality', []))}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 Characters with the most Energy:</h3>
                <ul>{generate_top_list(top_stats.get('Energy', []))}</ul>
            </div>
        </div>

        <!-- Life & Mana Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>The 5 Characters with the Most Life*:</h3>
                <ul>{generate_top_list(top_stats.get('Life', []))}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>The 5 Characters with the Most Mana*:</h3>
                <ul>{generate_top_list(top_stats.get('Mana', []))}</ul>
            </div>
        </div>
        <em>*"Most" Life and Mana values are from a snapshot in time and may or may not be affected by bonuses from BO, Oak, etc.</em>
        
        <!-- Magic Find & Gold Find Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>The 5 Characters with the Most Magic Find:</h3>
                <ul>{generate_top_list(top_stats.get('MagicFind', []))}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>The 5 Characters with the Most Gold Find:</h3>
                <ul>{generate_top_list(top_stats.get('GoldFind', []))}</ul>
            </div>
        </div>
        """

    @staticmethod
    def _generate_averages_section(averages, medians):
        """Generate averages and medians section"""
        return f"""
        <h2 id="averages-medians">
            Average & Median Statistics
            <a href="#averages-medians" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Life Statistics</h3>
                <p><strong>Average Life:</strong> {averages['life']:.2f}</p>
                <p><strong>Median Life:</strong> {medians['life']:.2f}</p>
            </div>
            <div class="fun-facts-column">
                <h3>Mana Statistics</h3>
                <p><strong>Average Mana:</strong> {averages['mana']:.2f}</p>
                <p><strong>Median Mana:</strong> {medians['mana']:.2f}</p>
            </div>
        </div>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Magic Find Statistics</h3>
                <p><strong>Average Magic Find:</strong> {averages['mf']:.2f}</p>
                <p><strong>Median Magic Find:</strong> {medians['mf']:.2f}</p>
            </div>
            <div class="fun-facts-column">
                <h3>Gold Find Statistics</h3>
                <p><strong>Average Gold Find:</strong> {averages['gf']:.2f}</p>
                <p><strong>Median Gold Find:</strong> {medians['gf']:.2f}</p>
            </div>
        </div>
        """

    @staticmethod
    def _generate_top_accounts_section(top_accounts_data):
        """Generate the top accounts analysis section based on kfun_facts_html from github-make-homes.py"""
        
        if not top_accounts_data:
            return "<p>No top accounts data available.</p>"
        
        level_counter = top_accounts_data.get('level_counter', {})
        top_99s = top_accounts_data.get('top_99s', [])
        most_zons = top_accounts_data.get('most_zons', [])
        most_sins = top_accounts_data.get('most_sins', [])
        most_barbs = top_accounts_data.get('most_barbs', [])
        most_druids = top_accounts_data.get('most_druids', [])
        most_necros = top_accounts_data.get('most_necros', [])
        most_pallys = top_accounts_data.get('most_pallys', [])
        most_sorcs = top_accounts_data.get('most_sorcs', [])
        complete_class_accounts = top_accounts_data.get('complete_class_accounts', [])
        sorted_by_xp = top_accounts_data.get('sorted_by_xp', [])
        sorted_by_levels = top_accounts_data.get('sorted_by_levels', [])
        sorted_by_count = top_accounts_data.get('sorted_by_count', [])

        return f"""
        <h2 id="top-account-stats">
            Top Account Statistics 
            <a href="#top-account-stats" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>

        <!-- Level 95+ Summary -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
            <h4>High-Level Character Counts</h4>
            <ul>
                {"".join(f"<li>Level {lvl}: {count} characters</li>" for lvl, count in level_counter.items() if lvl in [99, 98, 97, 96, 95])}
            </ul>
        </div>
        <!-- Level 99 Accounts -->
            <div class="fun-facts-column">
        <h4>Top Accounts by Number of Level 99 Characters</h4>
        <ul>
            {"".join(
                f"<li><a href='https://beta.pathofdiablo.com/ladder?account/{acct}'>{acct}</a>: {count} characters at level 99</li>"
                for acct, count in top_99s
            )}
        </ul> 
       </div></div>

        <!-- Per-Class Top 5 Lists -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with multiple Amazons in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('ama', 0)} Amazons</li>" for acct, count in most_zons)}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Accounts with multiple Assassins in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('asn', 0)} Assassins</li>" for acct, count in most_sins)}</ul>
            </div>
        </div>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with multiple Barbarians in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('bar', 0)} Barbarians</li>" for acct, count in most_barbs)}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Accounts with multiple Druids in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('dru', 0)} Druids</li>" for acct, count in most_druids)}</ul>
            </div>
        </div>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with multiple Necromancers in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('nec', 0)} Necromancers</li>" for acct, count in most_necros)}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Accounts with multiple Paladins in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('pal', 0)} Paladins</li>" for acct, count in most_pallys)}</ul>
            </div>
        </div>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with multiple Sorceresses in the top 1K</h3>
                <ul>{"".join(f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {count.get('sor', 0)} Sorceresses</li>" for acct, count in most_sorcs)}</ul>
            </div>
        </div>

        <!-- All 7 Classes -->
        <h3>Accounts with all 7 classes in the top 1K: {len(complete_class_accounts)}</h3>
        <p>{", ".join(f"<a href='https://beta.pathofdiablo.com/ladder?account={acct}'>{acct}</a>" for acct in complete_class_accounts[:5])}</p>

        <!-- XP / Level / Count -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with the most experience</h3>
                    <ul>
                        {"".join(
                            f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {stats['xp']:,} XP, {stats['count']} chars, avg level {stats['levels']/stats['count']:.2f}</li>"
                            for acct, stats in sorted_by_xp
                        )}
                    </ul>
           </div>
            <div class="fun-facts-column">
                <h3>Accounts with the most Levels</h3>
                    <ul>
                        {"".join(
                            f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {stats['levels']} levels, {stats['count']} chars, avg level {stats['levels']/stats['count']:.2f}</li>"
                            for acct, stats in sorted_by_levels
                        )}
                    </ul>
            </div>
        </div>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Accounts with the most characters in the top 1K</h3>
                    <ul>
                        {"".join(
                            f"<li><a href='https://beta.pathofdiablo.com/account/{acct}'>{acct}</a>: {stats['count']} characters, total level {stats['levels']}, avg level {stats['levels']/stats['count']:.2f}</li>"
                            for acct, stats in sorted_by_count
                        )}
                    </ul>
            </div>
        </div>
        """

    @staticmethod
    def _generate_respec_leaderboard_section(respec_data):
        """Generate the respec leaderboard section"""
        
        if not respec_data or not respec_data.get('characters'):
            return "<p>No respec data available.</p>"
        
        characters = respec_data.get('characters', [])
        
        return f"""
        <h2 id="respec-leaderboard">
            Most Respecs / Tokens Used
            <a href="#respec-leaderboard" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <p>Characters who have used the most respec tokens to reset their skills and stats.</p>
        
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top Respecced Characters</h3>
                <ul>
                    {"".join(
                        f'''<li>
                            <a href="https://beta.pathofdiablo.com/armory?name={char['character']}" target="_blank">{char['character']}</a>: 
                            {char['total_respecs']} respecs 
                            ({char['total_points_removed']} skill points, {char['total_stats_removed']} stat points reset)
                        </li>'''
                        for char in characters
                    )}
                </ul>
            </div>
        </div>
        """


def generate_fun_facts_page(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """Main function to generate the complete fun facts page"""
    
    # Generate the 1K class distribution chart 
    level_filter_text = f" (Level {hc_level_filter}+)" if hc_level_filter and is_hardcore else ""
    
    # Fetch 1K ladder data and generate chart
    try:
        top_1k_characters = fetch_1k_ladder_characters(is_hardcore, hc_level_filter)
        top_1k_class_counts = analyze_api_class_distribution(top_1k_characters)
        HomePageGenerator.generate_class_distribution_chart(top_1k_class_counts, "1k", level_filter_text, is_hardcore)
        print("✓ Generated 1K class distribution chart for fun facts page")
    except Exception as e:
        print(f"⚠️ Warning: Failed to generate 1K chart for fun facts page: {e}")
    
    # Analyze fun facts data
    analyzer = FunFactsAnalyzer(all_characters)
    analysis_data = analyzer.analyze_fun_facts()
    
    # Generate HTML
    html_generator = FunFactsHTMLGenerator()
    html_content = html_generator.generate_full_fun_facts_page(analysis_data, timestamp, is_hardcore, hc_level_filter)
    
    return html_content