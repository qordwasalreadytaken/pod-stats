"""
Streamlined Home Page Module
Generates a focused home page with class distribution, ladder summary, and navigation to specialized pages
"""

import matplotlib
matplotlib.use('Agg')  # Use Anti-Grain Geometry backend
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from datetime import datetime
from collections import Counter
import json
import requests
from modules.shared_utils import (
    load_character_data, 
    get_ladder_summary_html, 
    generate_standard_html_head,
    generate_standard_navigation,
    generate_standard_javascript,
    generate_test_banner
)


def get_current_season():
    """Get the current season from the API"""
    url = "https://beta.pathofdiablo.com/api/ladder-summaries"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        seasons = response.json()
        current = next((s["season"] for s in seasons if s.get("current")), None)
        return current
    except requests.RequestException as e:
        print(f"Error fetching season: {e}")
        return None


def fetch_1k_ladder_characters(is_hardcore=False, level_filter=None):
    """Fetch top 1,000 characters from the API"""
    season = get_current_season()
    game_mode = 1 if is_hardcore else 0  # 0 = softcore, 1 = hardcore
    
    if season:
        base_ladder_url = f"https://beta.pathofdiablo.com/api/ladder/{season}/{game_mode}/0/"
    else:
        # Fallback to season 13
        base_ladder_url = f"https://beta.pathofdiablo.com/api/ladder/13/{game_mode}/0/"
    
    print(f"Fetching 1K ladder data from API: {base_ladder_url}")
    
    all_characters = []
    # Fetch pages 1-5 to get top 1,000 characters (200 per page)
    for page in range(1, 6):
        ladder_url = f"{base_ladder_url}{page}"
        try:
            response = requests.get(ladder_url, timeout=10)
            if response.status_code == 200:
                ladder_data = response.json()
                characters = ladder_data.get("ladder", [])
                all_characters.extend(characters)
                print(f"✓ Fetched page {page}: {len(characters)} characters")
            else:
                print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
        except requests.RequestException as e:
            print(f"⚠️ Error fetching page {page}: {e}")
    
    print(f"Total 1K characters fetched: {len(all_characters)}")
    
    # Apply level filtering if specified for hardcore
    if level_filter and is_hardcore:
        filtered_chars = []
        for char in all_characters:
            if isinstance(char, dict) and char.get('level', 0) >= level_filter:
                filtered_chars.append(char)
        print(f"After level {level_filter}+ filter: {len(filtered_chars)} characters")
        all_characters = filtered_chars
    
    return all_characters


def analyze_api_class_distribution(api_characters):
    """Analyze class distribution from API character data"""
    class_counts = Counter()
    
    for char_data in api_characters:
        if not isinstance(char_data, dict):
            continue
        # API uses 'charClass' field with short codes like 'sor', 'pal', etc.
        char_class_code = char_data.get("charClass", "unknown")
        
        # Map API class codes to full names
        class_name_map = {
            "ama": "Amazon",
            "asn": "Assassin", 
            "bar": "Barbarian",
            "dru": "Druid",
            "nec": "Necromancer",
            "pal": "Paladin",
            "sor": "Sorceress"
        }
        
        char_class = class_name_map.get(char_class_code, char_class_code.capitalize())
        class_counts[char_class] += 1
        
    return class_counts


class HomePageAnalyzer:
    def __init__(self, all_characters, level_filter=None):
        self.all_characters = all_characters
        self.level_filter = level_filter
        
    def filter_characters_by_level(self, characters):
        """Filter characters by minimum level if level_filter is set"""
        if not self.level_filter:
            return characters
            
        filtered = []
        for char_data in characters:
            if not isinstance(char_data, dict):
                continue
            # Level is stored in Stats.Level
            if 'Stats' in char_data and isinstance(char_data['Stats'], dict):
                char_level = char_data['Stats'].get('Level', 0)
                if isinstance(char_level, (int, float)) and char_level >= self.level_filter:
                    filtered.append(char_data)
        return filtered
        
    def get_top_1000_characters(self, is_hardcore=False):
        """Get the top 1,000 characters from the API"""
        # Fetch fresh data from the API for the 1K chart
        api_characters = fetch_1k_ladder_characters(is_hardcore, self.level_filter)
        return api_characters
        
    def get_all_characters_filtered(self):
        """Get all characters with level filtering applied"""
        return self.filter_characters_by_level(self.all_characters)
        
    def analyze_class_distribution(self, character_subset=None):
        """Analyze class distribution for charts"""
        chars_to_analyze = character_subset if character_subset is not None else self.all_characters
        class_counts = Counter()
        
        for char_data in chars_to_analyze:
            if not isinstance(char_data, dict):
                continue
            char_class = char_data.get("Class", "Unknown")
            class_counts[char_class] += 1
            
        return class_counts
    
    def get_basic_stats(self):
        """Get basic statistics for the overview"""
        total_characters = len(self.all_characters)
        
        # Count characters by level ranges using Stats.Level
        level_99_count = sum(1 for char in self.all_characters 
                           if isinstance(char, dict) and 'Stats' in char 
                           and isinstance(char['Stats'], dict)
                           and char['Stats'].get('Level') == 99)
        
        # Count characters with mercenaries
        chars_with_mercs = sum(1 for char in self.all_characters 
                             if isinstance(char, dict) and char.get("MercenaryType"))
        
        return {
            'total_characters': total_characters,
            'level_99_count': level_99_count,
            'chars_with_mercs': chars_with_mercs
        }


