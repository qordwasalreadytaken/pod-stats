"""
Special Analysis Data Processor
Extends the base data processor with specialized filtering methods
for the three special analysis types.
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

class SpecialAnalysisProcessor:
    def __init__(self):
        self.bow_related_items = [
            'Bow', 'Crossbow', 'Amazon Bow', 'Amazon Spear',
            'Bolts', 'Arrows'
        ]
        
        self.unique_projectiles = [
            'Dragonbreath', 'Swiftheart', 'Moonfire', 
            'Frostbite', 'Hailstorm'
        ]
        
        self.aura_items = [
            'Dream', 'Dragon', 'Hand of Justice', 'Doom',
            'Todesfaelle Flamme', 'Azurewrath'
        ]
    
    def load_character_data(self, league='sc'):
        """Load character data for specified league"""
        data_file = f"{league.upper()}_Characters_Analysis.json"
        
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Data file {data_file} not found")
            return []
        except json.JSONDecodeError:
            print(f"❌ Error parsing {data_file}")
            return []
    
    def filter_bow_users(self, characters, search_tags, exclude_classes=None):
        """Filter characters who use bows but are not in excluded classes"""
        if exclude_classes is None:
            exclude_classes = []
        
        filtered = []
        
        for char in characters:
            # Skip if character is in excluded class
            if char.get('class') in exclude_classes:
                continue
            
            # Check if character uses bow-related items
            has_bow_items = False
            
            # Check equipped items
            for item in char.get('items', []):
                item_name = item.get('name', '')
                item_type = item.get('type', '')
                
                # Check for bow-related items
                if any(bow_item.lower() in item_name.lower() or 
                      bow_item.lower() in item_type.lower() 
                      for bow_item in self.bow_related_items):
                    has_bow_items = True
                    break
                
                # Check for search tags (bolts, arrows)
                if any(tag.lower() in item_name.lower() 
                      for tag in search_tags):
                    has_bow_items = True
                    break
            
            if has_bow_items:
                filtered.append(char)
        
        return filtered
    
    def filter_unique_projectile_users(self, characters, unique_items):
        """Filter characters who use unique projectiles"""
        filtered = []
        
        for char in characters:
            has_unique_projectile = False
            
            # Check equipped items
            for item in char.get('items', []):
                item_name = item.get('name', '')
                
                # Check for unique projectiles
                if any(unique_item.lower() in item_name.lower() 
                      for unique_item in unique_items):
                    has_unique_projectile = True
                    break
            
            if has_unique_projectile:
                filtered.append(char)
        
        return filtered
    
    def filter_multi_aura_users(self, characters, aura_items, min_items=2):
        """Filter characters who use multiple aura-granting items"""
        filtered = []
        
        for char in characters:
            aura_item_count = 0
            found_aura_items = []
            
            # Check equipped items
            for item in char.get('items', []):
                item_name = item.get('name', '')
                
                # Check for aura items
                for aura_item in aura_items:
                    if aura_item.lower() in item_name.lower():
                        aura_item_count += 1
                        found_aura_items.append(aura_item)
                        break  # Don't double-count same item
            
            if aura_item_count >= min_items:
                # Add metadata about found items
                char['found_aura_items'] = found_aura_items
                char['aura_item_count'] = aura_item_count
                filtered.append(char)
        
        return filtered
    
    def perform_clustering_analysis(self, characters, n_clusters=6, top_skills=4):
        """Perform clustering analysis on character data"""
        if len(characters) < n_clusters:
            n_clusters = len(characters)
        
        # Extract skill data for clustering
        skill_data = []
        character_indices = []
        
        for i, char in enumerate(characters):
            skills = char.get('skills', {})
            if skills:
                # Convert skills to numerical array
                skill_values = []
                for skill_name, skill_level in skills.items():
                    skill_values.append(skill_level)
                
                if skill_values:
                    skill_data.append(skill_values)
                    character_indices.append(i)
        
        if not skill_data:
            return {
                'clusters': [],
                'top_skills': [],
                'bottom_skills': []
            }
        
        # Pad skill data to same length
        max_skills = max(len(skills) for skills in skill_data)
        padded_data = []
        for skills in skill_data:
            padded = skills + [0] * (max_skills - len(skills))
            padded_data.append(padded[:max_skills])  # Ensure same length
        
        # Perform clustering
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(padded_data)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(scaled_data)
        
        # Organize characters by cluster
        clusters = defaultdict(list)
        for char_idx, cluster_label in zip(character_indices, cluster_labels):
            clusters[cluster_label].append(characters[char_idx])
        
        # Convert to list format
        cluster_list = []
        for cluster_id in sorted(clusters.keys()):
            cluster_chars = clusters[cluster_id]
            cluster_list.append({
                'id': cluster_id,
                'size': len(cluster_chars),
                'characters': cluster_chars,
                'representative_skills': self._get_cluster_representative_skills(cluster_chars)
            })
        
        # Get top and bottom skills across all characters
        all_skills = Counter()
        for char in characters:
            for skill, level in char.get('skills', {}).items():
                if level > 0:
                    all_skills[skill] += 1
        
        top_skills_list = [
            {'skill': skill, 'count': count, 'percentage': (count/len(characters))*100}
            for skill, count in all_skills.most_common(top_skills)
        ]
        
        bottom_skills_list = [
            {'skill': skill, 'count': count, 'percentage': (count/len(characters))*100}
            for skill, count in list(all_skills.most_common())[-top_skills:]
        ]
        
        return {
            'clusters': cluster_list,
            'top_skills': top_skills_list,
            'bottom_skills': bottom_skills_list
        }
    
    def _get_cluster_representative_skills(self, cluster_characters):
        """Get representative skills for a cluster"""
        skill_counts = Counter()
        
        for char in cluster_characters:
            for skill, level in char.get('skills', {}).items():
                if level > 0:
                    skill_counts[skill] += 1
        
        # Return top 3 skills for this cluster
        top_skills = skill_counts.most_common(3)
        return [
            {
                'skill': skill,
                'count': count,
                'percentage': (count/len(cluster_characters))*100
            }
            for skill, count in top_skills
        ]
    
    def analyze_mercenaries(self, characters):
        """Analyze mercenary usage patterns"""
        merc_types = Counter()
        merc_items = Counter()
        
        for char in characters:
            mercenary = char.get('mercenary', {})
            if mercenary:
                merc_type = mercenary.get('type', 'Unknown')
                merc_types[merc_type] += 1
                
                # Count mercenary items
                for item in mercenary.get('items', []):
                    item_name = item.get('name', 'Unknown')
                    merc_items[item_name] += 1
        
        total_chars = len(characters)
        
        return {
            'types': [
                {
                    'type': merc_type,
                    'count': count,
                    'percentage': (count/total_chars)*100
                }
                for merc_type, count in merc_types.most_common()
            ],
            'top_items': [
                {
                    'item': item,
                    'count': count,
                    'percentage': (count/total_chars)*100
                }
                for item, count in merc_items.most_common(10)
            ]
        }
    
    def generate_charts(self, analysis_data, analysis_name, league):
        """Generate chart data for visualization"""
        charts = {}
        
        # Cluster size distribution
        if analysis_data['clusters']:
            cluster_sizes = [cluster['size'] for cluster in analysis_data['clusters']]
            charts['cluster_distribution'] = {
                'type': 'pie',
                'data': {
                    'labels': [f"Cluster {i+1}" for i in range(len(cluster_sizes))],
                    'values': cluster_sizes
                },
                'title': f'Character Distribution by Cluster - {analysis_name} ({league.upper()})'
            }
        
        # Top skills bar chart
        if analysis_data['top_skills']:
            charts['top_skills'] = {
                'type': 'bar',
                'data': {
                    'labels': [skill['skill'] for skill in analysis_data['top_skills']],
                    'values': [skill['count'] for skill in analysis_data['top_skills']]
                },
                'title': f'Most Popular Skills - {analysis_name} ({league.upper()})'
            }
        
        return charts
    
    def get_character_summary_stats(self, characters):
        """Get summary statistics for characters"""
        if not characters:
            return {}
        
        levels = [char.get('level', 0) for char in characters]
        classes = Counter(char.get('class', 'Unknown') for char in characters)
        
        return {
            'total_characters': len(characters),
            'average_level': sum(levels) / len(levels) if levels else 0,
            'level_range': {
                'min': min(levels) if levels else 0,
                'max': max(levels) if levels else 0
            },
            'class_distribution': [
                {
                    'class': cls,
                    'count': count,
                    'percentage': (count/len(characters))*100
                }
                for cls, count in classes.most_common()
            ]
        }