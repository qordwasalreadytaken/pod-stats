"""
Class Pages Analysis Module
Handles all class-specific analysis and HTML generation for individual class pages
Based on class-test.py but modularized for both softcore and hardcore modes
"""

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
import plotly.express as px
import plotly.io as pio
import json
import os
from collections import Counter, defaultdict
import numpy as np
from jinja2 import Template
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import statistics
import html
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path to access items_list.py
sys.path.append(str(Path(__file__).parent.parent.parent))
import items_list

from .shared_utils import generate_standard_javascript


class ClassPagesAnalyzer:
    """Analyzes character data for class-specific clustering and statistics"""
    
    def __init__(self, all_characters, is_hardcore=False):
        self.all_characters = all_characters
        self.is_hardcore = is_hardcore
        self.mode_prefix = "hc" if is_hardcore else ""
        self.icons_folder = "icons"
        
        # Class configurations with similarity thresholds
        self.classes = [
            {"what_class": "Barbarian", "howmany_clusters": 10, "howmany_skills": 5, "threshold": 0.70},
            {"what_class": "Druid", "howmany_clusters": 7, "howmany_skills": 5, "threshold": 0.60},
            {"what_class": "Amazon", "howmany_clusters": 11, "howmany_skills": 5, "threshold": 0.65},
            {"what_class": "Assassin", "howmany_clusters": 6, "howmany_skills": 5, "threshold": 0.65},
            {"what_class": "Necromancer", "howmany_clusters": 6, "howmany_skills": 5, "threshold": 0.70},
            {"what_class": "Paladin", "howmany_clusters": 6, "howmany_skills": 5, "threshold": 0.70},
            {"what_class": "Sorceress", "howmany_clusters": 10, "howmany_skills": 5, "threshold": 0.65}
        ]
        
        self.quality_colors = {
            "q_runeword": "#edcd74",
            "q_unique": "#edcd74", 
            "q_set": "#45a823",
            "q_magic": "#7074c9",
            "q_rare": "yellow",
            "q_crafted": "orange"
        }
        
        # Define skill weights for meaningful sorting
        self.skill_weights = {
            ### Amazon
            "Multiple Shot": 100,
            "Strafe": 90,
            "Guided Arrow": 80,
            "Lightning Bolt": 100,
            "Lightning Strike": 90,
            "Charged Strike": 80,
            "Lightning Fury": 100,
            "Poison Javelin": 70,
            "Plague Javelin": 80,
            "Freezing Arrow": 90,
            "Immolation Arrow": 85,
            "Explosive Arrow": 75,
            
            ### Assassin
            "Dragon Talon": 100,
            "Dragon Claw": 80,
            "Dragon Tail": 70,
            "Dragon Flight": 30,
            "Mind Blast": 100, 
            "Psychic Hammer": 100,
            "Cloak of Shadows": 60,
            "Shadow Warrior": 80,
            "Shadow Master": 90,
            "Fire Blast": 60,
            "Lightning Sentry": 100,
            "Death Sentry": 90,
            "Wake of Fire": 80,
            "Blade Sentinel": 70,
            
            ### Barbarian
            "Bash": 50,
            "Cleave": 50,
            "Whirlwind": 100,
            "Double Swing": 50,
            "War Cry": 70,
            "Concentrate": 90,
            "Berserk": 80,
            "Frenzy": 85,
            "Double Throw": 75,
            "Leap Attack": 60,
            "Battle Orders": 95,
            "Battle Command": 85,
            "Shout": 70,
            
            ### Druid
            "Rabies": 50,
            "Fury": 70,
            "Fire Claws": 70,
            "Maul": 80,
            "Shock Wave": 75,
            "Armageddon": 90,
            "Hurricane": 85,
            "Tornado": 100,
            "Cyclone Armor": 70,
            "Twister": 60,
            "Volcano": 80,
            "Fissure": 75,
            "Molten Boulder": 65,
            "Creeper": 60,
            "Carrion Vine": 70,
            "Spirit Wolf": 50,
            "Dire Wolf": 70,
            "Grizzly": 90,
            
            ### Necromancer
            "Hemorrhage": 70,
            "Deadly Poison": 70,
            "Corpse Explosion": 50,
            "Bone Spear": 100,
            "Bone Spirit": 90,
            "Bone Prison": 60,
            "Bone Armor": 80,
            "Poison Nova": 85,
            "Poison Explosion": 75,
            "Raise Skeleton": 80,
            "Skeleton Mastery": 85,
            "Raise Skeletal Mage": 75,
            "Golem Mastery": 70,
            "Iron Golem": 65,
            "Clay Golem": 60,
            "Blood Golem": 55,
            "Fire Golem": 70,
            "Amplify Damage": 85,
            "Decrepify": 80,
            "Lower Resist": 75,
            
            ### Paladin
            "Fist of the Heavens": 80,
            "Zeal": 70,
            "Dashing Strike": 70,
            "Smite": 70,
            "Charge": 70,
            "Holy Bolt": 70,
            "Blessed Hammer": 100,
            "Concentration": 90,
            "Fanaticism": 85,
            "Conviction": 95,
            "Salvation": 80,
            "Redemption": 75,
            "Sanctuary": 70,
            "Holy Fire": 65,
            "Holy Freeze": 70,
            "Holy Shock": 75,
            "Might": 60,
            "Prayer": 50,
            
            ### Sorceress
            "Telekinesis": 50,
            "Thunder Storm": 80,
            "Lightning Surge": 100,
            "Nova": 50,
            "Charged Bolt": 100,
            "Lightning": 90,
            "Chain Lightning": 95,
            "Blizzard": 100,
            "Frigerate": 100,
            "Freezing Pulse": 100,
            "Frozen Orb": 100,
            "Frost Nova": 50,
            "Ice Bolt": 40,
            "Glacial Spike": 70,
            "Hydra": 100,
            "Meteor": 100,
            "Enflame": 100,
            "Immolate": 50,
            "Inferno": 80,
            "Fireball": 90,
            "Fire Bolt": 60,
            "Fire Wall": 75,
            "Teleport": 95,
            "Energy Shield": 85,
            "Warmth": 60,
            "Static Field": 80
        }
    
    def map_readable_names(self, mercenary_type, worn_category=""):
        """Map mercenary and equipment names to readable format"""
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
    
    def analyze_class_builds(self, what_class, howmany_clusters, howmany_skills, threshold=0.65):
        """Analyze builds for a specific class using advanced clustering"""
        
        # Filter characters by class
        filtered_characters = [char for char in self.all_characters if char.get("Class") == what_class]
        
        if not filtered_characters:
            print(f"No characters found for class {what_class}")
            return None
        
        print(f"Analyzing {len(filtered_characters)} {what_class} characters...")
        
        # Analyze maxed skills
        maxed_skills = defaultdict(list)
        for char in filtered_characters:
            name = char.get("Name", "Unknown")
            for skill_tab in char.get("SkillTabs", []):
                for skill in skill_tab.get("Skills", []):
                    if skill.get("Level", 0) == 20:
                        skill_name = skill.get("Name", "Unknown Skill")
                        maxed_skills[skill_name].append(name)
        
        sorted_maxed_skills = sorted(maxed_skills.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Process skill data for clustering
        df = self._load_skill_data(filtered_characters)
        
        if len(df) < 3:
            print(f"Not enough characters ({len(df)}) for clustering analysis")
            return None
        
        # Perform advanced clustering analysis
        clustering_results = self._perform_advanced_clustering(df, what_class, threshold)
        
        # Calculate global top/bottom skills (matches class-test.py)
        top_bottom_skills = self._calculate_global_skill_usage(clustering_results['df'], clustering_results['skill_columns']) if clustering_results else None
        
        # Analyze equipment patterns
        equipment_analysis = self._analyze_equipment_patterns(filtered_characters, clustering_results['df'] if clustering_results else None)
        
        # Analyze mercenary usage
        mercenary_analysis = self._analyze_mercenary_patterns(filtered_characters)
        
        # Analyze fun facts for both softcore and hardcore
        fun_facts_analysis = self._analyze_fun_facts(filtered_characters, what_class)
        
        return {
            'class_name': what_class,
            'filtered_characters': filtered_characters,
            'maxed_skills': sorted_maxed_skills,
            'clustering_results': clustering_results,
            'top_bottom_skills': top_bottom_skills,
            'equipment_analysis': equipment_analysis,
            'mercenary_analysis': mercenary_analysis,
            'fun_facts_analysis': fun_facts_analysis,
            'character_count': len(filtered_characters)
        }
    
    def _load_skill_data(self, filtered_characters):
        """Load and process skill data for clustering"""
        all_data = []
        
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
                        skill_data[skill_name] = skill_level
                        skills.append((skill_name, skill_level))
                
                skills_sorted = sorted(skills, key=lambda x: x[1], reverse=True)
                skill_data["Skills"] = ", ".join([
                    f"<img src='{self.icons_folder}/{name}.png' alt='{name}' class='skill-icon-smaller'> {name}:{level}"
                    for name, level in skills_sorted
                ])
                
                # Process Equipment
                equipment_titles = defaultdict(Counter)
                for item in char_data["Equipped"]:
                    worn_category = item.get("Worn", "Unknown")
                    title = item.get("Title", "Unknown")
                    quality_code = item.get("QualityCode", "default")
                    tag = item.get("Tag", "")
                    
                    # Standardize worn category names
                    worn_category = {
                        "ring1": "Ring", "ring2": "Ring",
                        "sweapon1": "Left hand", "weapon1": "Left hand", 
                        "sweapon2": "Offhand", "weapon2": "Offhand",
                        "body": "Armor", "gloves": "Gloves",
                        "belt": "Belt", "helmet": "Helmet",
                        "boots": "Boots", "amulet": "Amulet"
                    }.get(worn_category, worn_category)
                    
                    # Set colored title
                    color = self.quality_colors.get(quality_code, "white")
                    if quality_code in ["q_magic", "q_rare", "q_crafted"]:
                        formatted_tag = f" {tag}" if tag else ""
                        colored_title = f"<span style='color: {color};'>{quality_code.split('_')[1].capitalize()}{formatted_tag}</span>"
                    else:
                        colored_title = f"<span style='color: {color};'>{title}</span>"
                    
                    equipment_titles[worn_category][colored_title] += 1
                
                # Convert equipment data to a readable string
                skill_data["Equipment"] = ", ".join([
                    f"{worn}: {title} x{count}" if count > 1 else f"{worn}: {title}"
                    for worn, titles in equipment_titles.items()
                    for title, count in titles.items()
                ])
                
                # Process mercenary info
                mercenary_type = char_data.get("MercenaryType", "No mercenary")
                readable_mercenary, _ = self.map_readable_names(mercenary_type)
                mercenary_equipment = ", ".join(
                    [item.get("Title", "Unknown") for item in char_data.get("MercenaryEquipped", [])]
                ) if char_data.get("MercenaryEquipped") else "No equipment"
                
                skill_data["Mercenary"] = readable_mercenary
                skill_data["MercenaryEquipment"] = mercenary_equipment
                
                all_data.append(skill_data)
        
        return pd.DataFrame(all_data).fillna(0)
    
    def _perform_advanced_clustering(self, df, what_class, threshold):
        """Perform similarity clustering on skill data to match class-test.py"""
        
        if df.empty:
            return None
        
        # Get skill columns (exclude non-skill columns)
        skill_columns = [col for col in df.columns if col not in ['Name', 'Class', 'Level', 'Skills', 'Equipment', 'Mercenary', 'MercenaryEquipment']]
        
        if not skill_columns:
            print(f"No skill data found for {what_class}")
            return None
        
        print(f"[{what_class}] Using similarity threshold: {threshold}")
        
        # Perform similarity clustering (matches class-test.py exactly)
        df = self._similarity_cluster(df, skill_columns, what_class, threshold)
        
        # Calculate cluster statistics using 'Cluster' column (not 'Cluster_Hybrid')
        cluster_col = 'Cluster'
        cluster_sizes = df[cluster_col].value_counts().sort_index()
        total_chars = len(df)
        
        # Calculate skill averages per cluster
        skill_averages = df[skill_columns].groupby(df[cluster_col]).mean()
        
        # Generate cluster labels based on top skills
        cluster_labels = {}
        for cluster in cluster_sizes.index:
            top_skills = skill_averages.loc[cluster].nlargest(3)
            label_parts = []
            for skill, avg_points in top_skills.items():
                if avg_points >= 1:
                    label_parts.append(f"{skill}({avg_points:.0f})")
            cluster_labels[cluster] = ", ".join(label_parts)
        
        df['Cluster_Label'] = df[cluster_col].map(cluster_labels)
        df['Percentage'] = df[cluster_col].map(lambda x: (cluster_sizes[x] / total_chars) * 100)
        
        # Perform PCA for visualization
        pca = PCA(n_components=2, random_state=42)
        reduced_data = pca.fit_transform(df[skill_columns].values)
        
        return {
            'df': df,
            'skill_columns': skill_columns,
            'skill_averages': skill_averages,
            'cluster_sizes': cluster_sizes,
            'cluster_labels': cluster_labels,
            'reduced_data': reduced_data,
            'total_characters': total_chars,
            'cluster_column': cluster_col
        }
    
    def _similarity_cluster(self, df, skill_columns, what_class, threshold):
        """Similarity clustering that matches class-test.py exactly"""
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        skill_matrix = df[skill_columns].to_numpy()
        similarity_matrix = cosine_similarity(skill_matrix)
        
        cluster_labels = np.full(len(df), -1)
        cluster_id = 0
        
        for i in range(len(df)):
            if cluster_labels[i] == -1:  # Not assigned yet
                similar_indices = np.where(similarity_matrix[i] >= threshold)[0]
                if len(similar_indices) > 1:
                    cluster_labels[similar_indices] = cluster_id
                    cluster_id += 1
        
        # Miscellaneous cluster for unassigned
        misc_indices = np.where(cluster_labels == -1)[0]
        if len(misc_indices) > 0:
            cluster_labels[misc_indices] = cluster_id
            cluster_id += 1
        
        df['Cluster'] = cluster_labels
        print(f"[{what_class}] Clusters formed: {cluster_id}")
        return df
    
    def _calculate_global_skill_usage(self, df, skill_columns):
        """Calculate global top/bottom 5 skills like class-test.py"""
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
        
        return {
            'top_5_most_used_skills': top_5_most_used_skills,
            'bottom_5_least_used_skills': bottom_5_least_used_skills,
            'total_skill_usage': total_skill_usage
        }
    
    def _hybrid_cluster(self, df, skill_columns, min_points_common=60, cosine_threshold=0.6):
        """
        Hybrid clustering:
        1. Group by skill points in common (>= min_points_common).
        2. Cluster remainder with cosine similarity.
        """
        skill_matrix = df[skill_columns].to_numpy()
        n = len(skill_matrix)
        
        # Initialize cluster labels
        cluster_labels = np.full(n, -1)
        cluster_id = 0
        
        # Pass 1: Skill Points in Common
        for i in range(n):
            if cluster_labels[i] != -1:
                continue
            
            base = skill_matrix[i]
            common_points = np.sum(np.minimum(base, skill_matrix), axis=1)
            similar_indices = np.where(common_points >= min_points_common)[0]
            
            if len(similar_indices) > 1:
                cluster_labels[similar_indices] = cluster_id
                cluster_id += 1
        
        # Pass 2: Cosine Similarity for Remainder
        unassigned = np.where(cluster_labels == -1)[0]
        if len(unassigned) > 1:
            remainder = skill_matrix[unassigned]
            sim_matrix = cosine_similarity(remainder)
            
            for idx, i in enumerate(unassigned):
                if cluster_labels[i] != -1:
                    continue
                
                similar_indices = unassigned[np.where(sim_matrix[idx] >= cosine_threshold)[0]]
                if len(similar_indices) > 1:
                    cluster_labels[similar_indices] = cluster_id
                    cluster_id += 1
            
            # Any still unassigned? Put in a misc cluster
            misc_indices = np.where(cluster_labels == -1)[0]
            if len(misc_indices) > 0:
                cluster_labels[misc_indices] = cluster_id
                cluster_id += 1
        
        df['Cluster_Hybrid'] = cluster_labels
        print(f"[Hybrid] {cluster_id} clusters formed (≥{min_points_common} points + cosine ≥{cosine_threshold})")
        return df
    
    def _analyze_equipment_patterns(self, filtered_characters, df):
        """Comprehensive equipment analysis matching class-test.py reference implementation"""
        
        # Initialize all the counters and data structures like in the reference
        runeword_counter = Counter()
        unique_counter = Counter()
        set_counter = Counter()
        synth_counter = Counter()
        crafted_counters = {
            "Rings": Counter(),
            "Weapons and Shields": Counter(),
            "Arrows": Counter(),
            "Bolts": Counter(),
            "Body Armor": Counter(),
            "Gloves": Counter(),
            "Belts": Counter(),
            "Helmets": Counter(),
            "Boots": Counter(),
            "Amulets": Counter(),
        }
        magic_counters = {
            "Rings": Counter(),
            "Weapons and Shields": Counter(),
            "Arrows": Counter(),
            "Bolts": Counter(),
            "Body Armor": Counter(),
            "Gloves": Counter(),
            "Belts": Counter(),
            "Helmets": Counter(),
            "Boots": Counter(),
            "Amulets": Counter(),
        }
        rare_counters = {
            "Rings": Counter(),
            "Weapons and Shields": Counter(),
            "Arrows": Counter(),
            "Bolts": Counter(),
            "Body Armor": Counter(),
            "Gloves": Counter(),
            "Belts": Counter(),
            "Helmets": Counter(),
            "Boots": Counter(),
            "Amulets": Counter(),
        }
        
        synth_sources = {}  # Maps item names to all synth items that used them
        runeword_users = {}
        unique_users = {}
        set_users = {}
        synth_users = {}
        crafted_users = {category: {} for category in crafted_counters}
        rare_users = {category: {} for category in crafted_counters}
        magic_users = {category: {} for category in crafted_counters}

        # Process all characters for equipment analysis
        class_counts, runeword_counter, unique_counter, set_counter, synth_counter, runeword_users, unique_users, set_users, synth_users, crafted_counters, crafted_users, synth_sources = self._process_all_characters(filtered_characters)
        
        magic_counters, magic_users, rare_counters, rare_users = self._process_all_characters_for_magic_rare(filtered_characters)

        # Get the most/least common items
        most_common_runewords = runeword_counter.most_common(10)
        most_common_uniques = unique_counter.most_common(10)
        most_common_set_items = set_counter.most_common(10)

        # Get all the items
        all_runewords = runeword_counter.most_common(150)
        all_uniques = unique_counter.most_common(450)
        all_set = set_counter.most_common(150)
        all_synth = synth_counter.most_common(150)

        # Get the least common items
        least_common_runewords = runeword_counter.most_common()[:-11:-1]
        least_common_uniques = unique_counter.most_common()[:-11:-1]
        least_common_set_items = set_counter.most_common()[:-11:-1]

        # Socket analysis
        socketed_runes_html, socketed_excluding_runes_html, other_items_html = self._socket_html(filtered_characters)

        return {
            'runeword_counter': runeword_counter,
            'unique_counter': unique_counter,
            'set_counter': set_counter,
            'synth_counter': synth_counter,
            'crafted_counters': crafted_counters,
            'magic_counters': magic_counters,
            'rare_counters': rare_counters,
            'most_common_runewords': most_common_runewords,
            'most_common_uniques': most_common_uniques,
            'most_common_set_items': most_common_set_items,
            'least_common_runewords': least_common_runewords,
            'least_common_uniques': least_common_uniques,
            'least_common_set_items': least_common_set_items,
            'all_runewords': all_runewords,
            'all_uniques': all_uniques,
            'all_set': all_set,
            'all_synth': all_synth,
            'runeword_users': runeword_users,
            'unique_users': unique_users,
            'set_users': set_users,
            'synth_users': synth_users,
            'crafted_users': crafted_users,
            'magic_users': magic_users,
            'rare_users': rare_users,
            'synth_sources': synth_sources,
            'socketed_runes_html': socketed_runes_html,
            'socketed_excluding_runes_html': socketed_excluding_runes_html,
            'other_items_html': other_items_html,
            'synth_user_count': sum(len(users) for users in synth_users.values()),
            'craft_user_count': sum(len(users) for users in crafted_users.values()),
            'magic_user_count': sum(len(users) for users in magic_users.values()),
            'rare_user_count': sum(len(users) for users in rare_users.values()),
            'synth_source_user_count': sum(len(users) for users in synth_sources.values()),
        }

    def _process_all_characters(self, filtered_characters):
        """Process all characters for runewords, uniques, sets, and synth items (matches class-test.py)"""
        
        class_counts = {}
        runeword_counter = Counter()
        unique_counter = Counter()
        set_counter = Counter()
        synth_counter = Counter()
        crafted_counters = {
            "Rings": Counter(),
            "Weapons and Shields": Counter(),
            "Arrows": Counter(),
            "Bolts": Counter(),
            "Body Armor": Counter(),
            "Gloves": Counter(),
            "Belts": Counter(),
            "Helmets": Counter(),
            "Boots": Counter(),
            "Amulets": Counter(),
        }
        
        synth_sources = {}  # Maps item names to all synth items that used them
        runeword_users = {}
        unique_users = {}
        set_users = {}
        synth_users = {}
        crafted_users = {category: {} for category in crafted_counters}

        def categorize_worn_slot(worn_category, text_tag):
            """Categorize equipment slots for crafted items"""
            if worn_category in ["ring1", "ring2"]:
                return "Rings"
            elif worn_category in ["sweapon1", "weapon1", "sweapon2", "weapon2"]:
                if text_tag == "Arrow":
                    return "Arrows"
                elif text_tag == "Bolt":
                    return "Bolts"
                else:
                    return "Weapons and Shields"
            elif worn_category == "body":
                return "Body Armor"
            elif worn_category == "gloves":
                return "Gloves"
            elif worn_category == "belt":
                return "Belts"
            elif worn_category == "helmet":
                return "Helmets"
            elif worn_category == "boots":
                return "Boots"
            elif worn_category == "amulet":
                return "Amulets"
            else:
                return "Weapons and Shields"  # Default fallback

        for char_data in filtered_characters:
            char_name = char_data.get("Name", "Unknown")
            char_level = char_data.get("Stats", {}).get("Level", "Unknown")
            char_class = char_data.get("Class", "Unknown")

            for item in char_data.get("Equipped", []):
                title = item.get("Title", "Unknown Item")
                quality_code = item.get("QualityCode", "default")
                worn_category = item.get("Worn", "Unknown")
                text_tag = item.get("TextTag", "")
                tag = item.get("Tag", "")

                # Process different item types
                if quality_code == "q_runeword":
                    runeword_counter[title] += 1
                    if title not in runeword_users:
                        runeword_users[title] = []
                    runeword_users[title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

                elif quality_code == "q_unique":
                    unique_counter[title] += 1
                    if title not in unique_users:
                        unique_users[title] = []
                    unique_users[title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

                elif quality_code == "q_set":
                    set_counter[title] += 1
                    if title not in set_users:
                        set_users[title] = []
                    set_users[title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

                # Process synthesized items (check Tag and TextTag for "synth")
                if "synth" in tag.lower() or "synth" in text_tag.lower():
                    synth_counter[title] += 1
                    if title not in synth_users:
                        synth_users[title] = []
                    synth_users[title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

                    # Process SynthesisedFrom property for source tracking
                    synthesized_from = item.get("SynthesisedFrom", [])
                    all_related_items = [title] + synthesized_from
                    for source_item in all_related_items:
                        if source_item not in synth_sources:
                            synth_sources[source_item] = []
                        synth_sources[source_item].append({
                            "name": char_name,
                            "class": char_class,
                            "level": char_level,
                            "synthesized_item": title
                        })

                elif quality_code == "q_crafted":
                    category = categorize_worn_slot(worn_category, text_tag)
                    crafted_counters[category][title] += 1
                    if title not in crafted_users[category]:
                        crafted_users[category][title] = []
                    crafted_users[category][title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

        return (
            class_counts, runeword_counter, unique_counter, set_counter, synth_counter,
            runeword_users, unique_users, set_users, synth_users, crafted_counters, crafted_users, synth_sources
        )

    def _process_all_characters_for_magic_rare(self, filtered_characters):
        """Process all characters for magic and rare items (matches class-test.py)"""
        
        magic_counters = defaultdict(Counter)
        rare_counters = defaultdict(Counter)
        magic_users = defaultdict(lambda: defaultdict(list))
        rare_users = defaultdict(lambda: defaultdict(list))

        def categorize_worn_slot(worn_category, text_tag):
            """Categorize equipment slots"""
            if worn_category in ["ring1", "ring2"]:
                return "Rings"
            elif worn_category in ["sweapon1", "weapon1", "sweapon2", "weapon2"]:
                if text_tag == "Arrow":
                    return "Arrows"
                elif text_tag == "Bolt":
                    return "Bolts"
                else:
                    return "Weapons and Shields"
            elif worn_category == "body":
                return "Body Armor"
            elif worn_category == "gloves":
                return "Gloves"
            elif worn_category == "belt":
                return "Belts"
            elif worn_category == "helmet":
                return "Helmets"
            elif worn_category == "boots":
                return "Boots"
            elif worn_category == "amulet":
                return "Amulets"
            else:
                return "Weapons and Shields"  # Default fallback

        # Iterate through all characters
        for char_data in filtered_characters:
            char_name = char_data.get("Name", "Unknown")
            char_level = char_data.get("Stats", {}).get("Level", "Unknown")
            char_class = char_data.get("Class", "Unknown")

            for item in char_data.get("Equipped", []):
                title = item.get("Title", "Unknown Item")
                quality_code = item.get("QualityCode", "default")
                worn_category = item.get("Worn", "Unknown")
                text_tag = item.get("TextTag", "")

                category = categorize_worn_slot(worn_category, text_tag)

                if quality_code == "q_magic":
                    magic_counters[category][title] += 1
                    magic_users[category][title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

                elif quality_code == "q_rare":
                    rare_counters[category][title] += 1
                    rare_users[category][title].append({
                        "name": char_name, "level": char_level, "class": char_class
                    })

        return magic_counters, magic_users, rare_counters, rare_users

    def _socket_html(self, filtered_characters):
        """Generate socketed item analysis (matches class-test.py)"""
        
        rune_names = {
            "El Rune", "Eld Rune", "Tir Rune", "Nef Rune", "Eth Rune", "Ith Rune", "Tal Rune", "Ral Rune", "Ort Rune", "Thul Rune", "Amn Rune", "Sol Rune",
            "Shael Rune", "Dol Rune", "Hel Rune", "Io Rune", "Lum Rune", "Ko Rune", "Fal Rune", "Lem Rune", "Pul Rune", "Um Rune", "Mal Rune", "Ist Rune",
            "Gul Rune", "Vex Rune", "Ohm Rune", "Lo Rune", "Sur Rune", "Ber Rune", "Jah Rune", "Cham Rune", "Zod Rune"
        }

        # Categorization
        all_items = []
        socketed_items = []
        items_excluding_runewords = []
        just_socketed = []
        just_socketed_excluding_runewords = []

        # Process all characters
        for char_data in filtered_characters:
            for item in char_data.get('Equipped', []):
                all_items.append(item)
                
                # Check if item has sockets and socketables
                socketables = item.get('Sockets', [])
                if socketables:
                    socketed_items.append(item)
                    
                    # Check if it's not a runeword
                    if item.get('QualityCode') != 'q_runeword':
                        items_excluding_runewords.append(item)
                    
                    # Add individual socketed items
                    for socketed_item in socketables:
                        just_socketed.append(socketed_item)
                        if item.get('QualityCode') != 'q_runeword':
                            just_socketed_excluding_runewords.append(socketed_item)

        # Count items by type (matching reference exactly)
        def count_items_by_type(items):
            rune_counter = Counter()
            non_rune_counter = Counter()
            magic_jewel_counter = Counter()
            rare_jewel_counter = Counter()
            facet_counter = defaultdict(lambda: {"count": 0, "perfect": 0})

            for item in items:
                title = item.get('Title', 'Unknown')
                quality = item.get('QualityCode', '')

                if title in rune_names:
                    rune_counter[title] += 1
                elif "Rainbow Facet" in title:
                    # Extract element type from properties
                    element_types = ["fire", "cold", "lightning", "poison", "physical", "magic"]
                    element = "Unknown"
                    for elem in element_types:
                        for prop in item.get('PropertyList', []):
                            if elem in prop.lower():
                                element = elem.capitalize()
                                break
                        if element != "Unknown":
                            break
                    
                    facet_counter[element]["count"] += 1
                    # Check if perfect - look for +5% and -5% in properties
                    properties = item.get('PropertyList', [])
                    prop_text = ' '.join(properties) if properties else ''
                    has_plus_five = '+5%' in prop_text
                    has_minus_five = '-5%' in prop_text
                    if has_plus_five and has_minus_five:
                        facet_counter[element]["perfect"] += 1
                        
                elif quality == "q_magic":
                    # Analyze magic jewel properties
                    properties = item.get('PropertyList', [])
                    magic_jewel_counter['Misc. Magic Jewels'] += 1
                    
                    # Count specific properties
                    for prop in properties:
                        prop_text = prop.lower() if isinstance(prop, str) else str(prop).lower()
                        if 'splash' in prop_text:
                            magic_jewel_counter['splash'] += 1
                        elif 'attack speed' in prop_text or 'ias' in prop_text:
                            magic_jewel_counter['attack speed'] += 1
                        elif 'enhanced damage' in prop_text:
                            magic_jewel_counter['enhanced damage'] += 1
                    
                    # Combined properties
                    has_ias = any('attack speed' in str(prop).lower() or 'ias' in str(prop).lower() for prop in properties)
                    has_splash = any('splash' in str(prop).lower() for prop in properties)
                    has_ed = any('enhanced damage' in str(prop).lower() for prop in properties)
                    
                    if has_ias and has_splash:
                        magic_jewel_counter['iassplash'] += 1
                    if has_ias and has_ed:
                        magic_jewel_counter['iased'] += 1
                        
                elif quality == "q_rare":
                    # Analyze rare jewel properties
                    properties = item.get('PropertyList', [])
                    rare_jewel_counter['Misc. Rare Jewels'] += 1
                    
                    for prop in properties:
                        prop_text = prop.lower() if isinstance(prop, str) else str(prop).lower()
                        if 'splash' in prop_text:
                            rare_jewel_counter['splash'] += 1
                        elif 'enhanced damage' in prop_text:
                            rare_jewel_counter['enhanced damage'] += 1
                else:
                    non_rune_counter[title] += 1

            return rune_counter, non_rune_counter, magic_jewel_counter, rare_jewel_counter, facet_counter

        # Unpack correctly for all five values
        just_socketed_runes, just_socketed_non_runes, just_socketed_magic, just_socketed_rare, just_socketed_facets = count_items_by_type(just_socketed)
        just_socketed_excluding_runewords_runes, just_socketed_excluding_runewords_non_runes, just_socketed_excluding_runewords_magic, just_socketed_excluding_runewords_rare, just_socketed_excluding_runewords_facets = count_items_by_type(just_socketed_excluding_runewords)

        # Sort items for output
        sorted_just_socketed_runes = just_socketed_runes.most_common()
        sorted_just_socketed_excluding_runewords_runes = just_socketed_excluding_runewords_runes.most_common()

        # Combine non-runes, magic, rare, and facets into a single list
        all_other_items = [
            *(f"{item}: {count}" for item, count in just_socketed_excluding_runewords_non_runes.items()),
            f"Misc. Magic Jewels: {just_socketed_excluding_runewords_magic['Misc. Magic Jewels']} "
            f"({just_socketed_excluding_runewords_magic['splash']} Splash, {just_socketed_excluding_runewords_magic['attack speed']} IAS, "
            f"{just_socketed_excluding_runewords_magic['enhanced damage']} ED; {just_socketed_excluding_runewords_magic['iassplash']} IAS/Splash, {just_socketed_excluding_runewords_magic['iased']} IAS/ED)",
            f"Misc. Rare Jewels: {just_socketed_excluding_runewords_rare['Misc. Rare Jewels']} "
            f"({just_socketed_excluding_runewords_rare['splash']} Splash, {just_socketed_excluding_runewords_rare['enhanced damage']} ED)",
            *(f"Rainbow Facet ({element}): {counts['count']} ({counts['perfect']} Perfect)" for element, counts in just_socketed_excluding_runewords_facets.items())
        ]

        return (
            self._format_socket_html_runes(sorted_just_socketed_runes),
            self._format_socket_html_runes(sorted_just_socketed_excluding_runewords_runes),
            self._format_socket_html(all_other_items)
        )

    def _format_socket_html_runes(self, counter_data):
        """Format socketed runes as HTML list"""
        if isinstance(counter_data, list):  # If it's a list of tuples (like runes), format properly
            items = "".join(f"<li>{item}: {count}</li>" for item, count in counter_data)
            return f"<ul>{items}</ul>"
        
        elif isinstance(counter_data, Counter):  # If it's a Counter, format as a table
            rows = "".join(f"<tr><td>{item}</td><td>{count}</td></tr>" for item, count in counter_data.items())
            return f"<table><tr><th>Item</th><th>Count</th></tr>{rows}</table>"
        
        elif isinstance(counter_data, dict):  # If it's a dict (e.g., facet counts), format as a list
            items = "".join(f"<li>{item}: {count['count']} ({count['perfect']} perfect)</li>" for item, count in counter_data.items())
            return f"<ul>{items}</ul>"
        
        return ""

    def _format_socket_html(self, counter_data):
        """Format socketed items as HTML list"""
        if isinstance(counter_data, list):  # If it's a list, format as an unordered list
            items = "".join(f"<li>{item}</li>" for item in counter_data)
            return f"<ul>{items}</ul>"
        
        elif isinstance(counter_data, Counter):  # If it's a Counter, format as a table
            rows = "".join(f"<tr><td>{item}</td><td>{count}</td></tr>" for item, count in counter_data.items())
            return f"<table><tr><th>Item</th><th>Count</th></tr>{rows}</table>"
        
        elif isinstance(counter_data, dict):  # If it's a dict (e.g., facet counts), format as a list
            items = "".join(f"<li>{item}: {count['count']} ({count['perfect']} perfect)</li>" for item, count in counter_data.items())
            return f"<ul>{items}</ul>"
        
        return ""

    def _analyze_mercenary_patterns(self, filtered_characters):
        """Analyze mercenary usage patterns matching class-test.py implementation"""
        mercenary_counts = Counter()
        mercenary_equipment = defaultdict(lambda: defaultdict(Counter))
        mercenary_names = Counter()

        for char_data in filtered_characters:
            if not isinstance(char_data, dict):
                continue  # Skip invalid entries

            mercenary = char_data.get("MercenaryType")
            if mercenary:
                readable_mercenary, _ = self.map_readable_names(mercenary, "")
                mercenary_counts[readable_mercenary] += 1

                merc_name = char_data.get("MercenaryName", "Unknown")
                mercenary_names[merc_name] += 1

                for item in char_data.get("MercenaryEquipped", []):
                    worn_category = item.get("Worn", "Unknown")
                    readable_mercenary, readable_worn = self.map_readable_names(mercenary, worn_category)
                    title = item.get("Title", "Unknown")
                    mercenary_equipment[readable_mercenary][readable_worn][title] += 1

        # Generate the HTML report
        html_output = self._generate_mercenary_html(mercenary_counts, mercenary_equipment, mercenary_names)
        
        return {
            'mercenary_counts': mercenary_counts,
            'mercenary_equipment': mercenary_equipment, 
            'mercenary_names': mercenary_names,
            'html_output': html_output
        }
    
    def _generate_mercenary_html(self, mercenary_counts, mercenary_equipment, mercenary_names):
        """Generate HTML for mercenary analysis matching class-test.py format"""
        html_output = "<p><h2>Mercenary Analysis and Popular Equipment</h2></p>"

        # Mercenary type counts
        html_output += "<p><h3>Mercenary Type Counts</h3></p><ul>"
        for mercenary, count in mercenary_counts.items():
            html_output += f"<li>{mercenary}: {count}</li>"
        html_output += "</ul>"

        # Most common mercenary names
        html_output += "<h3>Most Common Mercenary Names</h3><ul>"
        for name, count in mercenary_names.most_common(10):
            html_output += f"<li>{name}: {count}</li>"
        html_output += "</ul>"

        # Popular Equipment by Mercenary Type
        html_output += "<p><h3>Popular Equipment by Mercenary Type</h3></p>"
        for mercenary, categories in mercenary_equipment.items():
            html_output += f"<div class='row'><p><strong>{mercenary}</strong></p>"
            for worn_category, items in categories.items():
                html_output += f"<div class='merccolumn'><strong>Most Common {worn_category}s:</strong>"
                html_output += "<ul>"
                top_items = items.most_common(15)  # Get the top 15 items
                for title, count in top_items:
                    html_output += f"<li>{title}: {count}</li>"
                html_output += "</ul></div>"
            html_output += "</div>"

        return html_output

    def _analyze_fun_facts(self, filtered_characters, what_class):
        """Analyze fun facts for softcore characters"""
        
        # Extract alive characters (not dead)
        alive_characters = [char for char in filtered_characters if not char.get("IsDead", True)]
        undead_count = len(alive_characters)
        character_count = len(filtered_characters)
        
        # Function to get the top 5 characters for a given stat
        def get_top_characters(stat_name):
            if stat_name in ["MagicFind", "GoldFind"]:
                # Special handling for MF and GF which come from Bonus stats
                ranked = sorted(
                    filtered_characters,
                    key=lambda c: (c.get("Bonus", {}).get(stat_name, 0) + 
                                 c.get("Bonus", {}).get("WeaponSetMain", {}).get(stat_name, 0) + 
                                 c.get("Bonus", {}).get("WeaponSetOffhand", {}).get(stat_name, 0)),
                    reverse=True,
                )[:5]
                
                return [(char.get('Name', 'Unknown'), 
                        c.get("Bonus", {}).get(stat_name, 0) + 
                        c.get("Bonus", {}).get("WeaponSetMain", {}).get(stat_name, 0) + 
                        c.get("Bonus", {}).get("WeaponSetOffhand", {}).get(stat_name, 0)) 
                       for char in ranked for c in [char]]
            else:
                # Regular stats from Stats section
                ranked = sorted(
                    filtered_characters,
                    key=lambda c: c.get("Stats", {}).get(stat_name, 0) + c.get("Bonus", {}).get(stat_name, 0),
                    reverse=True,
                )[:5]
                
                return [(char.get('Name', 'Unknown'), 
                        char.get('Stats', {}).get(stat_name, 0) + char.get('Bonus', {}).get(stat_name, 0)) 
                       for char in ranked]
        
        # Get stats data
        stats_data = {
            'alive_characters': alive_characters,
            'undead_count': undead_count,
            'character_count': character_count,
            'top_strength': get_top_characters("Strength"),
            'top_dexterity': get_top_characters("Dexterity"), 
            'top_vitality': get_top_characters("Vitality"),
            'top_energy': get_top_characters("Energy"),
            'top_life': get_top_characters("Life"),
            'top_mana': get_top_characters("Mana"),
            'top_magic_find': get_top_characters("MagicFind"),
            'top_gold_find': get_top_characters("GoldFind")
        }
        
        # Calculate averages and medians
        mf_values = []
        gf_values = []
        life_values = []
        mana_values = []
        
        total_mf = 0
        total_gf = 0
        total_life = 0
        total_mana = 0
        
        for char in filtered_characters:
            mf = (char.get("Bonus", {}).get("MagicFind", 0) + 
                  char.get("Bonus", {}).get("WeaponSetMain", {}).get("MagicFind", 0) + 
                  char.get("Bonus", {}).get("WeaponSetOffhand", {}).get("MagicFind", 0))
            gf = (char.get("Bonus", {}).get("GoldFind", 0) + 
                  char.get("Bonus", {}).get("WeaponSetMain", {}).get("GoldFind", 0) + 
                  char.get("Bonus", {}).get("WeaponSetOffhand", {}).get("GoldFind", 0))
            life = char.get("Stats", {}).get("Life", 0)
            mana = char.get("Stats", {}).get("Mana", 0)
            
            total_mf += mf
            total_gf += gf
            total_life += life
            total_mana += mana
            
            mf_values.append(mf)
            gf_values.append(gf)
            life_values.append(life)
            mana_values.append(mana)
        
        # Calculate averages and medians
        averages_medians = {
            'average_mf': total_mf / character_count if character_count > 0 else 0,
            'average_gf': total_gf / character_count if character_count > 0 else 0,
            'average_life': total_life / character_count if character_count > 0 else 0,
            'average_mana': total_mana / character_count if character_count > 0 else 0,
            'median_mf': statistics.median(mf_values) if mf_values else 0,
            'median_gf': statistics.median(gf_values) if gf_values else 0,
            'median_life': statistics.median(life_values) if life_values else 0,
            'median_mana': statistics.median(mana_values) if mana_values else 0
        }
        
        return {
            'stats_data': stats_data,
            'averages_medians': averages_medians,
            'class_name': what_class
        }


class ClassPagesHTMLGenerator:
    """Generates HTML for individual class pages with comprehensive content"""
    
    def __init__(self, is_hardcore=False, skill_weights=None):
        self.is_hardcore = is_hardcore
        self.mode_prefix = "hc" if is_hardcore else ""
        self.mode_name = "Hardcore" if is_hardcore else "Softcore"
        self.icons_folder = "icons"
        self.skill_weights = skill_weights or {}
    
    def generate_class_page(self, analysis_data, timestamp):
        """Generate complete HTML for a class page"""
        
        if not analysis_data or not analysis_data['clustering_results']:
            return self._generate_error_page(analysis_data['class_name'] if analysis_data else "Unknown")
        
        class_name = analysis_data['class_name']
        clustering_results = analysis_data['clustering_results']
        equipment_analysis = analysis_data['equipment_analysis']
        maxed_skills = analysis_data['maxed_skills']
        
        # Generate charts
        self._generate_clustering_charts(clustering_results, class_name)
        
        # Generate comprehensive HTML content
        html_content = self._generate_comprehensive_html(analysis_data, timestamp)
        
        return html_content
    
    def _generate_comprehensive_html(self, analysis_data, timestamp):
        """Generate the complete comprehensive HTML content"""
        
        class_name = analysis_data['class_name']
        character_count = analysis_data['character_count']
        clustering_results = analysis_data['clustering_results']
        equipment_analysis = analysis_data['equipment_analysis']
        maxed_skills = analysis_data['maxed_skills']
        filtered_characters = analysis_data['filtered_characters']
        
        # Generate intro summary
        intro_summary = self._generate_intro_summary(maxed_skills, character_count, class_name)
        
        # Generate charts section HTML
        charts_html = self._generate_charts_section(class_name)
        
        # Generate skill clusters HTML with detailed breakdowns
        clusters_html = self._generate_clusters_html(clustering_results, class_name)
        
        # Generate top/bottom skills section  
        top_bottom_skills_html = self._generate_top_bottom_skills_html(analysis_data.get('top_bottom_skills'), class_name)
        
        # Generate maxed skills section
        maxed_skills_html = self._generate_maxed_skills_section(maxed_skills, filtered_characters)
        
        # Generate comprehensive equipment sections
        equipment_sections_html = self._generate_all_equipment_sections(equipment_analysis, class_name)
        
        # Generate mercenary section
        mercenary_sections_html = self._generate_mercenary_section(analysis_data.get('mercenary_analysis', {}))
        
        # Generate fun facts section for both softcore and hardcore
        fun_facts_sections_html = self._generate_fun_facts_section(analysis_data.get('fun_facts_analysis', {}))
        
        # Meta tags
        meta_tag = f"{class_name}, path of diablo, builds, stats, statistics, data, analysis, analytics, trends"
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <link rel="stylesheet" type="text/css" href="./css/test-css.css">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Path of Diablo (PoD) {class_name} build trends. This page includes data analytics and statistics for {class_name} skills and equipment.">
        <meta name="keywords" content="{meta_tag}">
        <meta name="robots" content="index, follow">
            <title>{class_name} Analysis Report</title>

        </head>
        <body class="main special-background-{class_name.lower()}">
        <div class="is-clipped">
            <div id="navbar-placeholder"></div>
            <script>
            fetch("templates/navbar.html")
                .then(res => res.text())
                .then(html => {{
                document.getElementById("navbar-placeholder").innerHTML = html;
                }});
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
<div page-intro-class>
            <h1>{class_name} {self.mode_name} Skill Distribution </h1>
            <div class="summary-container">
            {intro_summary}
            <p class="indented-skills"> </p>

        {clusters_html}

        {top_bottom_skills_html}

        {maxed_skills_html}

        {equipment_sections_html}

        {mercenary_sections_html}

        {fun_facts_sections_html}

        {charts_html}

        </div>
        </div>
        
        {generate_standard_javascript()}
        <script src="pod-stats.js"></script>
        </body>
        </html>"""
        
        return html_template
    
    def _generate_charts_section(self, class_name):
        """Generate HTML section for charts"""
        charts_section = f"""
        <div class="analysis-section">
            <h2>Build Distribution Charts</h2>
            <div class="charts-container">
                <div class="chart-item">
                    <h3>Build Distribution</h3>
                    <img src="charts/{self.mode_prefix}{class_name.lower()}_distribution_pie.png" alt="{class_name} Build Distribution" class="chart-image">
                </div>
                <div class="chart-item">
                    <h3>Skill Clustering Visualization</h3>
                    <img src="charts/{self.mode_prefix}{class_name.lower()}_clusters_scatter.png" alt="{class_name} Skill Clusters" class="chart-image">
                </div>
            </div>
        </div>
        """
        return charts_section
    
    def _generate_intro_summary(self, maxed_skills, character_count, class_name):
        """Generate intro summary showing top maxed skills"""
        summary_lines = []
        for skill, characters in maxed_skills[:5]:  # Top 5 skills
            percentage = (len(characters) / character_count) * 100
            summary_lines.append(f"<strong>{percentage:.2f}% of all {class_name}s invest in {skill}</strong><br>")
        return "".join(summary_lines)
    
    def _generate_all_equipment_sections(self, equipment_analysis, class_name):
        """Generate all equipment sections matching class-test.py reference implementation"""
        
        # Generate HTML for each equipment section
        equipment_html = f"""
        <hr>
        <h1>Equipment and item details for {class_name}</h1>
        """
        
        # Runewords section
        equipment_html += self._generate_runewords_section(equipment_analysis)
        
        # Uniques section  
        equipment_html += self._generate_uniques_section(equipment_analysis)
        
        # Set items section
        equipment_html += self._generate_sets_section(equipment_analysis)
        
        # Synth items section
        equipment_html += self._generate_synth_section(equipment_analysis)
        
        # Crafted items section
        equipment_html += self._generate_crafted_section(equipment_analysis)
        
        # Magic items section
        equipment_html += self._generate_magic_section(equipment_analysis)
        
        # Rare items section
        equipment_html += self._generate_rare_section(equipment_analysis)
        
        # Socketable items section
        equipment_html += self._generate_socketable_section(equipment_analysis)
        
        return equipment_html

    def _generate_runewords_section(self, equipment_analysis):
        """Generate runewords section HTML"""
        most_popular = self._generate_list_items(equipment_analysis['most_common_runewords'])
        least_popular = self._generate_list_items(equipment_analysis['least_common_runewords'])
        all_runewords = self._generate_all_list_items(equipment_analysis['all_runewords'], equipment_analysis['runeword_users'])
        
        return f"""
        <button type="button" class="collapsible runewords-button">
            <img src="icons/Runewords.png" alt="Runewords Open" class="icon open-icon">
            <img src="icons/Runewords_click.png" alt="Runewords Close" class="icon close-icon hidden">
        </button>
        <div class="content">
            <div id="runewords" class="container">
                <div class="column">
                    <h3>Most Used Runewords:</h3>
                    <ul id="most-popular-runewords">
                        {most_popular}
                    </ul>
                </div>
                <div class="column">
                    <h3>Least Used Runewords:</h3>
                    <ul id="least-popular-runewords">
                        {least_popular}
                    </ul>
                </div>
            </div>

            <button type="button" class="collapsible small-collapsible">
                <img src="icons/closed.png" alt="All Runewords Open" class="icon-small open-icon">
                <img src="icons/open.png" alt="Runewords Close" class="icon-small close-icon hidden">
                <strong>ALL Runewords</strong>
            </button>

            <div class="content">
                <div id="allrunewords">
                    {all_runewords}
                </div>
            </div>
        </div>
        <br>
        """

    def _generate_uniques_section(self, equipment_analysis):
        """Generate uniques section HTML"""
        most_popular = self._generate_list_items(equipment_analysis['most_common_uniques'])
        least_popular = self._generate_list_items(equipment_analysis['least_common_uniques'])
        all_uniques = self._generate_all_list_items(equipment_analysis['all_uniques'], equipment_analysis['unique_users'])
        
        return f"""
        <button type="button" class="collapsible uniques-button">
            <img src="icons/Uniques.png" alt="Uniques Open" class="icon open-icon">
            <img src="icons/Uniques_click.png" alt="Uniques Close" class="icon close-icon hidden">
        </button>    
        <div class="content">   
            <div id="uniques" class="container">
                <div class="column">
                    <h3>Most Used Uniques:</h3>
                    <ul id="most-popular-uniques">
                        {most_popular}
                    </ul>
                </div>
                <div class="column">
                    <h3>Least Used Uniques:</h3>
                    <ul id="least_popular_uniques">
                        {least_popular}
                    </ul>
                </div>
            </div>
            <button type="button" class="collapsible small-collapsible">
                <img src="icons/closed.png" alt="All Uniques Open" class="icon-small open-icon">
                <img src="icons/open.png" alt="Uniques Close" class="icon-small close-icon hidden">
                <strong>ALL Uniques</strong>
            </button>

            <div class="content">
                <div id="alluniques">
                    {all_uniques}
                </div>
            </div>
        </div>
        <br>
        """

    def _generate_sets_section(self, equipment_analysis):
        """Generate set items section HTML"""
        most_popular = self._generate_list_items(equipment_analysis['most_common_set_items'])
        least_popular = self._generate_list_items(equipment_analysis['least_common_set_items'])
        all_set = self._generate_all_list_items(equipment_analysis['all_set'], equipment_analysis['set_users'])
        
        return f"""
        <button type="button" class="collapsible sets-button">
            <img src="icons/Sets.png" alt="Sets Open" class="icon open-icon">
            <img src="icons/Sets_click.png" alt="Sets Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="sets" class="container">
                <div class="column">
                    <h3>Most Used Set Items:</h3>
                    <ul id="most-popular-set-items">
                        {most_popular}
                    </ul>
                </div>
                <div class="column">
                    <h3>Least Used Set Items:</h3>
                    <ul id="least_popular_set_items">
                        {least_popular}
                    </ul>
                </div>
            </div>
            <button type="button" class="collapsible small-collapsible">
                <img src="icons/closed.png" alt="All Set Open" class="icon-small open-icon">
                <img src="icons/open.png" alt="Set Close" class="icon-small close-icon hidden">
                <strong>ALL Set</strong>
            </button>

            <div class="content">
                <div id="allset">
                    {all_set}
                </div>
            </div>
        </div>
        <br>
        """

    def _generate_synth_section(self, equipment_analysis):
        """Generate synth items section HTML"""
        all_synth = self._generate_synth_list_items(equipment_analysis['synth_counter'], equipment_analysis['synth_users'])
        synth_sources = self._generate_synth_source_list(equipment_analysis['synth_sources'])
        
        return f"""
        <h2>Synth reporting</h2>
        <h2 id="synth-items">
            {equipment_analysis['synth_user_count']} Characters with Synthesized items equipped
            <a href="#synth-items" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>This is base synthesized items</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="special">
                {all_synth}
            </div>
        </div>

        <h2 id="synth-from">
            {equipment_analysis['synth_source_user_count']} Synthesized FROM listings
            <a href="#synth-from" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>This shows where propertied an item are showing up in other items. If you wanted to see where the slow from Kelpie or the Ball light from Ondal's had popped up, this is where to look </h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="special">
                {synth_sources}
            </div>
        </div>
        <br>
        """

    def _generate_crafted_section(self, equipment_analysis):
        """Generate crafted items section HTML"""
        all_crafted = self._generate_crafted_list_items(equipment_analysis['crafted_counters'], equipment_analysis['crafted_users'])
        
        return f"""
        <h2 id="craft-reporting">Craft reporting
            <a href="#craft-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>        
        <h3>{equipment_analysis['craft_user_count']} Characters with crafted items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="special">
                {all_crafted}
            </div>
        </div>
        <br>
        """

    def _generate_magic_section(self, equipment_analysis):
        """Generate magic items section HTML"""
        all_magic = self._generate_magic_list_items(equipment_analysis['magic_counters'], equipment_analysis['magic_users'])
        
        return f"""
        <h2 id="magic-reporting">Magic reporting
            <a href="#magic-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>{equipment_analysis['magic_user_count']} Characters with Magic items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="special">
                {all_magic}
            </div>
        </div>
        <br>
        """

    def _generate_rare_section(self, equipment_analysis):
        """Generate rare items section HTML"""
        all_rare = self._generate_rare_list_items(equipment_analysis['rare_counters'], equipment_analysis['rare_users'])
        
        return f"""
        <h2 id="rare-reporting">Rare reporting
            <a href="#rare-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>{equipment_analysis['rare_user_count']} Characters with rare items equipped</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <div id="special">
                {all_rare}
            </div>
        </div>
        <br>
        """

    def _generate_socketable_section(self, equipment_analysis):
        """Generate socketable items section HTML"""
        
        return f"""
        <h2 id="socketable-reporting">Socketable reporting
            <a href="#socketable-reporting" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <h3>What are people puting in sockets</h3>

        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Synth Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Synth Close" class="icon close-icon hidden">
        </button>  
        <div class="content">  
            <h2>Socketed Runes Count</h2>
            <h3>Includes Only Character Data, No Mercs</h3>
            <div id="special" class="container">
                <br>
                <div class="column">
                    <!-- Left Column -->
                    <h2>Most Common Runes <br>(Including Runewords)</h2>
                    <ul id="sorted_just_socketed_runes">
                        {equipment_analysis['socketed_runes_html']}
                    </ul>
                </div>

                <!-- Right Column -->
                <div class="column">
                    <h2>Most Common Runes <br>(Excluding Runewords)</h2>
                    <ul id="sorted_just_socketed_excluding_runewords_runes">
                        {equipment_analysis['socketed_excluding_runes_html']}
                    </ul>
                </div>
            </div>

            <div>
                <h2>Other Items Found in Sockets</h2>
                <h3>Includes Only Character Data, No Mercs</h3>
                {equipment_analysis['other_items_html']}
            </div>
        </div>
        <hr>
        """

    def _generate_mercenary_section(self, mercenary_analysis):
        """Generate mercenary section HTML matching class-test.py format"""
        if not mercenary_analysis or not mercenary_analysis.get('html_output'):
            return ""
            
        return f"""
        <h1>Mercenary reporting</h1>
        <h3 id="merc-equipment">
            Mercenary counts and Most Used Runewords, Uniques, and Set items equipped
            <a href="#merc-equipment" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h3>

        <button type="button" class="collapsible">
            <img src="icons/Merc.png" alt="Merc Details Open" class="icon open-icon">
            <img src="icons/Merc_click.png" alt="Merc Details Close" class="icon close-icon hidden">
        </button>
        <div class="content">
            <div id="mercequips">
                {mercenary_analysis['html_output']}
            </div>
        </div>
        <hr>
        """

    def _generate_fun_facts_section(self, fun_facts_analysis):
        """Generate fun facts section HTML for both softcore and hardcore"""
        if not fun_facts_analysis:
            return ""
            
        stats_data = fun_facts_analysis['stats_data']
        averages_medians = fun_facts_analysis['averages_medians']
        what_class = fun_facts_analysis['class_name']
        
        # Different titles and descriptions for hardcore vs softcore
        if self.is_hardcore:
            section_title = "Hardcore Fun Facts"
            death_text = f"{stats_data['undead_count']} {what_class}'s out of {stats_data['character_count']} are still alive"
        else:
            section_title = "Softcore Fun Facts"
            death_text = f"{stats_data['undead_count']} {what_class}'s out of {stats_data['character_count']} have not died"
        
        # Generate alive characters list
        alive_list_html = "".join(
            f'''
            <div class="character-info">
                <div class="character-link">
                    <a href="https://beta.pathofdiablo.com/armory?name={char.get("Name", "Unknown")}" target="_blank">
                        {char.get("Name", "Unknown")}
                    </a>
                </div>
                <div>Level {char.get("Stats", {}).get("Level", "N/A")}</div>
                <div class="hover-trigger" data-character-name="{char.get("Name", "Unknown")}"></div>
            </div>
            <div class="character">
                <div class="popup hidden"></div> <!-- No iframe inside initially -->
            </div>
            ''' for char in stats_data['alive_characters']
        )
        
        # Generate top 5 lists
        def format_top_list(top_data):
            return "".join(
                f'''<li>&nbsp;&nbsp;&nbsp;&nbsp;
                    <a href="https://beta.pathofdiablo.com/armory?name={name}" target="_blank">
                        {name} ({value})
                    </a>
                </li>'''
                for name, value in top_data
            )
        
        return f'''
        <h3 id="fun-facts">{section_title} <a href="#fun-facts" class="anchor-link"><img src="icons/anchor.png" alt="🔗" class="anchor-icon"></a></h3>
        <h3>{death_text}</h3>
        <button type="button" class="collapsible sets-button">
            <img src="icons/Special.png" alt="Undead Open" class="icon open-icon">
            <img src="icons/Special_click.png" alt="Undead Close" class="icon close-icon hidden">
        </button>
        <div class="content">  
            <div id="special">{alive_list_html}</div>
        </div>
        <br>

        <!-- Strength & Dexterity Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Strength:</h3>
                <ul>{format_top_list(stats_data['top_strength'])}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Dexterity:</h3>
                <ul>{format_top_list(stats_data['top_dexterity'])}</ul>
            </div>
        </div>

        <!-- Vitality & Energy Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Vitality:</h3>
                <ul>{format_top_list(stats_data['top_vitality'])}</ul>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Energy:</h3>
                <ul>{format_top_list(stats_data['top_energy'])}</ul>
            </div>
        </div>

        <!-- Life & Mana Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Life:</h3>
                <ul>{format_top_list(stats_data['top_life'])}</ul>
                <p><strong>Average Life:</strong> {averages_medians['average_life']:.2f} | <strong>Median Life:</strong> {averages_medians['median_life']:.2f}</p>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Mana:</h3>
                <ul>{format_top_list(stats_data['top_mana'])}</ul>
                <p><strong>Average Mana:</strong> {averages_medians['average_mana']:.2f} | <strong>Median Mana:</strong> {averages_medians['median_mana']:.2f}</p>
            </div>
        </div>

        <!-- Magic Find & Gold Find Row -->
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Magic Find:</h3>
                <ul>{format_top_list(stats_data['top_magic_find'])}</ul>
                <p><strong>Average Magic Find:</strong> {averages_medians['average_mf']:.2f} | <strong>Median:</strong> {averages_medians['median_mf']:.2f}</p>
            </div>
            <div class="fun-facts-column">
                <h3>Top 5 {what_class}'s with the Most Gold Find:</h3>
                <ul>{format_top_list(stats_data['top_gold_find'])}</ul>
                <p><strong>Average Gold Find:</strong> {averages_medians['average_gf']:.2f} | <strong>Median:</strong> {averages_medians['median_gf']:.2f}</p>
            </div>
        </div>
        <hr>
        '''

    def _generate_list_items(self, items):
        """Generate simple list items for most/least popular sections"""
        return ''.join(
            f'<li><a href="#{self._slugify(name)}">{name}</a>: {count}</li>'
            for item, count in items
            for name in [  
                "Delirium" if item == "2693" else 
                "Pattern2" if item == "-26" else 
                item
            ]
        )

    def _generate_all_list_items(self, counter, character_data):
        """Generate comprehensive list items with character details"""
        if not isinstance(character_data, dict):
            return ""

        items_html = ""

        for item, count in counter:
            name = ("Delirium" if item == "2693" else 
                   "Pattern2" if item == "-26" else 
                   item)
            
            slug = self._slugify(name)
            users = character_data.get(item, [])
            
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
            <span id="{slug}"></span>
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Closed" class="icon-small close-icon hidden">
                <strong>{name} ({count} users)</strong>     
                <a href="#{slug}" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>
            </button>
            <div class="content">
                {character_list_html if users else "<p>No characters using this item.</p>"}
            </div>
            """

        return items_html

    def _generate_synth_list_items(self, counter, synth_users):
        """Generate synth items list with character details"""
        items_html = ""
        
        for item, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
            slug = self._slugify(item)
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

            items_html += f"""
            <span id="{slug}"></span>
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Closed" class="icon-small close-icon hidden">
                <strong>{item} ({count} users)</strong>     
                <a href="#{slug}" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>
            </button>
            <div class="content">
                {character_list_html if users else "<p>No characters using this synth item.</p>"}
            </div>
            """
        
        return items_html

    def _generate_synth_source_list(self, synth_sources):
        """Generate synth source list with character details"""
        items_html = ""

        for source_item, characters in sorted(synth_sources.items(), key=lambda x: (-len(x[1]), x[0])):
            slug = self._slugify(source_item)
            
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["name"]}" target="_blank">
                            {char["name"]}
                        </a>
                    </div>
                    <div>Level {char["level"]} {char["class"]}</div>
                    <div>Used in: <strong>{char["synthesized_item"]}</strong></div>
                    <div class="hover-trigger" data-character-name="{char["name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in characters
            )

            items_html += f"""
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="All Runewords Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Runewords Close" class="icon-small close-icon hidden">
                <strong>
                <a href="#synthsource-{slug}" class="anchor-link">
                    {source_item} (Found in {len(characters)} Items)
                </a>
                </strong>
            </button>
            <div class="content" id="synthsource-{slug}">
                {character_list_html if characters else "<p>No characters using this item.</p>"}
            </div>
            """

        return items_html

    def _generate_crafted_list_items(self, crafted_counters, crafted_users):
        """Generate crafted items list by category"""
        items_html = ""

        for worn_category, counter in crafted_counters.items():
            if not counter:
                continue
            
            # Collect all characters in this category
            category_users = []
            for item, count in counter.items():
                category_users.extend(crafted_users[worn_category].get(item, []))

            # Skip categories with no users
            if not category_users:
                continue

            # Create the list of all users in this category
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
                """ for char in category_users
            )

            # Create a collapsible button for each category
            items_html += f"""
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="All Runewords Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Runewords Close" class="icon-small close-icon hidden">
                <strong>Crafted {worn_category} ({len(category_users)} users)</strong>
            </button>
            <div class="content">
                {character_list_html if category_users else "<p>No characters using crafted items in this category.</p>"}
            </div>
            """

        return items_html

    def _generate_magic_list_items(self, magic_counters, magic_users):
        """Generate magic items list by category"""
        items_html = ""

        for worn_category, counter in magic_counters.items():
            if not counter:
                continue
            
            # Collect all characters in this category
            category_users = []
            for item, count in counter.items():
                category_users.extend(magic_users[worn_category][item])

            # Skip categories with no users
            if not category_users:
                continue

            # Create the list of all users in this category
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
                """ for char in category_users
            )

            # Create a collapsible button for each category
            items_html += f"""
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="All Runewords Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Runewords Close" class="icon-small close-icon hidden">
                <strong>Magic {worn_category} ({len(category_users)} users)</strong>
            </button>
            <div class="content">
                {character_list_html if category_users else "<p>No characters using magic items in this category.</p>"}
            </div>
            """

        return items_html

    def _generate_rare_list_items(self, rare_counters, rare_users):
        """Generate rare items list by category"""
        items_html = ""

        for worn_category, counter in rare_counters.items():
            if not counter:
                continue
            
            # Collect all characters in this category
            category_users = []
            for item, count in counter.items():
                category_users.extend(rare_users[worn_category][item])

            # Skip categories with no users
            if not category_users:
                continue

            # Create the list of all users in this category
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
                """ for char in category_users
            )

            # Create a collapsible button for each category
            items_html += f"""
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="All Runewords Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Runewords Close" class="icon-small close-icon hidden">
                <strong>Rare {worn_category} ({len(category_users)} users)</strong>
            </button>
            <div class="content">
                {character_list_html if category_users else "<p>No characters using Rare items in this category.</p>"}
            </div>
            """

        return items_html

    def _slugify(self, name):
        """Convert name to URL-friendly slug"""
        return name.lower().replace(" ", "-").replace("'", "").replace('"', "")
    
    def _generate_maxed_skills_section(self, maxed_skills, filtered_characters):
        """Generate the maxed skills section matching class-test.py reference implementation"""
        section_html = ""
        
        # Sort skills by number of characters with 20 points  
        sorted_skills = sorted(maxed_skills, key=lambda x: len(x[1]), reverse=True)
        
        for skill_name, char_names in sorted_skills:
            # Get full character info from filtered_characters
            characters = [char for char in filtered_characters if char["Name"] in char_names]

            # Build character display block
            character_list_html = "".join(
                f"""
                <div class="character-info">
                    <div class="character-link">
                        <a href="https://beta.pathofdiablo.com/armory?name={char["Name"]}" target="_blank">
                            {char["Name"]}
                        </a>
                    </div>
                <div>Level {char.get("Stats", {}).get("Level", "?")} {char.get("Class", "Unknown")}</div>                        <div class="hover-trigger" data-character-name="{char["Name"]}"></div>
                </div>
                <div class="character">
                    <div class="popup hidden"></div>
                </div>
                """ for char in characters
            )

            # Collapsible block per maxed skill
            safe_skill_name = skill_name.replace(" ", "-")
            section_html += f"""
            <span id="{safe_skill_name}"></span>
            <button class="collapsible">
                <img src="icons/closed-grey.png" alt="Open" class="icon-small open-icon">
                <img src="icons/open-grey.png" alt="Closed" class="icon-small close-icon hidden">
                <strong>{skill_name} ({len(characters)} users)</strong>     
                <a href="#{safe_skill_name}" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>
            </button>
            <div class="content">
                {character_list_html if characters else "<p>No characters maxed this skill.</p>"}
            </div>
            """

        # Wrap in container with section header
        if section_html:
            return f"""
            <h3 id="maxed-skills">Maxed Skills
                <a href="#maxed-skills" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>
            </h3>
            <p>These skills have been maxed (20 points) by one or more characters.</p>
            <button type="button" class="collapsible sets-button">
                <img src="icons/Special.png" alt="Undead Open" class="icon open-icon">
                <img src="icons/Special_click.png" alt="Undead Close" class="icon close-icon hidden">
            </button>
            <div class="content">  
                <div id="special">{section_html}</div>
            </div>
            """
        else:
            return ""
    
    def _generate_clusters_html(self, clustering_results, class_name):
        """Generate HTML for detailed skill clusters display with characters and equipment"""
        df = clustering_results['df']
        cluster_col = clustering_results['cluster_column']
        cluster_sizes = clustering_results['cluster_sizes']
        skill_columns = clustering_results['skill_columns']
        
        clusters_html = ""
        
        # Sort clusters by size (descending)
        sorted_clusters = cluster_sizes.sort_values(ascending=False)
        
        for idx, (cluster_id, size) in enumerate(sorted_clusters.items()):
            cluster_data = df[df[cluster_col] == cluster_id]
            if cluster_data.empty:
                continue
                
            first_char = cluster_data.iloc[0]
            percentage = first_char['Percentage']
            label = first_char['Cluster_Label']
            
            # Calculate skill statistics for this cluster
            skill_stats = self._calculate_cluster_skill_stats(cluster_data, skill_columns)
            
            # Generate main skill bars for the cluster
            main_skills_html = self._generate_cluster_main_skills_html(skill_stats)
            
            # Generate "All Skills" collapsible section for this cluster
            all_skills_html = self._generate_cluster_all_skills_html(skill_stats)
            
            # Generate equipment analysis for this cluster
            equipment_html = self._generate_cluster_equipment_html(cluster_data)
            
            # Generate character listings for this cluster
            characters_html = self._generate_cluster_characters_html(cluster_data)
            
            clusters_html += f"""
        <div class="class-intro">
        <div id="skills" class="skills-container">
            <div class="column">
                <ul id="most-popular-skills">
                    <h2><div id="cluster-{cluster_id}">{percentage:.2f}% of {class_name}'s Main Skills:<a href="#cluster-{cluster_id}" class="anchor-link"><img src="icons/anchor.png" alt="🔗" class="anchor-icon"></a><br>
                    {main_skills_html}
                    </div></h2>
                </ul>
            </div>
        </div>
        
        {all_skills_html}
        
        {equipment_html}
        
        {characters_html}
        
        </div>
            """
        
        return clusters_html
    
    def _generate_top_bottom_skills_html(self, top_bottom_skills, class_name):
        """Generate top/bottom 5 skills section like class-test.py"""
        if not top_bottom_skills:
            return ""
        
        top_5 = top_bottom_skills['top_5_most_used_skills']
        bottom_5 = top_bottom_skills['bottom_5_least_used_skills']
        
        # Format top 5 skills
        top_skills_html = ""
        for skill, total_points in top_5.items():
            top_skills_html += f"<li>{skill}: {total_points:.0f}</li>\n"
        
        # Format bottom 5 skills
        bottom_skills_html = ""
        for skill, total_points in bottom_5.items():
            bottom_skills_html += f"<li>{skill}: {total_points:.0f}</li>\n"
        
        return f"""
            <h3>Top 5 Most Popular {class_name} Skills and total points invested:</h3>
            <ul>
            {top_skills_html}
            </ul>

            <h3>Top 5 Least Popular {class_name} Skills and total points invested:</h3>
            <ul>
            {bottom_skills_html}
            </ul>
            <br>
        """
    
    def _calculate_cluster_skill_stats(self, cluster_data, skill_columns):
        """Calculate skill statistics for a cluster"""
        skill_stats = {}
        total_chars = len(cluster_data)
        
        for skill in skill_columns:
            chars_with_skill = len(cluster_data[cluster_data[skill] > 0])
            avg_level = cluster_data[skill].mean()
            percentage = (chars_with_skill / total_chars) * 100
            
            skill_stats[skill] = {
                'percentage': percentage,
                'avg_level': avg_level,
                'char_count': chars_with_skill,
                'total_points': cluster_data[skill].sum()
            }
        
        return skill_stats
    
    def _generate_cluster_main_skills_html(self, skill_stats):
        """Generate main skill bars for a cluster"""
        # Get top skills by average level, then sort by skill weights for meaningful ordering
        top_skills_by_level = sorted(skill_stats.items(), key=lambda x: x[1]['avg_level'], reverse=True)[:8]
        
        # Now sort these top skills by weight (higher weight = more important = shown first)
        top_skills = sorted(top_skills_by_level, key=lambda x: self.skill_weights.get(x[0], 0), reverse=True)[:5]
        
        main_skills_html = ""
        for skill, stats in top_skills:
            if stats['avg_level'] >= 1:
                main_skills_html += f"""
                    <div class="skillbar-container">
                        <div class="skill-row">
                            <img src="{self.icons_folder}/{skill}.png" alt="{skill}" class="skill-icon">
                            <div class="skill-bar-container">
                                <div class="skill-bar">
                                    <span class="skill-label">{skill} ({stats['total_points']:.0f})</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
        
        return main_skills_html
    
    def _generate_cluster_all_skills_html(self, skill_stats):
        """Generate collapsible 'All Skills' section for a cluster"""
        
        # Sort skills by a combination of percentage and skill weights
        # First by weight (descending), then by percentage (descending) for equal weights
        sorted_skills = sorted(skill_stats.items(), 
                             key=lambda x: (self.skill_weights.get(x[0], 0), x[1]['percentage']), 
                             reverse=True)
        
        skills_html = ""
        skills_count = 0
        current_row = ""
        
        for skill, stats in sorted_skills:
            if stats['percentage'] > 5:  # Only show skills used by more than 5% of characters
                width = min(400, stats['percentage'] * 4)  # Scale width
                skill_item = f"<div class='skill-item'><div class='skillbar-container'><div class='skill-info'><img src='{self.icons_folder}/{skill}.png' alt='{skill}' class='skill-icon'> {skill} {stats['percentage']:.1f}% ({stats['total_points']:.0f})</div><div class='skill-mini-bar' style='width: {width}px;'></div></div></div>"
                
                current_row += skill_item
                skills_count += 1
                
                # Create new row every 2 skills
                if skills_count % 2 == 0:
                    skills_html += f"<div class='skills-row'>{current_row}</div>"
                    current_row = ""
        
        # Add remaining skill if any
        if current_row:
            skills_html += f"<div class='skills-row'>{current_row}</div>"
        
        return f"""
                <button type="button" class="collapsible small-collapsible">
        <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
        <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
                <strong>All Skills</strong></button>
                <div class="content">
                    <div><div class='skills-group'>{skills_html}</div></div>
                </div>
        """
    
    def _generate_cluster_equipment_html(self, cluster_data):
        """Generate equipment analysis for a cluster"""
        
        # Analyze equipment for this cluster
        equipment_stats = defaultdict(lambda: defaultdict(int))
        
        for _, char in cluster_data.iterrows():
            equipment_str = char.get('Equipment', '')
            # Parse equipment string to extract items by slot
            # This is a simplified version - the original is more complex
            if equipment_str:
                items = equipment_str.split(', ')
                for item in items:
                    if ':' in item:
                        slot, item_name = item.split(':', 1)
                        slot = slot.strip()
                        item_name = item_name.strip()
                        equipment_stats[slot][item_name] += 1
        
        # Generate equipment HTML
        equipment_html = ""
        for slot, items in equipment_stats.items():
            if items:
                sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)
                slot_html = f"<strong>{slot}</strong>: <br>"
                
                for item, count in sorted_items[:5]:  # Top 5 items per slot
                    percentage = (count / len(cluster_data)) * 100
                    slot_html += f"&nbsp;&nbsp;&nbsp;&nbsp;{item} {percentage:.2f}% ({count})<br>"
                
                equipment_html += slot_html
        
        return f"""
                <button type="button" class="collapsible small-collapsible">
        <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
        <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
                <strong>Most Common Equipment:</strong></button>
                <div class="content">
                    <div>{equipment_html}</div>
                </div>
        """
    
    def _generate_cluster_characters_html(self, cluster_data):
        """Generate character listings for a cluster"""
        
        characters_html = ""
        char_count = len(cluster_data)
        
        for _, char in cluster_data.iterrows():
            name = char.get('Name', 'Unknown')
            level = char.get('Level', 'Unknown')
            skills = char.get('Skills', 'No skills data')
            equipment = char.get('Equipment', 'No equipment data')
            mercenary = char.get('Mercenary', 'No mercenary')
            merc_equipment = char.get('MercenaryEquipment', 'No equipment')
            
            characters_html += f"""
<div class="character-container char2" id="{name}">
    <div class="character-info">
        <div class="character-link"><strong>Name: <a href="https://beta.pathofdiablo.com/armory?name={name}" target="_blank">
                {name}
            </a></strong></div>
                <strong>Level: {level}</strong>
                <a href="#{name}" class="anchor-link">
                    <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
                </a>

        <div class="hover-trigger" data-character-name="{name}">
            <!-- Armory Quickview -->
        </div>
    </div>

    <div class="character">
        <div class="popup hidden"></div> <!-- No iframe inside initially -->
    </div>

    <p><strong>Skills:<br></strong> {skills}</p>
    <p><strong>Equipment:<br></strong> {equipment}</p>
    <p><strong>Mercenary:<br></strong> {mercenary} - {merc_equipment}</p>

    <div class="character-section" data-character-name="{name}"></div>
</div>
<hr color="#141414">
<br>
            """
        
        return f"""
            <button type="button" class="collapsible small-collapsible">
        <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
        <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
            <strong>{char_count} Characters in this cluster:</strong>
        </button>
        <div class="content">
{characters_html}
        </div>
        """
    
    def _generate_all_skills_html(self, clustering_results):
        """Generate collapsible section with all skills"""
        df = clustering_results['df']
        skill_columns = clustering_results['skill_columns']
        
        # Calculate overall skill usage
        skill_usage = {}
        total_chars = len(df)
        
        for skill in skill_columns:
            chars_with_skill = len(df[df[skill] > 0])
            avg_level = df[skill].mean()
            percentage = (chars_with_skill / total_chars) * 100
            skill_usage[skill] = {
                'percentage': percentage,
                'avg_level': avg_level,
                'char_count': chars_with_skill
            }
        
        # Sort by a combination of skill weights and percentage
        sorted_skills = sorted(skill_usage.items(), 
                             key=lambda x: (self.skill_weights.get(x[0], 0), x[1]['percentage']), 
                             reverse=True)
        
        skills_html = ""
        for skill, data in sorted_skills:
            if data['percentage'] > 5:  # Only show skills used by more than 5% of characters
                width = min(400, data['percentage'] * 4)  # Scale width
                skills_html += f"""
                <div class='skill-item'><div class='skillbar-container'><div class='skill-info'><img src='{self.icons_folder}/{skill}.png' alt='{skill}' class='skill-icon'> {skill} {data['percentage']:.1f}% ({data['avg_level']:.0f})</div><div class='skill-mini-bar' style='width: {width}px;'></div></div></div>
                """
        
        return f"""
    <button type="button" class="collapsible small-collapsible">
        <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
        <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
                <strong>All Skills</strong></button>
                <div class="content">
                    <div><div class='skills-group'><div class='skills-row'>{skills_html}</div></div></div>
                </div>
        """
    
    def _generate_equipment_sections(self, equipment_analysis, clustering_results):
        """Generate equipment analysis sections"""
        
        equipment_html = ""
        
        # Runewords section
        if equipment_analysis['runewords']:
            runewords_html = self._generate_equipment_category_html(
                equipment_analysis['runewords'], "Runewords", "runewords-button"
            )
            equipment_html += runewords_html
        
        # Uniques section
        if equipment_analysis['uniques']:
            uniques_html = self._generate_equipment_category_html(
                equipment_analysis['uniques'], "Unique Items", "uniques-button"
            )
            equipment_html += uniques_html
        
        # Sets section
        if equipment_analysis['sets']:
            sets_html = self._generate_equipment_category_html(
                equipment_analysis['sets'], "Set Items", "sets-button"
            )
            equipment_html += sets_html
        
        return equipment_html
    
    def _generate_equipment_category_html(self, category_data, category_name, button_class):
        """Generate HTML for a specific equipment category"""
        
        items_html = ""
        for slot, items in category_data.items():
            if items:
                sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)
                slot_html = f"<h3>{slot}</h3>"
                
                for item, count in sorted_items[:10]:  # Top 10 items per slot
                    percentage = (count / sum(items.values())) * 100
                    slot_html += f"""
                    <button type="button" class="collapsible small-collapsible">
                        <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
                        <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
                        <strong>{item} ({count} characters, {percentage:.1f}%)</strong>
                    </button>
                    <div class="content">
                        <div>Used by {count} characters in this category.</div>
                    </div>
                    """
                
                items_html += f'<div class="equipment-slot">{slot_html}</div>'
        
        return f"""
            <button type="button" class="collapsible {button_class}">
                <img src="icons/closed.png" alt="Open" class="icon-small open-icon">
                <img src="icons/open.png" alt="Close" class="icon-small close-icon hidden">
                <strong>{category_name}</strong>
            </button>
            <div class="content">
                <div>{items_html}</div>
            </div>
        """
    
    def _generate_clustering_charts(self, clustering_results, class_name):
        """Generate pie chart and scatter plot for clustering results"""
        
        df = clustering_results['df']
        reduced_data = clustering_results['reduced_data']
        cluster_col = clustering_results['cluster_column']
        
        # Ensure charts directory exists
        os.makedirs('charts', exist_ok=True)
        
        # Calculate pie chart data
        pie_data = df.groupby(cluster_col).agg({
            'Percentage': 'mean',
            'Cluster_Label': 'first'
        }).reset_index()
        
        # Create pie chart
        pie_data['Display_Label'] = pie_data.apply(
            lambda row: f"{row['Percentage']:.1f}% - {row['Cluster_Label']}", axis=1
        )
        
        fig_pie = px.pie(
            pie_data,
            values='Percentage',
            names='Display_Label',
            title=f"{self.mode_name} {class_name} Build Distribution"
        )
        
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            title=dict(font=dict(color='white')),
            width=900,
            height=600
        )
        
        # Save pie chart
        chart_filename = f"charts/{self.mode_prefix}{class_name.lower()}_distribution_pie.png"
        
        # Set plotly to use kaleido for image export
        pio.kaleido.scope.default_width = 900
        pio.kaleido.scope.default_height = 600
        
        try:
            fig_pie.write_image(chart_filename)
        except Exception as e:
            print(f"Warning: Could not save pie chart for {class_name}: {e}")
            # Create a simple HTML-based chart as fallback
            return
        
        # Create scatter plot
        plot_data = pd.DataFrame({
            'PCA1': reduced_data[:, 0],
            'PCA2': reduced_data[:, 1],
            'Cluster': df[cluster_col],
            'Cluster_Label': df['Cluster_Label']
        })
        
        fig_scatter = px.scatter(
            plot_data,
            x='PCA1',
            y='PCA2',
            color='Cluster',
            title=f"{self.mode_name} {class_name} Skill Clusters",
            hover_data=['Cluster_Label']
        )
        
        fig_scatter.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            xaxis_showticklabels=False,
            yaxis_showticklabels=False
        )
        
        # Save scatter plot
        scatter_filename = f"charts/{self.mode_prefix}{class_name.lower()}_clusters_scatter.png"
        
        try:
            fig_scatter.write_image(scatter_filename)
        except Exception as e:
            print(f"Warning: Could not save scatter chart for {class_name}: {e}")
            return
        
        print(f"✓ Generated charts for {class_name}")
    
    def _generate_error_page(self, class_name):
        """Generate error page when analysis fails"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{self.mode_name} {class_name} - Error</title>
</head>
<body>
    <h1>Error Generating {class_name} Page</h1>
    <p>Unable to generate analysis for {class_name}. Insufficient data or analysis error.</p>
</body>
</html>"""
        """Generate pie chart and scatter plot for clustering results"""
        
        df = clustering_results['df']
        reduced_data = clustering_results['reduced_data']
        
        # Ensure charts directory exists
        os.makedirs('charts', exist_ok=True)
        
        # Calculate pie chart data
        pie_data = df.groupby('Cluster').agg({
            'Percentage': 'mean',
            'Cluster_Label': 'first'
        }).reset_index()
        
        # Create pie chart
        pie_data['Display_Label'] = pie_data.apply(
            lambda row: f"{row['Percentage']:.1f}% - {row['Cluster_Label']}", axis=1
        )
        
        fig_pie = px.pie(
            pie_data,
            values='Percentage',
            names='Display_Label',
            title=f"{self.mode_name} {class_name} Build Distribution"
        )
        
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            title=dict(font=dict(color='white')),
            width=900,
            height=600
        )
        
        # Save pie chart
        chart_filename = f"charts/{self.mode_prefix}{class_name.lower()}_distribution_pie.png"
        
        # Set plotly to use kaleido for image export
        pio.kaleido.scope.default_width = 900
        pio.kaleido.scope.default_height = 600
        
        try:
            fig_pie.write_image(chart_filename)
        except Exception as e:
            print(f"Warning: Could not save pie chart for {class_name}: {e}")
            # Create a simple HTML-based chart as fallback
            return
        
        # Create scatter plot
        plot_data = pd.DataFrame({
            'PCA1': reduced_data[:, 0],
            'PCA2': reduced_data[:, 1],
            'Cluster': df['Cluster'],
            'Cluster_Label': df['Cluster_Label']
        })
        
        fig_scatter = px.scatter(
            plot_data,
            x='PCA1',
            y='PCA2',
            color='Cluster',
            title=f"{self.mode_name} {class_name} Skill Clusters",
            hover_data=['Cluster_Label']
        )
        
        fig_scatter.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            xaxis_showticklabels=False,
            yaxis_showticklabels=False
        )
        
        # Save scatter plot
        scatter_filename = f"charts/{self.mode_prefix}{class_name.lower()}_clusters_scatter.png"
        
        try:
            fig_scatter.write_image(scatter_filename)
        except Exception as e:
            print(f"Warning: Could not save scatter chart for {class_name}: {e}")
            return
        
        print(f"✓ Generated charts for {class_name}")
    
    def _generate_html_content(self, analysis_data, timestamp):
        """Generate the complete HTML content"""
        
        class_name = analysis_data['class_name']
        character_count = analysis_data['character_count']
        clustering_results = analysis_data['clustering_results']
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.mode_name} {class_name} Builds - PoD Analytics</title>
    <link rel="stylesheet" href="css/test-css.css">
    <link rel="icon" type="image/x-icon" href="icons/pod.ico">
