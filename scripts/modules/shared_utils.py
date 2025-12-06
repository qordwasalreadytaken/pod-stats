"""
Shared Utilities Module
Common functions and utilities used across multiple page modules
"""

import json
import requests
from datetime import datetime
from html import escape


def load_character_data(json_file_path):
    """Load character data from JSON file"""
    try:
        with open(json_file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading character data from {json_file_path}: {e}")
        return []


def filter_characters_by_level(characters, min_level=None):
    """Filter characters by minimum level if specified"""
    if min_level is None:
        return characters
    
    filtered_chars = []
    for char in characters:
        # Level can be in different locations depending on data source
        level = None
        if 'level' in char:
            level = char['level']
        elif 'Stats' in char and isinstance(char['Stats'], dict) and 'Level' in char['Stats']:
            level = char['Stats']['Level']
        elif 'Level' in char:
            level = char['Level']
        
        if level is not None and level >= min_level:
            filtered_chars.append(char)
    
    original_count = len(characters)
    filtered_count = len(filtered_chars)
    
    if min_level and original_count != filtered_count:
        print(f"🔍 Level filter applied: {original_count} → {filtered_count} characters (level {min_level}+)")
    
    return filtered_chars


def get_current_season():
    """Get current season from API"""
    # Temporarily hardcoded to season 13
    return "13"
    
    # Original API call (commented out temporarily)
    # try:
    #     response = requests.get("https://beta.pathofdiablo.com/api/current-season", timeout=10)
    #     response.raise_for_status()
    #     return response.json().get("season")
    # except requests.RequestException as e:
    #     print(f"Error fetching current season: {e}")
    #     return None


def get_ladder_summary_html(game_mode=0):
    """Generate ladder summary HTML with top 10 and firsts"""
    # Fetch Top 10 Characters
    season = get_current_season()
    if season:
        base_ladder_url = f"https://beta.pathofdiablo.com/api/ladder/{season}/{game_mode}/0/"
    else:
        base_ladder_url = "https://beta.pathofdiablo.com/api/ladder/13/0/0/"
    
    try:
        ladder_response = requests.get(base_ladder_url, timeout=10)
        ladder_response.raise_for_status()
        ladder_data = ladder_response.json().get("ladder", [])
        top_10 = ladder_data[:10]
    except requests.RequestException as e:
        top_10 = []
        top_10_html = f"<p>Error fetching top characters: {escape(str(e))}</p>"

    top_10_html = ['<div class="fun-facts-column">', '<h4>Top 10 Characters</h4>', '<ul>']
    for entry in top_10:
        name = escape(entry.get("charName", "Unknown"))
        level = entry.get("level", 0)
        char_class_name = escape(entry.get("charClass", "").capitalize())
        max_date = entry.get("maxLevelDate")
        date_str = f' <br>&nbsp;&nbsp;&nbsp;&nbsp;<em>(Level 99 on {datetime.strptime(max_date, "%Y-%m-%d %H:%M:%S").date()})</em>' if max_date else ""
        link = f'<a href="https://beta.pathofdiablo.com/armory?name={name}" target="_blank">{name}</a>'
        top_10_html.append(f'<li>{link} – Level {level} {char_class_name}{date_str}</li>')
    top_10_html.append('</ul></div>')

    # Fetch Ladder Firsts
    firsts_url = "https://beta.pathofdiablo.com/api/ladder-firsts"
    try:
        firsts_response = requests.get(firsts_url, timeout=10)
        firsts_response.raise_for_status()
        firsts_data = firsts_response.json()
    except requests.RequestException as e:
        firsts_data = []
        ladder_firsts_html = f"<p>Error fetching ladder firsts: {escape(str(e))}</p>"

    season_label = next((entry["season"] for entry in firsts_data if entry.get("gameMode") == game_mode), season)
    mode_label = "Hardcore" if game_mode == 1 else "Softcore"

    from collections import defaultdict
    grouped = defaultdict(list)
    for entry in firsts_data:
        if entry.get("gameMode") != game_mode:
            continue
        key = (
            escape(entry.get("charName", "Unknown")),
            entry.get("charLevel", "??"),
            escape(entry.get("charClass", "Unknown"))
        )
        difficulty = entry.get("difficulty", "Unknown")
        boss_name = escape(entry.get("bossName", "Unknown"))
        kill_desc = f"First {difficulty} {boss_name} Kill" if difficulty != "Hell" else f"First {boss_name} Kill"
        grouped[key].append(kill_desc)

    ladder_firsts_html = ['<div class="fun-facts-column">', '<h4>Ladder Firsts</h4>', '<ul style="list-style-type: none; padding-left: 0;">']
    for (raw_name, char_level, char_class), kills in grouped.items():
        link = f'<a href="https://beta.pathofdiablo.com/armory?name={escape(raw_name)}" target="_blank">{escape(raw_name)}</a>'
        line1 = f"{link} (Level {char_level} {char_class})"
        line2 = "&nbsp;&nbsp;&nbsp;&nbsp;" + " and ".join(kills)
        ladder_firsts_html.append(f"<li>{line1}<br>{line2}</li>")
    ladder_firsts_html.append('</ul></div>')

    # Wrap both in fun-facts-row
    html = [
        f"<section id='ladder-summary'>",
        f"<h2>Season {season_label} {mode_label} Ladder Highlights</h2>",
        '<div class="fun-facts-row">',
        "\n".join(top_10_html),
        "\n".join(ladder_firsts_html),
        '</div>',
        '</section>'
    ]
    return "\n".join(html)


def slugify(name):
    """Convert name to URL-friendly slug"""
    return name.lower().replace(" ", "-").replace("'", "").replace('"', "")


def generate_character_html(character_list, show_hover=True):
    """Generate standardized character list HTML"""
    if not character_list:
        return "<p>No characters found.</p>"
    
    html_parts = []
    for char in character_list:
        name = char.get("name", "Unknown")
        level = char.get("level", 0)
        char_class = char.get("class", "Unknown")
        
        hover_div = f'<div class="hover-trigger" data-character-name="{name}"></div>' if show_hover else ""
        
        html_parts.append(f"""
        <div class="character-info">
            <div class="character-link">
                <a href="https://beta.pathofdiablo.com/armory?name={name}" target="_blank">
                    {name}
                </a>
            </div>
            <div>Level {level} {char_class}</div>
            {hover_div}
        </div>
        <div class="character">
            <div class="popup hidden"></div>
        </div>
        """)
    
    return "".join(html_parts)


def generate_standard_javascript():
    """Generate the standard JavaScript used across all pages"""
    return """
    <script>
    // Collapsible elements
    var coll = document.getElementsByClassName("collapsible");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            
            // Skip if no content element found
            if (!content) return;
            
            // Handle icons - look for various alt text patterns
            var openIcon = this.querySelector("img.open-icon") || this.querySelector("img[alt='Open']") || this.querySelector("img.icon[alt='Open']");
            var closeIcon = this.querySelector("img.close-icon") || this.querySelector("img[alt='Close']") || this.querySelector("img.icon[alt='Close']");

            // Toggle content display - check if currently hidden
            if (content.style.display === "none" || content.style.display === "") {
                // Currently hidden, so expand it
                content.style.display = "block";
                // Swap icons only if both exist
                if (openIcon && closeIcon) {
                    openIcon.classList.remove("hidden");
                    closeIcon.classList.add("hidden");
                }
            } else {
                // Currently visible, so collapse it
                content.style.display = "none";
                // Swap icons only if both exist
                if (openIcon && closeIcon) {
                    openIcon.classList.add("hidden");
                    closeIcon.classList.remove("hidden");
                }
            }
        });
    }

    //Back to top button
    var backToTopBtn = document.getElementById("backToTopBtn");

    // When the user scrolls down 20px from the top of the document, show the button
    window.onscroll = function() {scrollFunction()};

    function scrollFunction() {
        if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
            backToTopBtn.style.display = "block";
        } else {
            backToTopBtn.style.display = "none";
        }
    }

    // When the user clicks on the button, scroll to the top of the document
    function topFunction() {
        document.body.scrollTop = 0; // For Safari
        document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
    }

    //Trends toolbar
    function toggleMenu() {
        const navMenu = document.querySelector('.top-buttons');
        navMenu.classList.toggle('show');
    }

    document.addEventListener("DOMContentLoaded", function () {
        const scHcButton = document.getElementById("SC_HC");
        const currentUrl = window.location.href;
        const filename = currentUrl.split("/").pop(); // Get the last part of the URL

        // Check if the current page is Hardcore or Softcore
        const isHardcore = filename.startsWith("hc");

        // Update button appearance based on current mode
        if (isHardcore) {
            scHcButton.classList.add("hardcore");
            scHcButton.classList.remove("softcore");
        } else {
            scHcButton.classList.add("softcore");
            scHcButton.classList.remove("hardcore");
        }

        // Update background image based on mode
        updateButtonImage(isHardcore);

        // Add click event to toggle between SC and HC pages
        scHcButton.addEventListener("click", function () {
            let newUrl;

            if (isHardcore) {
                // Convert HC -> SC (remove "hc" from filename)
                newUrl = currentUrl.replace(/hc(\w+)$/, "$1"); // Remove "hc"
            } else {
                // Convert SC -> HC (prepend "hc" to the filename)
                newUrl = currentUrl.replace(/\/(\w+)$/, "/hc$1"); // Prepend "hc"
            }

            // Redirect to the new page
            if (newUrl !== currentUrl) {
                window.location.href = newUrl;
            }
        });

        // Function to update button background image
        function updateButtonImage(isHardcore) {
            if (isHardcore) {
                scHcButton.style.backgroundImage = "url('icons/Hardcore_click.png')";
            } else {
                scHcButton.style.backgroundImage = "url('icons/Softcore_click.png')";
            }
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        const currentPage = window.location.pathname.split("/").pop(); // Get current page filename
        const menuItems = document.querySelectorAll(".top-button");

        menuItems.forEach(item => {
            const itemPage = item.getAttribute("href");
            if (itemPage && currentPage === itemPage) {
                item.classList.add("active");
            }
        });
    });

    //Armory pop up
    document.addEventListener("DOMContentLoaded", function () {
        let activePopup = null;

        document.querySelectorAll(".hover-trigger").forEach(trigger => {
            trigger.addEventListener("click", function (event) {
                event.stopPropagation();
                const characterName = this.getAttribute("data-character-name");

                // Close any open popup first
                if (activePopup) {
                    activePopup.classList.remove("active");
                    activePopup.innerHTML = ""; // Remove iframe for memory efficiency
                    activePopup = null;
                }

                // Find the associated popup container
                const popup = this.closest(".character-info").nextElementSibling.querySelector(".popup");

                // If this popup was already active, just close it
                if (popup === activePopup) {
                    return;
                }

                // Create an iframe and set its src
                const iframe = document.createElement("iframe");
                iframe.src = `./armory/video_component.html?charName=${encodeURIComponent(characterName)}`;
                iframe.setAttribute("id", "popupFrame");

                // Add iframe to the popup
                popup.appendChild(iframe);
                popup.classList.add("active");

                // Set this popup as the active one
                activePopup = popup;
            });
        });

        // Close the popup when clicking anywhere outside
        document.addEventListener("click", function (event) {
            if (activePopup && !activePopup.contains(event.target)) {
                activePopup.classList.remove("active");
                activePopup.innerHTML = ""; // Remove iframe to free memory
                activePopup = null;
            }
        });
    });

    //PoD nav buttons
    document.addEventListener('DOMContentLoaded', () => {
        const burger = document.querySelector('.navbar-burger');
        const menu = document.querySelector('.navbar-menu');

        burger.addEventListener('click', () => {
            menu.classList.toggle('is-active');
            burger.classList.toggle('is-active');
        });
    });

    document.addEventListener('DOMContentLoaded', () => {
        const dropdownButton = document.querySelector('.dropdown2-button');
        const dropdownContent = document.querySelector('.dropdown2-content');

        dropdownButton.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevents clicks from propagating to other elements
            dropdownContent.classList.toggle('is-active'); // Toggles the dropdown visibility
        });

        // Close the dropdown if you click anywhere outside it
        document.addEventListener('click', () => {
            if (dropdownContent.classList.contains('is-active')) {
                dropdownContent.classList.remove('is-active');
            }
        });
    });

    //Anchor in place fix
    // Expand collapsibles and scroll to anchor
    function scrollWithOffset(el, offset = -50) {
        const y = el.getBoundingClientRect().top + window.pageYOffset + offset;
        window.scrollTo({ top: y, behavior: 'smooth' });
    }

    function expandToAnchor(anchorId) {
        const target = document.getElementById(anchorId);
        if (!target) return;

        // Step 1: Collect all parent .content elements that need expanding
        const stack = [];
        let el = target;
        while (el) {
            if (el.classList?.contains('content')) {
                stack.unshift(el); // add to beginning to expand outermost first
            }
            el = el.parentElement;
        }

        // Step 2: Expand each .content section in order
        for (const content of stack) {
            const button = content.previousElementSibling;
            if (button?.classList.contains('collapsible')) {
                button.classList.add('active');
                content.style.display = "block";

                const openIcon = button.querySelector("img.open-icon");
                const closeIcon = button.querySelector("img.close-icon");
                if (openIcon) openIcon.classList.add("hidden");
                if (closeIcon) closeIcon.classList.remove("hidden");
            }
        }

        // Step 3: Delay scroll until DOM has reflowed
        setTimeout(() => {
            scrollWithOffset(target);
        }, 250); // Adjust if necessary
    }

    // Handle clicks on .anchor-link elements
    document.addEventListener('DOMContentLoaded', () => {
        // Handle clicks on .anchor-link elements
        document.querySelectorAll('.anchor-link, a[href^="#"]').forEach(link => {
            link.addEventListener('click', function (event) {
                event.preventDefault(); // Prevent default anchor behavior
                const anchorId = this.getAttribute('href').substring(1);
                const fullUrl = `${window.location.origin}${window.location.pathname}#${anchorId}`;

                navigator.clipboard.writeText(fullUrl); // Copy full link to clipboard
                history.pushState(null, '', `#${anchorId}`); // Update URL without page reload
                expandToAnchor(anchorId); // Expand and scroll
            });
        });

        // On initial load with hash
        if (window.location.hash) {
            const anchorId = window.location.hash.substring(1);
            // Wait a bit for collapsibles/content to render
            setTimeout(() => {
                expandToAnchor(anchorId);
            }, 200);
        }
    });
    </script>
    """


def generate_standard_html_head(title, description=None):
    """Generate standard HTML head section"""
    if description is None:
        description = "Path of Diablo ladder statistics and analytics"
    
    return f"""
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <meta name="keywords" content="path of diablo, builds, stats, statistics, data, analysis, analytics">
    <meta name="robots" content="index, follow">
    <title>{title}</title>
    <link rel="shortcut icon" type="image/x-icon" href="icons/pod.ico">
    <link rel="stylesheet" type="text/css" href="./css/test-css.css">
    """


def generate_test_banner():
    """Generate test site banner"""
    return """
    <div style="background-color: #ff6b6b; color: white; padding: 15px; text-align: center; font-weight: bold; border-bottom: 3px solid #c92a2a; margin-bottom: 20px;">
        ⚠️ This is a test preview of next season's display. Please direct any feedback to Qord. ⚠️
    </div>
    """


def generate_standard_navigation():
    """Generate standard navigation HTML"""
    return """
    <div id="navbar-placeholder"></div>
    <script>
    fetch("templates/navbar.html")
        .then(res => res.text())
        .then(html => {
        document.getElementById("navbar-placeholder").innerHTML = html;
        });
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
    """