"""
Charm Analysis Page Generator
Generates HTML for the charm analysis page
"""

from typing import Dict, List, Any


def generate_standard_javascript():
    """Generate standard JavaScript for collapsibles and character popups"""
    return """
    <script>
        // Collapsible functionality
        var coll = document.getElementsByClassName("collapsible");
        var i;

        for (i = 0; i < coll.length; i++) {
            coll[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.display === "block") {
                    content.style.display = "none";
                } else {
                    content.style.display = "block";
                }
                
                // Toggle icons
                var openIcon = this.querySelector('.open-icon');
                var closeIcon = this.querySelector('.close-icon');
                if (openIcon && closeIcon) {
                    openIcon.classList.toggle('hidden');
                    closeIcon.classList.toggle('hidden');
                }
            });
        }

        // Character popup functionality
        document.addEventListener('DOMContentLoaded', function() {
            const hoverTriggers = document.querySelectorAll('.hover-trigger');
            
            hoverTriggers.forEach(trigger => {
                trigger.addEventListener('mouseenter', function() {
                    const characterName = this.getAttribute('data-character-name');
                    const popup = this.nextElementSibling.querySelector('.popup');
                    
                    if (popup && !popup.classList.contains('loaded')) {
                        fetch(`https://beta.pathofdiablo.com/armory?name=${characterName}`)
                            .then(response => response.text())
                            .then(html => {
                                popup.innerHTML = html;
                                popup.classList.add('loaded');
                                popup.classList.remove('hidden');
                            })
                            .catch(error => {
                                console.error('Error loading character data:', error);
                            });
                    } else if (popup) {
                        popup.classList.remove('hidden');
                    }
                });
                
                trigger.addEventListener('mouseleave', function() {
                    const popup = this.nextElementSibling.querySelector('.popup');
                    if (popup) {
                        setTimeout(() => {
                            popup.classList.add('hidden');
                        }, 200);
                    }
                });
            });
        });
    </script>
    """