</head>
<body>
    <div id="navbar-placeholder"></div>
    <script>
    fetch("templates/navbar.html")
        .then(res => res.text())
        .then(html => {{
        document.getElementById("navbar-placeholder").innerHTML = html;
        }});
    </script>
    
    <div class="container">
        <h1>{self.mode_name} {class_name} Build Analysis</h1>
        <p class="subtitle">Analysis of {character_count} {class_name} characters</p>
        <p class="timestamp">Generated: {timestamp}</p>
        
        <div class="analysis-section">
            <h2>Build Distribution</h2>
            <img src="charts/{self.mode_prefix}{class_name.lower()}_distribution_pie.png" alt="{class_name} Build Distribution" class="chart-image">
        </div>
        
        <div class="analysis-section">
            <h2>Skill Clustering Visualization</h2>
            <img src="charts/{self.mode_prefix}{class_name.lower()}_clusters_scatter.png" alt="{class_name} Skill Clusters" class="chart-image">
        </div>
        
        <div class="cluster-details">
            <h2>Detailed Build Analysis</h2>
            {self._generate_cluster_details_html(clustering_results)}
        </div>
    </div>
    
    {generate_standard_javascript()}
</body>
</html>"""
        
        return html_template
    
    def _generate_cluster_details_html(self, clustering_results):
        """Generate detailed HTML for cluster information"""
        
        df = clustering_results['df']
        skill_averages = clustering_results['skill_averages']
        cluster_sizes = clustering_results['cluster_sizes']
        
        details_html = ""
        
        # Sort clusters by size (descending)
        sorted_clusters = cluster_sizes.sort_values(ascending=False)
        
        for cluster_id in sorted_clusters.index:
            cluster_data = df[df['Cluster'] == cluster_id].iloc[0]
            percentage = cluster_data['Percentage']
            label = cluster_data['Cluster_Label']
            size = cluster_sizes[cluster_id]
            
            # Get top skills for this cluster
            top_skills = skill_averages.loc[cluster_id].nlargest(5)
            skills_html = ""
            for skill, avg in top_skills.items():
                if avg >= 1:
                    skills_html += f"<li>{skill}: {avg:.1f} avg points</li>"
            
            details_html += f"""
            <div class="cluster-detail">
                <h3>Build Type {cluster_id + 1}: {label}</h3>
                <p><strong>{size} characters ({percentage:.1f}%)</strong></p>
                <div class="skills-list">
                    <h4>Top Skills:</h4>
                    <ul>{skills_html}</ul>
                </div>
            </div>
            """
        
        return details_html
    
    def _generate_error_page(self, class_name):
        """Generate error page when analysis fails"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{self.mode_name} {class_name} - Error</title>