class HomePageGenerator:
    @staticmethod
    def generate_class_distribution_chart(class_counts, chart_type="all", level_filter_text="", is_hardcore=False):
        """Generate class distribution pie chart"""
        classes = list(class_counts.keys())
        counts = list(class_counts.values())
        total = sum(counts)
        
        if total == 0:  # Handle empty dataset
            print(f"Warning: No characters found for {chart_type} chart")
            return f"charts/{chart_type}_class_distribution.png"
        
        # Load custom font
        try:
            # Use absolute path from project root to handle archive generation
            import os
            current_dir = os.getcwd()
            # If we're in an archive subdirectory, go back to root
            if 'Season' in current_dir:
                font_path = '../../../armory/font/avqest.ttf'
            else:
                font_path = 'armory/font/avqest.ttf'
            armory = FontProperties(fname=font_path)
        except:
            armory = FontProperties()  # Fallback to default font
        
        def make_autopct(values):
            def my_autopct(pct):
                absolute = int(pct/100.*total)
                return f'{pct:.1f}%\n({absolute:,})'
            return my_autopct
        
        # Class color mapping (hex format for matplotlib)
        class_color_map = {
            "Amazon": "#FF6669",      # Amazon - Red (rgb(255, 102, 105))
            "Assassin": "#FFFFFF",    # Assassin - White (rgb(255, 255, 255))
            "Barbarian": "#966920",   # Barbarian - Brown (rgb(150, 105, 32))
            "Druid": "#FFBA4A",       # Druid - Orange (rgb(255, 186, 74))
            "Necromancer": "#B3FFFD", # Necromancer - Cyan (rgb(179, 255, 253))
            "Paladin": "#FFF370",     # Paladin - Yellow (rgb(255, 243, 112))
            "Sorceress": "#BC6BFF"    # Sorceress - Lavender (rgb(188, 107, 255))
        }
        
        colors = [class_color_map.get(class_code, "#808080") for class_code in classes]
        
        # Timestamp for title
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Set figure size with explicit facecolor
        fig = plt.figure(figsize=(22, 22), facecolor='none')
        ax = fig.gca()
        ax.set_facecolor('none')
        plt.subplots_adjust(top=0.5, bottom=0.15)
        
        # Create the pie chart
        wedges, texts, autotexts = plt.pie(
            counts, labels=classes, autopct=make_autopct(counts), startangle=250, 
            colors=colors, radius=1.4, 
            textprops={'fontsize': 30, 'color': 'white', 'fontproperties': armory}
        )
        
        # Explicitly set wedge colors to ensure they're not converted to grayscale
        for i, wedge in enumerate(wedges):
            wedge.set_facecolor(colors[i])
            wedge.set_edgecolor('none')
        
        # Generate appropriate title based on chart type
        if chart_type == "1k":
            chart_title = f"Class Distribution of top 1,000 ladder characters{level_filter_text}"
        else:
            chart_title = f"Class Distribution of all {total:,} characters with a ladder ranking{level_filter_text}"
            
        title = plt.title(
            f"{chart_title}\n\nAs of {timestamp}", 
            pad=50, fontsize=40, fontproperties=armory, loc='left', color="white"
        )
        title.set_fontsize(45)
        
        for text in texts:
            text.set_fontsize(35)  # Class labels
        for autotext in autotexts:
            autotext.set_fontsize(25)  # Percentages on slices
            autotext.set_color('black')
        
        plt.axis('equal')  # Ensures the pie chart is circular
        
        # Save the plot with transparent background
        mode_prefix = "hc_" if is_hardcore else "sc_"
        if chart_type == "1k":
            chart_filename = f"charts/{mode_prefix}1kclass_distribution.png"
        else:
            chart_filename = f"charts/{mode_prefix}class_distribution.png"
            
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight', transparent=True, 
                    facecolor='none', edgecolor='none', format='png')
        
        print(f"Plot saved as {chart_filename}")
        
        # Display the plot