class CharmAnalysisHTMLGenerator:
    """Generates HTML for the charm analysis page"""
    
    @staticmethod
    def generate_full_charm_page(analysis_data: Dict[str, Any], ladder_type: str, timestamp: str) -> str:
        """
        Generate the complete HTML for the charm analysis page
        
        Args:
            analysis_data: Dictionary containing all charm analysis data
            ladder_type: 'sc' or 'hc' for softcore/hardcore
            timestamp: Timestamp string for the footer
        """
        ladder_display = "Softcore" if ladder_type == 'sc' else "Hardcore"
        
        # Generate individual sections
        overview_html = CharmAnalysisHTMLGenerator._generate_overview_section(
            analysis_data.get('overview', {})
        )
        
        top_characters_html = CharmAnalysisHTMLGenerator._generate_top_characters_section(
            analysis_data.get('top_characters', {}),
            ladder_type
        )
        
        skillers_html = CharmAnalysisHTMLGenerator._generate_skillers_section(
            analysis_data.get('skillers', {})
        )
        
        small_charms_html = CharmAnalysisHTMLGenerator._generate_small_charms_section(
            analysis_data.get('small_charms', {})
        )
        
        large_charms_html = CharmAnalysisHTMLGenerator._generate_large_charms_section(
            analysis_data.get('large_charms', {})
        )
        
        grand_charms_html = CharmAnalysisHTMLGenerator._generate_grand_charms_section(
            analysis_data.get('grand_charms', {})
        )
        
        rare_finds_html = CharmAnalysisHTMLGenerator._generate_rare_finds_section(
            analysis_data.get('rare_finds', {})
        )
        
        # Combine into full page
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PoD Charm Analysis - {ladder_display}</title>
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
                    <h1>PoD CHARM ANALYSIS - {ladder_display.upper()}</h1>
                    <h2>Comprehensive analysis of charm usage patterns from ladder characters</h2>
                    
                    {overview_html}
                    
                    <hr>
                    
                    {top_characters_html}
                    
                    <hr>
                    
                    {skillers_html}
                    
                    <hr>
                    
                    {small_charms_html}
                    
                    <hr>
                    
                    {large_charms_html}
                    
                    <hr>
                    
                    {grand_charms_html}
                    
                    <hr>
                    
                    {rare_finds_html}
                    
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
    def _generate_overview_section(overview_data: Dict[str, Any]) -> str:
        """Generate HTML for overview section"""
        total_chars = overview_data.get('total_characters', 0)
        total_charms = overview_data.get('total_charms', 0)
        small_count = overview_data.get('small_count', 0)
        large_count = overview_data.get('large_count', 0)
        grand_count = overview_data.get('grand_count', 0)
        chars_with_charms = overview_data.get('chars_with_charms', 0)
        
        avg_charms_per_char = total_charms / chars_with_charms if chars_with_charms > 0 else 0
        
        return f"""
        <h2 id="charm-overview">
            Charm Usage Overview
            <a href="#charm-overview" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <div class="intro-section">
            <p><strong>Total Characters:</strong> {total_chars:,}</p>
            <p><strong>Characters Using Charms:</strong> {chars_with_charms:,} ({chars_with_charms/total_chars*100:.1f}%)</p>
            <p><strong>Total Active Charms:</strong> {total_charms:,}</p>
            <p><strong>Average Charms per Character:</strong> {avg_charms_per_char:.1f}</p>
            
            <h3>Charm Distribution by Size:</h3>
            <ul>
                <li><strong>Small Charms:</strong> {small_count:,} ({small_count/total_charms*100:.1f}%)</li>
                <li><strong>Large Charms:</strong> {large_count:,} ({large_count/total_charms*100:.1f}%)</li>
                <li><strong>Grand Charms:</strong> {grand_count:,} ({grand_count/total_charms*100:.1f}%)</li>
            </ul>
        </div>
        """
    
    @staticmethod
    def _generate_top_characters_section(top_chars_data: Dict[str, Any], ladder_type: str) -> str:
        """Generate HTML for top 5 characters by various metrics"""
        
        # Determine class prefix for hardcore
        class_prefix = "hc" if ladder_type == 'hc' else ""
        
        def format_character_list(char_list: List[Dict], metric_name: str, metric_key: str, extra_info_key: str = None):
            """Helper to format a character list"""
            if not char_list:
                return "<p>No data available.</p>"
            
            html = "<ol>"
            for char in char_list[:5]:  # Top 5 only
                name = char.get('name', 'Unknown')
                char_class = char.get('class', 'Unknown')
                level = char.get('level', 0)
                metric_value = char.get(metric_key, 0)
                
                extra_info = ""
                if extra_info_key and extra_info_key in char:
                    extra_info = f" (+{char[extra_info_key]} {extra_info_key.replace('_', ' ')})"
                
                html += f"""
                <li>
                    <a href="https://trends.pathofdiablo.com/{class_prefix}{char_class}#{name}" target="_blank">{name}</a>
                    ({char_class} Lvl {level}) - {metric_value:,} {metric_name}{extra_info}
                </li>
                """
            html += "</ol>"
            return html
        
        # Generate individual metric sections
        most_life_html = format_character_list(
            top_chars_data.get('most_life', []), '+Life', 'total_life'
        )
        
        most_resists_html = format_character_list(
            top_chars_data.get('most_resists', []), 'Total Resists', 'total_resists'
        )
        
        most_max_dmg_html = format_character_list(
            top_chars_data.get('most_max_damage', []), '+Max Damage', 'total_max_dmg', 'total_ar'
        )
        
        most_ar_html = format_character_list(
            top_chars_data.get('most_ar', []), '+Attack Rating', 'total_ar', 'total_max_dmg'
        )
        
        most_mf_html = format_character_list(
            top_chars_data.get('most_mf', []), '% MF', 'total_mf'
        )
        
        return f"""
        <h2 id="top-characters">
            Top Characters by Charm Stats
            <a href="#top-characters" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible runewords-button">
            <img src="icons/Special_click.png" alt="Top Characters Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Top Characters Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="top-chars" class="container">
                <div class="column">
                    <h3>Most +Life from Charms:</h3>
                    {most_life_html}
                </div>
                <div class="column">
                    <h3>Most Total Resists (incl. Anni/Torch):</h3>
                    {most_resists_html}
                </div>
            </div>
            
            <div id="top-chars-combat" class="container">
                <div class="column">
                    <h3>Most +Max Damage from Charms:</h3>
                    {most_max_dmg_html}
                </div>
                <div class="column">
                    <h3>Most +Attack Rating from Charms:</h3>
                    {most_ar_html}
                </div>
            </div>
            
            <div id="top-chars-mf">
                <h3>Most Magic Find from Charms:</h3>
                {most_mf_html}
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_skillers_section(skillers_data: Dict[str, Any]) -> str:
        """Generate HTML for skillers section"""
        total_skillers = skillers_data.get('total_skillers', 0)
        by_class = skillers_data.get('by_class', {})
        by_tree = skillers_data.get('by_tree', [])
        
        # Generate class breakdown
        class_html = "<ul>"
        for char_class, count in sorted(by_class.items(), key=lambda x: x[1], reverse=True):
            pct = count / total_skillers * 100 if total_skillers > 0 else 0
            class_html += f"<li><strong>{char_class}:</strong> {count:,} ({pct:.1f}%)</li>"
        class_html += "</ul>"
        
        # Generate most popular trees (by_tree is already a list of tuples)
        if isinstance(by_tree, dict):
            top_trees = sorted(by_tree.items(), key=lambda x: x[1], reverse=True)[:15]
        else:
            top_trees = by_tree[:15]
        
        trees_html = "<ol>"
        for tree_name, count in top_trees:
            trees_html += f"<li><strong>{tree_name}:</strong> {count:,}</li>"
        trees_html += "</ol>"
        
        return f"""
        <h2 id="skillers">
            Skiller Grand Charms
            <a href="#skillers" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible uniques-button">
            <img src="icons/Special_click.png" alt="Skillers Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Skillers Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <p><strong>Total Skillers in Use:</strong> {total_skillers:,}</p>
            
            <div id="skillers-content" class="container">
                <div class="column">
                    <h3>Skillers by Class:</h3>
                    {class_html}
                </div>
                <div class="column">
                    <h3>Top 15 Skill Trees:</h3>
                    {trees_html}
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_small_charms_section(small_charms_data: Dict[str, Any]) -> str:
        """Generate HTML for small charms section"""
        total_count = small_charms_data.get('total_count', 0)
        top_combos = small_charms_data.get('top_combos', [])
        top_properties = small_charms_data.get('top_properties', [])
        
        # Top combinations
        combos_html = "<ol>"
        for combo, count in top_combos[:15]:
            combos_html += f"<li>{combo}: <strong>{count}</strong></li>"
        combos_html += "</ol>"
        
        # Top individual properties
        props_html = "<ol>"
        for prop, count in top_properties[:15]:
            props_html += f"<li>{prop}: <strong>{count}</strong></li>"
        props_html += "</ol>"
        
        return f"""
        <h2 id="small-charms">
            Small Charms
            <a href="#small-charms" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Small Charms Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Small Charms Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <p><strong>Total Small Charms:</strong> {total_count:,}</p>
            
            <div id="small-charms-content" class="container">
                <div class="column">
                    <h3>Top 15 Property Combinations:</h3>
                    {combos_html}
                </div>
                <div class="column">
                    <h3>Top 15 Individual Properties:</h3>
                    {props_html}
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_large_charms_section(large_charms_data: Dict[str, Any]) -> str:
        """Generate HTML for large charms section"""
        total_count = large_charms_data.get('total_count', 0)
        top_combos = large_charms_data.get('top_combos', [])
        top_properties = large_charms_data.get('top_properties', [])
        
        # Top combinations
        combos_html = "<ol>"
        for combo, count in top_combos[:15]:
            combos_html += f"<li>{combo}: <strong>{count}</strong></li>"
        combos_html += "</ol>"
        
        # Top individual properties
        props_html = "<ol>"
        for prop, count in top_properties[:15]:
            props_html += f"<li>{prop}: <strong>{count}</strong></li>"
        props_html += "</ol>"
        
        return f"""
        <h2 id="large-charms">
            Large Charms
            <a href="#large-charms" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Large Charms Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Large Charms Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <p><strong>Total Large Charms:</strong> {total_count:,}</p>
            
            <div id="large-charms-content" class="container">
                <div class="column">
                    <h3>Top 15 Property Combinations:</h3>
                    {combos_html}
                </div>
                <div class="column">
                    <h3>Top 15 Individual Properties:</h3>
                    {props_html}
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_grand_charms_section(grand_charms_data: Dict[str, Any]) -> str:
        """Generate HTML for grand charms section (non-skillers)"""
        total_count = grand_charms_data.get('total_count', 0)
        top_combos = grand_charms_data.get('top_combos', [])
        top_properties = grand_charms_data.get('top_properties', [])
        
        # Top combinations
        combos_html = "<ol>"
        for combo, count in top_combos[:15]:
            combos_html += f"<li>{combo}: <strong>{count}</strong></li>"
        combos_html += "</ol>"
        
        # Top individual properties
        props_html = "<ol>"
        for prop, count in top_properties[:15]:
            props_html += f"<li>{prop}: <strong>{count}</strong></li>"
        props_html += "</ol>"
        
        return f"""
        <h2 id="grand-charms">
            Grand Charms (Non-Skillers)
            <a href="#grand-charms" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Grand Charms Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Grand Charms Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <p><strong>Total Grand Charms (Non-Skillers):</strong> {total_count:,}</p>
            
            <div id="grand-charms-content" class="container">
                <div class="column">
                    <h3>Top 15 Property Combinations:</h3>
                    {combos_html}
                </div>
                <div class="column">
                    <h3>Top 15 Individual Properties:</h3>
                    {props_html}
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_rare_finds_section(rare_finds_data: Dict[str, Any]) -> str:
        """Generate HTML for rare finds and interesting facts section"""
        
        interesting_finds = rare_finds_data.get('interesting_finds', [])
        
        # Generate list of interesting finds
        finds_html = ""
        if interesting_finds:
            finds_html = "<ul>"
            for find in interesting_finds:
                finds_html += f"<li>{find}</li>"
            finds_html += "</ul>"
        else:
            finds_html = "<p>No rare finds to display yet.</p>"
        
        return f"""
        <h2 id="rare-finds">
            Rare Finds & Fun Facts
            <a href="#rare-finds" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special_click.png" alt="Rare Finds Open" class="icon open-icon hidden">
            <img src="icons/Special.png" alt="Rare Finds Close" class="icon close-icon">
        </button>
        <div class="content" style="display: none;">
            <div id="rare-finds-content">
                <h3>Interesting Charm Discoveries:</h3>
                {finds_html}
            </div>
        </div>
        """