</head>
<body>
    <h1>Error Generating {class_name} Page</h1>
    <p>Unable to generate analysis for {class_name}. Insufficient data or analysis error.</p>
</body>
</html>"""


def generate_all_class_pages(all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """Main function to generate all class pages
    
    Note: Level filtering is now applied in the main script before calling this function,
    but we keep the parameters for consistency and future use.
    """
    
    print(f"🎭 Generating {('Hardcore' if is_hardcore else 'Softcore')} class pages...")
    
    analyzer = ClassPagesAnalyzer(all_characters, is_hardcore)
    html_generator = ClassPagesHTMLGenerator(is_hardcore, analyzer.skill_weights)
    
    generated_pages = []
    
    for class_config in analyzer.classes:
        class_name = class_config['what_class']
        print(f"Generating {class_name} page...")
        
        # Analyze the class with threshold
        analysis_data = analyzer.analyze_class_builds(
            class_config['what_class'],
            class_config['howmany_clusters'], 
            class_config['howmany_skills'],
            class_config['threshold']
        )
        
        if analysis_data:
            # Generate HTML
            html_content = html_generator.generate_class_page(analysis_data, timestamp)
            
            # Save the page
            mode_prefix = "hc" if is_hardcore else ""
            filename = f"{mode_prefix}{class_name}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            generated_pages.append(filename)
            print(f"✓ {class_name} page saved as {filename}")
        else:
            print(f"✗ Failed to generate {class_name} page")
    
    print(f"✅ Generated {len(generated_pages)} class pages")
    return generated_pages


def generate_single_class_page(class_name, all_characters, timestamp, is_hardcore=False, hc_level_filter=None):
    """Generate a single class page
    
    Note: Level filtering is now applied in the main script before calling this function,
    but we keep the parameters for consistency and future use.
    """
    
    analyzer = ClassPagesAnalyzer(all_characters, is_hardcore)
    html_generator = ClassPagesHTMLGenerator(is_hardcore, analyzer.skill_weights)
    
    # Find class configuration
    class_config = None
    for config in analyzer.classes:
        if config['what_class'].lower() == class_name.lower():
            class_config = config
            break
    
    if not class_config:
        print(f"Unknown class: {class_name}")
        return None
    
    print(f"Generating {class_name} page...")
    
    # Analyze the class with threshold
    analysis_data = analyzer.analyze_class_builds(
        class_config['what_class'],
        class_config['howmany_clusters'],
        class_config['howmany_skills'], 
        class_config['threshold']
    )
    
    if analysis_data:
        # Generate HTML
        html_content = html_generator.generate_class_page(analysis_data, timestamp)
        
        # Save the page
        mode_prefix = "hc" if is_hardcore else ""
        filename = f"{mode_prefix}{class_name}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ {class_name} page saved as {filename}")
        return filename
    else:
        print(f"✗ Failed to generate {class_name} page")
        return None