#        plt.show()
        plt.close()  # Close the figure to free memory
        
        return chart_filename

    @staticmethod
    def generate_teaser_fun_facts(all_characters):
        """Generate a small teaser of fun facts to encourage visiting the full page"""
        # Count undead characters
        undead_count = sum(1 for char in all_characters 
                          if isinstance(char, dict) and char.get("deaths", 0) == 0)
        
        # Get highest level character
        highest_level = 0
        highest_char = None
        for char in all_characters:
            if isinstance(char, dict):
                level = char.get("level", 0)
                if level > highest_level:
                    highest_level = level
                    highest_char = char
        
        # Count level 99 characters
        level_99_count = sum(1 for char in all_characters 
                           if isinstance(char, dict) and char.get("level") == 99)
        
        return f"""
        <h3 id="quick-facts">Quick Fun Facts <a href="#quick-facts" class="anchor-link"><img src="icons/anchor.png" alt="🔗" class="anchor-icon"></a></h3>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h4>{undead_count} characters have never died</h4>
                <h4>{level_99_count} characters have reached level 99</h4>
            </div>
            <div class="fun-facts-column">
                {f'<h4>Highest level character: <a href="https://beta.pathofdiablo.com/armory?name={highest_char["name"]}" target="_blank">{highest_char["name"]}</a> (Level {highest_level})</h4>' if highest_char else '<h4>No character data available</h4>'}
                <h4><a href="FunFacts">View all fun facts and statistics →</a></h4>
            </div>
        </div>
        """

    @staticmethod
    def generate_navigation_cards(is_hardcore=False):
        """Generate navigation cards to other sections"""
        hc_prefix = "hc" if is_hardcore else ""
        
        return f"""
        <div class="nav-section">
            <h3>Miscellaneous Data Pages</h3>
            <div class="navigation-cards">
                
            <div class="nav-card">
                <a href="{hc_prefix}Items">
                    Equipment usage 
                </a>
            </div>

            
            <div class="nav-card">
                <a href="{hc_prefix}charms">
                    Charm analysis and usage
                </a>
            </div>

                        <div class="nav-card">
                <a href="{hc_prefix}Mercenaries">
                    Mercenary data analysis
                </a>
            </div>
            
            <div class="nav-card">
                <a href="{hc_prefix}FunFacts">
                    Fun facts and statistics
                </a>
            </div>
<!--            
            <div class="nav-card">
                <a href="{hc_prefix}Amazon">
                    <h3>Class Analysis</h3>
                    <p>Detailed breakdowns of skills, builds, and equipment for each character class</p>
                </a>
            </div>
            
            <div class="nav-card">
                <a href="{hc_prefix}Builds">
                    <h3>Specialty Builds</h3>
                    <p>Unique character builds and specialty searches</p>
                </a>
            </div>
-->
            <div class="nav-card">
                <a href="skillsearch">
                        Skill Search
                </a>
            </div>

            <div class="nav-card">
                <a href="itemsearch">
                    Item Search
                </a>
            </div>

            <div class="nav-card">
                <a href="charactersearch">
                    Character Search
                </a>
            </div>
                        
        </div>
        </br>
        """

    @staticmethod
    def generate_full_home_page(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
        """Generate the complete streamlined home page"""
        
        # Set up level filtering
        level_filter = hc_level_filter if is_hardcore and hc_level_filter else None
        level_filter_text = f" (Level {level_filter}+)" if level_filter else ""
        
        # Analyze data with level filtering
        analyzer = HomePageAnalyzer(all_characters, level_filter)
        
        # Get two distinct datasets
        # 1. Top 1K from API (for 1K chart)
        top_1k_characters = analyzer.get_top_1000_characters(is_hardcore)
        # 2. All characters from JSON file (for all chars chart)
        all_characters_filtered = analyzer.get_all_characters_filtered()
        
        # Generate class distributions for both datasets
        # Use API analysis for 1K characters (different data structure)
        top_1k_class_counts = analyze_api_class_distribution(top_1k_characters)
        # Use JSON analysis for all characters
        all_class_counts = analyzer.analyze_class_distribution(all_characters_filtered)
        
        basic_stats = analyzer.get_basic_stats()
        
        # Generate both charts
        HomePageGenerator.generate_class_distribution_chart(top_1k_class_counts, "1k", level_filter_text, is_hardcore)
        HomePageGenerator.generate_class_distribution_chart(all_class_counts, "all", level_filter_text, is_hardcore)
        
        # Generate sections
        ladder_summary = get_ladder_summary_html(game_mode=1 if is_hardcore else 0)
        navigation_cards = HomePageGenerator.generate_navigation_cards(is_hardcore)
        
        # Determine page title and mode
        mode = "Hardcore" if is_hardcore else "Softcore"
        mode_prefix = "hc_" if is_hardcore else "sc_"
        
        # Generate level filter message for HC
        level_filter_message = ""
        if is_hardcore and level_filter:
            level_filter_message = f"""
            <div class="level-filter-notice">
                <p><strong>Note:</strong> Charts below show only characters level {level_filter} and above to provide clearer hardcore endgame data.</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            {generate_standard_html_head(f"PoD {mode} Stats", "Ever wonder how many Shako's are in use? Or what the most popular Sorc skills are? This site provides information about class build trends and item details from characters on the current Path of Diablo (PoD) ladder.")}
        </head>
        <body class="special-background">
            <div class="is-clipped">
                {generate_standard_navigation()}

                <div class="banner" style="top:50px; left:10%; width:80%;">
                    ⚠️ This is a test site for PoD's Trends site. Please direct any feedback to Qord. ⚠️
                </div>

                <div class="main page-intro">
                    <h1>PoD {mode.upper()} STATS, <u>ALL</u> RANKED LADDER CHARACTERS</h1>
                    <h3>Since there are class ladders in addition to the top 1,000, and many ranked characters do not appear in the top 1k, they are included below and in the rest of the Trends reporting to get as large a data set as possible when looking at item & equipment usage and skill distribution within classes</h3>
                    {level_filter_message}
                    <!-- Embed the Plotly pie chart -->
                    <!--     <h2>Pick a class below for more detail</h2>-->
                    <!--     <iframe src="cluster_analysis_report.html"></iframe>  -->
                    <div>
                        <img src="charts/{mode_prefix}class_distribution.png">
                    </div>
                    <h3>THESE PAGES INCLUDE DATA FROM ALL AVAILABLE RANKED LADDER CHARACTERS (THE TOP 1,000 AS WELL AS THE TOP 200 FROM EACH CLASS)</h3>
                    <!--        <h3>UNLESS STATED OTHERWISE, OTHER PAGE STATS AND DATA ARE FROM THE TOP 200 CHARACTERS OF THE RELEVANT CLASS OR CLASSES</h3> -->
<!--                    <hr>
                    <h3>Class and special pages have taken character data and separated it into probable builds. As such, the groupings and associated data
                        will change regularly to reflect what is currently accurate.
                        <br> -->
<!--                        Looking at class and build pages, what you see and what it means:</h3>
                    <div>
                        <img src="charts/build-pages-legend.png">
                    </div>
                    <h3>Looking at skills you can assume that:</h3>
                    <ul style="padding-left:20px">
                     <li>If the first number is 50%, then half of the characters fall into that "build"</li>
                     <li>If the percent bar following a skill is 100% then every character in that group has points in that skill</li>
                     <li>If the percent is 100% and the total points is high that skill is likely a main skill or synergy </li>
                     <li>If the percent is 100% but the total is low that skill is likely one-point-wonder like Hydra and Whirlwind or just a prerequisite </li>
                     </ul>
                    <br>
-->                     
                    <hr>

                    {ladder_summary}
                    <br>
                     
                    <hr>
                    
                    {navigation_cards}
                    
                    <!-- Quick Overview Stats -->
                    <div class="overview-stats">

                    </div>
                    
                    <hr>
                    
                    <!-- About the Data -->
                    <div class="about-section">
                        <h3>About This Data</h3>
                        <p>This analysis includes available data from all ranked ladder characters, including:</p>
                        <ul style="list-style-type: disc; padding-left: 40px;">
                            <li>The top 1,000 overall ladder characters</li>
                            <li>The top 200 characters from each class ladder</li>
                            <li>Equipment usage and skill point allocations</li>
                            <li>Mercenary equipment and details</li>
                        </ul>
                        <p>Character data and associated pages are updated regularly to reflect current ladder standings and trends.</p>
                    </div>
                    
                    <button onclick="topFunction()" id="backToTopBtn" class="back-to-top"></button>
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


def generate_home_page(json_file_path, is_hardcore=False, hc_level_filter=None):
    """Main function to generate the streamlined home page
    
    Args:
        json_file_path: Path to the character data JSON file
        is_hardcore: Boolean indicating if this is hardcore mode
        hc_level_filter: Minimum level filter for hardcore characters (e.g., 70)
    """
    
    # Load character data
    all_characters = load_character_data(json_file_path)
    
    if not all_characters:
        print("No character data loaded. Cannot generate home page.")
        return None
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate HTML
    html_content = HomePageGenerator.generate_full_home_page(
        all_characters, timestamp, is_hardcore, hc_level_filter
    )
    
    return html_content