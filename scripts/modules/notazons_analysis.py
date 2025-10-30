#!/usr/bin/env python3
"""
Notazons Analysis - Non-Amazon Bow Users
Analyzes characters that are not Amazons but have bolts or arrows equipped.
"""

import json
import pandas as pd
from collections import defaultdict, Counter
import plotly.express as px
from jinja2 import Template
from datetime import datetime
import os

def analyze_notazons(league="sc"):
    """Analyze non-Amazon characters using bows/crossbows"""
    
    icons_folder = "icons"
    what_class = "Notazons"
    search_tags = {"Bolts", "Arrows"}  # Use a set for faster lookups
    howmany_clusters = 6
    howmany_skills = 4

    # Load the consolidated JSON file
    # Determine path based on whether we're running from scripts/ directory or root
    import os
    current_dir = os.getcwd()
    if current_dir.endswith('/scripts/modules'):
        json_file = f"../../{league}_ladder.json"
    elif current_dir.endswith('/scripts'):
        json_file = f"../{league}_ladder.json"
    else:
        # Running from root directory
        json_file = f"{league}_ladder.json"
    
    with open(json_file, "r") as file:
        all_characters = json.load(file)

    # Filter characters based on equipped items
    filtered_characters = []
    for char_data in all_characters:
        # Exclude characters of the class "Amazon"
        if char_data.get("Class") == "Amazon":
            continue  # Skip this character

        for item in char_data.get("Equipped", []):
            if item.get("Tag") in search_tags:
                filtered_characters.append(char_data)
                break  # No need to check further items

    def map_readable_names(mercenary_type, worn_category=""):
        mercenary_mapping = {
            "Desert Mercenary": "Act 2 Desert Mercenary",
            "Rogue Scout": "Act 1 Rogue Scout",
            "Eastern Sorceror": "Act 3 Eastern Sorceror",
            "Barbarian": "Act 5 Barbarian"
        }
        worn_mapping = {
            "body": "Armor",
            "helmet": "Helmet",
            "weapon1": "Weapon",
            "weapon2": "Offhand"
        }
        readable_mercenary = mercenary_mapping.get(mercenary_type, mercenary_type)
        readable_worn = worn_mapping.get(worn_category, worn_category)
        return readable_mercenary, readable_worn

    def load_data(filtered_characters):
        all_data = []
        quality_colors = {
            "q_runeword": "#edcd74",
            "q_unique": "#edcd74",
            "q_set": "#45a823",
            "q_magic": "#7074c9",
            "q_rare": "yellow",
            "q_crafted": "orange"
        }

        for char_data in filtered_characters:
            if "SkillTabs" in char_data and "Equipped" in char_data:
                skill_data = {
                    "Name": char_data.get("Name", "Unknown"),
                    "Class": char_data.get("Class", "Unknown"),
                    "Level": char_data.get("Stats", {}).get("Level", "Unknown")
                }

                # Extract and sort skills
                skills = []
                for tab in char_data.get('SkillTabs', []):
                    for skill in tab.get('Skills', []):
                        skill_name = skill['Name']
                        skill_level = skill['Level']
                        skill_data[skill_name] = skill_level  # ✅ Creates a separate column for each skill
                        skills.append((skill_name, skill_level))
                skills_sorted = sorted(skills, key=lambda x: x[1], reverse=True)
                skill_data["Skills"] = ", ".join([f"{name}:{level}" for name, level in skills_sorted])

                # Process equipment
                equipment_titles = defaultdict(Counter)
                for item in char_data["Equipped"]:
                    worn_category = item.get("Worn", "Unknown")
                    title = item.get("Title", "Unknown")
                    quality_code = item.get("QualityCode", "default")
                    tag = item.get("Tag", "")

                    # Apply proper naming and colors
                    worn_category = {
                        "ring1": "Ring", "ring2": "Ring",
                        "sweapon1": "Left hand", "weapon1": "Left hand",
                        "sweapon2": "Offhand", "weapon2": "Offhand",
                        "body": "Armor", "gloves": "Gloves",
                        "belt": "Belt", "helmet": "Helmet",
                        "boots": "Boots", "amulet": "Amulet"
                    }.get(worn_category, worn_category)

                    # Set colored title
                    if quality_code in quality_colors:
                        color = quality_colors[quality_code]
                        if quality_code in ["q_magic", "q_rare", "q_crafted"]:
                            colored_title = f"<span style='color: {color};'>{quality_code.split('_')[1].capitalize()} {tag}</span>"
                        else:
                            colored_title = f"<span style='color: {color};'>{title}</span>"
                    else:
                        colored_title = title  # Default title if no color mapping

                    equipment_titles[worn_category][colored_title] += 1

                # Convert equipment data to a readable string
                skill_data["Equipment"] = ", ".join([
                    f"{worn}: {title} x{count}" if count > 1 else f"{worn}: {title}"
                    for worn, titles in equipment_titles.items()
                    for title, count in titles.items()
                ])

                # Process mercenary info
                mercenary_type = char_data.get("MercenaryType", "No mercenary")
                readable_mercenary, _ = map_readable_names(mercenary_type)
                mercenary_equipment = ", ".join(
                    [item.get("Title", "Unknown") for item in char_data.get("MercenaryEquipped", [])]
                ) if char_data.get("MercenaryEquipped") else "No equipment"

                skill_data["Mercenary"] = readable_mercenary
                skill_data["MercenaryEquipment"] = mercenary_equipment

                all_data.append(skill_data)

        return pd.DataFrame(all_data).fillna(0)  # Fill missing skills with 0

    # Load the data
    df = load_data(filtered_characters)
    
    if df.empty:
        print(f"No {what_class} found in {league.upper()} league")
        return

    # Define skill columns (exclude non-skill columns)
    skill_columns = [col for col in df.columns if col not in ['Name', 'Class', 'Level', 'Skills', 'Equipment', 'Mercenary', 'MercenaryEquipment']]

    # Just use Class as the cluster
    df['Cluster'] = df['Class']

    # Drop duplicates before calculating percentage-based stuff
    deduped_df = df.drop_duplicates(subset='Name')

    # Total points per character
    df['Total_Points'] = df[skill_columns].sum(axis=1)

    # Average total points per cluster (i.e., per class)
    cluster_averages = df.groupby('Cluster')['Total_Points'].mean().reset_index()
    cluster_averages.columns = ['Cluster', 'Avg_Points']
    df = pd.merge(df, cluster_averages, on='Cluster')

    # Skill averages per cluster (i.e., per class)
    skill_averages = df.groupby('Cluster')[skill_columns].mean()

    # Top skills per cluster with average points
    top_skills_with_avg = skill_averages.apply(
        lambda x: [(skill, round(x[skill], 2)) for skill in x.nlargest(howmany_skills).index],
        axis=1
    )

    # ✅ Calculate percentage of each class using deduplicated data
    cluster_counts = deduped_df['Cluster'].value_counts(normalize=True) * 100
    df['Percentage'] = df['Cluster'].map(cluster_counts)

    # Assign cluster labels
    cluster_labels = {
        class_name: ", ".join([f"{skill} ({avg})" for skill, avg in skills])
        for class_name, skills in zip(skill_averages.index, top_skills_with_avg)
    }
    df['Cluster_Label'] = df['Cluster'].map(cluster_labels)

    def analyze_mercenaries(characters):
        mercenary_counts = Counter()
        mercenary_equipment = defaultdict(lambda: defaultdict(Counter))

        for char_data in characters:
            if not isinstance(char_data, dict):
                print(f"Skipping unexpected data format: {char_data}")
                continue  # Skip invalid entries

            mercenary = char_data.get("MercenaryType")
            if mercenary:
                readable_mercenary, _ = map_readable_names(mercenary, "")
                mercenary_counts[readable_mercenary] += 1

                for item in char_data.get("MercenaryEquipped", []):
                    worn_category = item.get("Worn", "Unknown")
                    readable_mercenary, readable_worn = map_readable_names(mercenary, worn_category)
                    title = item.get("Title", "Unknown")
                    mercenary_equipment[readable_mercenary][readable_worn][title] += 1

        return mercenary, mercenary_counts, mercenary_equipment

    # Calculate the total usage of each skill across all clusters
    total_skill_usage = df[skill_columns].sum()

    # Sort skills by total usage in descending order
    most_used_skills = total_skill_usage.sort_values(ascending=False)

    # Sort skills by total usage in ascending order
    least_used_skills = total_skill_usage.sort_values(ascending=True)

    # Extract the top 5 most used skills
    top_5_most_used_skills = most_used_skills.head(5)

    # Extract the bottom 5 least used skills
    bottom_5_least_used_skills = least_used_skills.head(5)

    # Calculate the percentage of characters that have invested in each skill within the cluster
    skill_percentages = df[skill_columns].astype(bool).groupby(df['Cluster']).mean() * 100

    # Identify the top skills per cluster with their average points and percentages
    top_skills_with_avg_and_percent = skill_averages.apply(lambda x: [(skill, round(x[skill], 2), round(skill_percentages.loc[x.name, skill], 2)) for skill in x.nlargest(howmany_skills).index], axis=1)

    summary_label = ""
    summaries = []

    df = df.drop_duplicates(subset=['Name', 'Class'])
    
    # Gather data for the report
    clusters = {}
    for cluster, group in df.groupby('Cluster'):
        sorted_group = group.sort_values(by='Level', ascending=False)  # Sort by level descending
        character_count = len(sorted_group)
        cluster_percentage = cluster_counts[cluster]
        equipment_counts = {}

        # Process equipment
        for row in sorted_group.itertuples():
            equipment_list = row.Equipment.split(", ")
            for item in equipment_list:
                if item:
                    worn, title_count = item.split(": ", 1)
                    if " x" in title_count:
                        title, count = title_count.split(" x", 1)
                        count = int(count)
                    else:
                        title = title_count
                        count = 1

                    if worn not in equipment_counts:
                        equipment_counts[worn] = {}
                    if title in equipment_counts[worn]:
                        equipment_counts[worn][title] += count
                    else:
                        equipment_counts[worn][title] = count  # Initialize with real count

        # Get mercenary data for the cluster
        mercenary, mercenary_counts, mercenary_equipment = analyze_mercenaries(filtered_characters)

        # Generate HTML report for mercenaries in this cluster
        merc_count = f"<h3>Mercenary Equipment Analysis for Cluster {cluster}</h3>"
        merc_count += "<h4>Count of Mercenary Types</h4>"
        for mercenary, count in mercenary_counts.items():
            merc_count += f"<p>{mercenary}: {count}</p>"

        # Mercenary equipment titles
        merc_count += "<h4>Equipment Titles</h4>"
        for mercenary, equipment in mercenary_equipment.items():
            merc_count += f"<p><strong>{mercenary}:</strong></p>"
            for title, count in equipment.items():
                merc_count += f"<p>{title}: {count}</p>"

        # Ensure the cluster exists before adding merc_count and avoid overwrite
        if cluster not in clusters:
            clusters[cluster] = {}

        clusters[cluster].update({
            'merc_count': merc_count,
        })

        # Calculate total counts for each category
        total_counts = {
            worn: sum(titles.values())
            for worn, titles in equipment_counts.items()
        }

        # Calculate the percentages based on total counts
        equipment_percentages = {
            worn: {title: (count / total_counts[worn]) * 100 for title, count in titles.items()}
            for worn, titles in equipment_counts.items()
        }

        # Get top equipment based on count
        top_equipment = {
            worn: sorted(titles.items(), key=lambda item: item[1], reverse=True)[:5]
            for worn, titles in equipment_counts.items()
        }

        # Use equipment_percentages for display
        top_equipment_str_list = []
        for worn, titles in top_equipment.items():
            titles_str = "<br>".join([f"&nbsp;&nbsp;&nbsp;&nbsp;{title} {equipment_percentages[worn][title]:.2f}% ({count})" for title, count in titles])
            top_equipment_str_list.append(f"<strong>{worn.capitalize()}</strong>: <br>{titles_str}")

        top_equipment_str = "<br>".join(top_equipment_str_list)

        # Full display of equipment counts
        sorted_equipment_counts = {
            worn: dict(sorted(titles.items(), key=lambda item: item[1], reverse=True))
            for worn, titles in equipment_counts.items()
        }

        equipment_counts_str_list = []
        for worn, titles in sorted_equipment_counts.items():
            titles_str = ", ".join([f"{title} {equipment_percentages[worn][title]:.2f}%" for title in titles])
            equipment_counts_str_list.append(f"<strong>{worn.capitalize()}</strong>: {titles_str}")

        equipment_counts_str = "<br>".join(equipment_counts_str_list)

        # Define a helper function to format numbers
        def format_number(num):
            return int(num) if num % 1 == 0 else round(num, 2)

        # Filter top skills
        top_skills = [skill for skill, _, _ in top_skills_with_avg_and_percent[cluster]]

        # Filter other skills, ignoring those with zero points
        other_skills = skill_averages.loc[cluster].drop(top_skills)
        other_skills = other_skills[other_skills > 0].nlargest(6)
        other_skills_pie = "<br>".join([f"{skill} ({format_number(avg)})" for skill, avg in other_skills.items()])

        # Other skills display with icons
        other_skills_str = "<br>".join([
            f"<img src='{icons_folder}/{skill}.png' alt='{skill}' width='20' height='20'> "
            f"<span class='{'highlight-100' if round(skill_percentages.loc[cluster, skill], 2) == 100 else 'normal-skill'}'>"
            f"{skill} {round(skill_percentages.loc[cluster, skill], 2)}% "
            f"({format_number(other_skills[skill] * character_count)})</span>"
            for skill in other_skills.index
        ])

        # Filter remaining skills, ignoring those with zero points
        remaining_skills = skill_averages.loc[cluster].sort_values(ascending=False)
        remaining_skills = remaining_skills[remaining_skills > 0]

        remaining_skills_str_with_icons = "\n".join([
            "<div class='skills-group'>" + "\n".join([
                "<div class='skills-row'>" +
                "\n".join([
                    f"<div class='skill-item'>"
                    f"<div class='skillbar-container'>"
                    f"<div class='skill-info'>"
                    f"<img src='{icons_folder}/{skill}.png' alt='{skill}' class='skill-icon'> "
                    f"{skill} {round(skill_percentages.loc[cluster, skill], 2)}% ({format_number(remaining_skills[skill] * character_count)})"
                    f"</div>"
                    f"<div class='skill-mini-bar' style='width: {round(skill_percentages.loc[cluster, skill], 2) * 4}px;'></div>"
                    f"</div>"
                    f"</div>"
                    for skill in remaining_skills.index[row:row+2]
                ]) +
                "</div>"  # Close row
                for row in range(i, min(i+10, len(remaining_skills.index)), 2)
            ]) + "</div>"  # Close group
            for i in range(0, len(remaining_skills.index), 10)
        ])

        # Sorted summary label
        summary_labels = [skill for skill, _, _ in top_skills_with_avg_and_percent[cluster]]
        summary = f"{cluster_percentage:.2f}% of {what_class}'s invest heavily in " + ", ".join(summary_labels)

        clusters[cluster].update({
            'label': f'<div id="cluster-{cluster}">' +
                    f"{cluster_percentage:.2f}% of {what_class}'s are {cluster}'s:" +
                    f'<a href="#cluster-{cluster}" class="anchor-link">' +
                    f'<img src="icons/anchor.png" alt="🔗" class="anchor-icon"></a>' +
                    '<br>' +
                    "".join([
                f"""
                <div class="skillbar-container">
                    <div class="skill-row">
                        <img src="{icons_folder}/{skill}.png" alt="{skill}" class="skill-icon">
                        <div class="skill-bar-container">
                            <div class="skill-bar">
                                <span class="skill-label">{skill} ({int(avg * character_count)})</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                for skill, avg, percent in top_skills_with_avg_and_percent[cluster]
            ]),
            'character_count': character_count,
            'other_skills': other_skills_str,
            'other_skills_pie': other_skills_pie,
            'characters': [{'name': row.Name, 'level': row.Level, 'skills': row.Skills, 'equipment': row.Equipment, 'mercenary': row.Mercenary, 'mercenary_equipment': row.MercenaryEquipment, 'class': row.Class } for row in sorted_group.itertuples()],
            'top_equipment': top_equipment_str,
            'equipment_counts': equipment_counts_str,
            'remaining_skills_with_icons': remaining_skills_str_with_icons,
            'summary_label': summary,
            'mercenary': mercenary,
            'mercenary_equipment': mercenary_equipment,
        })

        mercenary, mercenary_counts, mercenary_equipment = analyze_mercenaries(filtered_characters)

    # Create pie chart
    pie_data = df.groupby('Cluster').agg({
        'Percentage': 'mean',
        'Cluster_Label': 'first'
    }).reset_index()

    # Add the class name explicitly
    pie_data['Class'] = pie_data['Cluster']

    # Combine cluster label and percentage for the pie chart labels
    pie_data['Cluster_Label_Percentage'] = pie_data.apply(lambda row: f"{row['Percentage']:.2f}% - Main Skills and avg points: {row['Cluster_Label']}", axis=1)

    # Get unique clusters
    unique_clusters = sorted(df['Cluster'].unique())

    # Assign colors from a predefined palette
    color_palette = px.colors.qualitative.Safe
    color_map = {cluster: color_palette[i % len(color_palette)] for i, cluster in enumerate(unique_clusters)}

    fig_pie = px.pie(
        pie_data,
        values='Percentage',
        names='Class',
        title=f"Base Class Distribution",
        hover_data={'Class': True, 'Cluster_Label': True},
        color_discrete_map={row['Class']: color_map[row['Cluster']] for _, row in pie_data.iterrows()}
    )

    # Customize the pie chart
    fig_pie.update_traces(
        textinfo='percent',
        textposition='inside',
        hovertemplate="<b>%{customdata[0]}</b><br>Other Skills and Average Point Investment:<br>%{customdata[1]}<extra></extra>",
        marker=dict(line=dict(color='black', width=1)),
        pull=[0.05] * len(pie_data),
        hole=0
    )

    # Position the legend and style
    fig_pie.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color='white'),
            bgcolor='rgba(0,0,0,0)',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=50, b=20),
        width=900,
        height=600,
        font=dict(color='white'),
        title=dict(font=dict(color='white')),
    )

    # Increase the pie size explicitly
    fig_pie.update_traces(domain=dict(x=[0, 1], y=[0.1, 1]))

    # Save the pie chart as a PNG file
    # Determine output path based on current directory
    current_dir = os.getcwd()
    if current_dir.endswith('/scripts/modules'):
        charts_dir = "../../pod-stats/charts"
    elif current_dir.endswith('/scripts'):
        charts_dir = "../pod-stats/charts"
    else:
        # Running from root directory
        charts_dir = "pod-stats/charts"
    
    os.makedirs(charts_dir, exist_ok=True)
    chart_filename = f"{what_class if league == 'sc' else 'hc' + what_class}-clusters_distribution_pie.png"
    fig_pie.write_image(f"{charts_dir}/{chart_filename}")

    print("Pie chart saved as PNG file.")

    # Sort clusters by percentage in descending order
    sorted_clusters = dict(sorted(clusters.items(), key=lambda item: item[1]['character_count'], reverse=True))

    dt = datetime.now()
    timeStamp = dt.strftime('%Y-%m-%d %H:%M')

    # HTML template
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ what_class }} Analysis Report</title>
        <link rel="stylesheet" type="text/css" href="./css/test-css.css">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body class="not-main">
        <div class="is-clipped">
            <div id="navbar-placeholder"></div>
            <script>
            fetch("templates/navbar.html")
                .then(res => res.text())
                .then(html => {
                document.getElementById("navbar-placeholder").innerHTML = html;
                });
            </script>

        <div class="hamburger hamburger2" onclick="toggleMenu()">
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

        <h1>{{ what_class }} {{ league.upper() }}core Skill Distribution </h1>
        <div class="summary-container">
        <br>
        <h3>The Notazon is not a Zon, but has bolts or arrows equipped</h3>

        {% for cluster, data in clusters.items() %}
        <div class="class-intro">
        <div id="skills" class="skills-container">
            <div class="column">
                <ul id="most-popular-skills">
                    <h2>{{ data['label'] }}</h2>
                </ul>
            </div>
        </div>

        <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                    <strong>All Skills</strong></button>
                    <div class="content">
                        <div>{{ data['remaining_skills_with_icons'] }}</div>
                    </div>

                    <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                    <strong>Most Common Equipment:</strong></button>
                    <div class="content">
                        <div>{{ data['top_equipment'] }}</div>
                    </div>

                 <button type="button" class="collapsible small-collapsible">
            <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
                <strong>{{ data['character_count'] }} Characters in this cluster:</strong>
            </button>
            <div class="content">
    {% for character in data['characters'] %}
    <div class="character-container char2">
        <div class="character-info">
            <div class="character-link"><strong>Name: <a href="https://beta.pathofdiablo.com/armory?name={{ character['name'] }}" target="_blank">
                    {{ character['name'] }}
                </a></strong></div>
            <div>Level: {{ character['level'] }}</div>
            <div>Class: {{ character['class'] }}</div>
            <div class="hover-trigger" data-character-name="{{ character['name'] }}">
                <!-- Armory Quickview -->
            </div>
        </div>

        <div class="character">
            <div class="popup hidden"></div> <!-- No iframe inside initially -->
        </div>

        <p><strong>Skills:<br></strong> {{ character['skills'] }}</p>
        <p><strong>Equipment:<br></strong> {{ character['equipment'] }}</p>
        <p><strong>Mercenary:<br></strong> {{ character['mercenary'] }} - {{ character['mercenary_equipment'] }}</p>

        <div class="character-section" data-character-name="{{ character['name'] }}"></div>
    </div>
    <hr color="#141414">
    <br>
    {% endfor %}
                <br>
                </div>
                </div>
            <br>
                {% endfor %}
            </ul>
            <br>
            <hr>
            <br>
            <br>
            </div>
            <br><br>
                        <!-- Embed the Plotly pie chart -->
            <div>
                <img src="charts/{{ chart_filename }}" alt="{{ what_class }} Skills Distribution">
            </div>

            <button onclick="topFunction()" id="backToTopBtn" class="back-to-top"></button>
                <div class="footer">
                <p>PoD data current as of {{ timeStamp }}</p>
                </div>

<script>
// Collapsible elements
var coll = document.getElementsByClassName("collapsible");
for (var i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        var openIcon = this.querySelector("img.icon[alt='Open']");
        var closeIcon = this.querySelector("img.icon[alt='Close']");

        if (content.style.display === "block") {
            content.style.display = "none";
            openIcon.classList.remove("hidden");
            closeIcon.classList.add("hidden");
        } else {
            content.style.display = "block";
            openIcon.classList.add("hidden");
            closeIcon.classList.remove("hidden");
        }
    });
}

//Back to top button
var backToTopBtn = document.getElementById("backToTopBtn");

window.onscroll = function() {scrollFunction()};

function scrollFunction() {
if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
backToTopBtn.style.display = "block";
} else {
backToTopBtn.style.display = "none";
}
}

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
    const filename = currentUrl.split("/").pop();

    const isHardcore = filename.startsWith("hc");

    if (isHardcore) {
        scHcButton.classList.add("hardcore");
        scHcButton.classList.remove("softcore");
    } else {
        scHcButton.classList.add("softcore");
        scHcButton.classList.remove("hardcore");
    }

    updateButtonImage(isHardcore);

    scHcButton.addEventListener("click", function () {
        let newUrl;

        if (isHardcore) {
            newUrl = currentUrl.replace(/hc(\w+)$/, "$1");
        } else {
            newUrl = currentUrl.replace(/\/(\w+)$/, "/hc$1");
        }

        if (newUrl !== currentUrl) {
            window.location.href = newUrl;
        }
    });

    function updateButtonImage(isHardcore) {
        if (isHardcore) {
            scHcButton.style.backgroundImage = "url('icons/Hardcore_click.png')";
        } else {
            scHcButton.style.backgroundImage = "url('icons/Softcore_click.png')";
        }
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const currentPage = window.location.pathname.split("/").pop();
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

if (activePopup) {
activePopup.classList.remove("active");
activePopup.innerHTML = "";
activePopup = null;
}

const popup = this.closest(".character-info").nextElementSibling.querySelector(".popup");

if (popup === activePopup) {
return;
}

const iframe = document.createElement("iframe");
iframe.src = `./armory/video_component.html?charName=${encodeURIComponent(characterName)}`;
iframe.setAttribute("id", "popupFrame");

popup.appendChild(iframe);
popup.classList.add("active");

activePopup = popup;
});
});

document.addEventListener("click", function (event) {
if (activePopup && !activePopup.contains(event.target)) {
activePopup.classList.remove("active");
activePopup.innerHTML = "";
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
        event.stopPropagation();
        dropdownContent.classList.toggle('is-active');
    });

    document.addEventListener('click', () => {
        if (dropdownContent.classList.contains('is-active')) {
            dropdownContent.classList.remove('is-active');
        }
    });
});

//Anchor in place fix
function scrollWithOffset(el, offset = -50) {
    const y = el.getBoundingClientRect().top + window.pageYOffset + offset;
    window.scrollTo({ top: y, behavior: 'smooth' });
}

function expandToAnchor(anchorId) {
    console.log("expandToAnchor called with:", anchorId);
    const target = document.getElementById(anchorId);
    if (!target) return;

    const stack = [];
    let el = target;
    while (el) {
        if (el.classList?.contains('content')) {
            stack.unshift(el);
        }
        el = el.parentElement;
    }

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

    setTimeout(() => {
        console.log("scrolling to:", target.id);
        scrollWithOffset(target);
    }, 250);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.anchor-link, a[href^="#"]').forEach(link => {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            const anchorId = this.getAttribute('href').substring(1);
            const fullUrl = `${window.location.origin}${window.location.pathname}#${anchorId}`;

            navigator.clipboard.writeText(fullUrl);
            history.pushState(null, '', `#${anchorId}`);
            expandToAnchor(anchorId);
        });
    });

    if (window.location.hash) {
        const anchorId = window.location.hash.substring(1);
        setTimeout(() => {
            expandToAnchor(anchorId);
        }, 200);
    }
});

</script>

    </body>
    </html>
    """

    # Render the HTML report
    template = Template(html_template)
    html_content = template.render(
        clusters=sorted_clusters, 
        what_class=what_class, 
        league=league,
        timeStamp=timeStamp,
        chart_filename=chart_filename
    )

    # Save the report to a file
    # Determine output path based on current directory
    current_dir = os.getcwd()
    if current_dir.endswith('/scripts/modules'):
        output_file = f"../../pod-stats/{what_class if league == 'sc' else 'hc' + what_class}.html"
    elif current_dir.endswith('/scripts'):
        output_file = f"../pod-stats/{what_class if league == 'sc' else 'hc' + what_class}.html"
    else:
        # Running from root directory
        output_file = f"pod-stats/{what_class if league == 'sc' else 'hc' + what_class}.html"
    with open(output_file, "w") as file:
        file.write(html_content)

    print(f"✅ {what_class} analysis report saved to {output_file}")
    return len(filtered_characters)

if __name__ == "__main__":
    # Generate for both leagues
    sc_count = analyze_notazons("sc")
    hc_count = analyze_notazons("hc")
    
    print(f"📊 Analysis complete:")
    print(f"   Softcore: {sc_count} non-Amazon bow users")
    print(f"   Hardcore: {hc_count} non-Amazon bow users")