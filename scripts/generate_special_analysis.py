#!/usr/bin/env python3
"""
Special Analysis Page Generator
Generates specialized analysis pages for Path of Diablo analytics:
- Notazons (Non-Amazon bow users)
- Unique_Bolts_and_Arrows (Unique projectile users)
- 2AuraItems (Multiple aura item users)

Uses the new modular template system.
"""

import sys
from pathlib import Path

# Add the modules to the path
sys.path.append(str(Path(__file__).parent / "scripts" / "modules"))

from page_generator import PageGenerator, TemplateManager
from special_analysis_processor import SpecialAnalysisProcessor

class SpecialAnalysisGenerator:
    def __init__(self):
        self.page_generator = PageGenerator()
        self.data_processor = SpecialAnalysisProcessor()
        self.template_manager = TemplateManager()
        
        # Configuration for each special analysis
        self.analysis_configs = {
            'notazons': {
                'name': 'Notazons',
                'title': 'Non-Amazon Bow Users',
                'description': 'Characters using bows/crossbows who are not Amazons',
                'search_tags': ['Bolts', 'Arrows'],
                'exclude_classes': ['Amazon'],
                'clusters': 6,
                'top_skills': 4,
                'output_filename': 'Notazons.html'
            },
            'unique_projectiles': {
                'name': 'Unique_Bolts_and_Arrows',
                'title': 'Unique Projectile Users',
                'description': 'Characters using unique arrows and bolts',
                'search_tags': ['Dragonbreath', 'Swiftheart', 'Moonfire', 'Frostbite', 'Hailstorm'],
                'item_type': 'unique',
                'clusters': 6,
                'top_skills': 4,
                'output_filename': 'Unique_Bolts_and_Arrows.html'
            },
            'dual_aura_items': {
                'name': '2AuraItems',
                'title': 'Dual Offensive Aura Items',
                'description': 'Characters wearing multiple aura-granting items',
                'search_tags': ['Dream', 'Dragon', 'Hand of Justice', 'Doom', 'Todesfaelle Flamme', 'Azurewrath'],
                'min_items': 2,
                'clusters': 6,
                'top_skills': 4,
                'output_filename': '2AuraItems.html'
            }
        }
    
    def generate_notazons_analysis(self, league='sc'):
        """Generate Non-Amazon bow users analysis"""
        config = self.analysis_configs['notazons']
        
        print(f"🏹 Generating {config['title']} analysis for {league.upper()}...")
        
        # Load character data
        characters = self.data_processor.load_character_data(league)
        
        # Filter for non-Amazon bow users
        filtered_chars = self.data_processor.filter_bow_users(
            characters, 
            config['search_tags'], 
            exclude_classes=config['exclude_classes']
        )
        
        if not filtered_chars:
            print(f"No {config['title']} found in {league.upper()}")
            return False
        
        print(f"Found {len(filtered_chars)} {config['title']} characters")
        
        # Perform clustering analysis
        analysis_data = self.data_processor.perform_clustering_analysis(
            filtered_chars,
            config['clusters'],
            config['top_skills']
        )
        
        # Add mercenary analysis
        merc_data = self.data_processor.analyze_mercenaries(filtered_chars)
        
        # Generate charts
        chart_data = self.data_processor.generate_charts(
            analysis_data,
            config['name'],
            league
        )
        
        # Prepare template data
        template_data = {
            'analysis_config': config,
            'league': league.upper(),
            'character_count': len(filtered_chars),
            'clusters': analysis_data['clusters'],
            'top_skills': analysis_data['top_skills'],
            'bottom_skills': analysis_data['bottom_skills'],
            'mercenary_data': merc_data,
            'charts': chart_data,
            'characters': filtered_chars[:50]  # Show top 50 for character list
        }
        
        # Generate page
        output_path = f"pod-stats/{league}{config['output_filename']}" if league == 'hc' else f"pod-stats/{config['output_filename']}"
        
        success = self.page_generator.generate_special_analysis_page(
            template_data,
            output_path
        )
        
        if success:
            print(f"✅ {config['title']} analysis saved to {output_path}")
        
        return success
    
    def generate_unique_projectiles_analysis(self, league='sc'):
        """Generate unique projectile users analysis"""
        config = self.analysis_configs['unique_projectiles']
        
        print(f"🎯 Generating {config['title']} analysis for {league.upper()}...")
        
        # Load character data
        characters = self.data_processor.load_character_data(league)
        
        # Filter for unique projectile users
        filtered_chars = self.data_processor.filter_unique_projectile_users(
            characters,
            config['search_tags']
        )
        
        if not filtered_chars:
            print(f"No {config['title']} found in {league.upper()}")
            return False
        
        print(f"Found {len(filtered_chars)} {config['title']} characters")
        
        # Perform clustering analysis
        analysis_data = self.data_processor.perform_clustering_analysis(
            filtered_chars,
            config['clusters'],
            config['top_skills']
        )
        
        # Add mercenary analysis
        merc_data = self.data_processor.analyze_mercenaries(filtered_chars)
        
        # Generate charts
        chart_data = self.data_processor.generate_charts(
            analysis_data,
            config['name'],
            league
        )
        
        # Prepare template data
        template_data = {
            'analysis_config': config,
            'league': league.upper(),
            'character_count': len(filtered_chars),
            'clusters': analysis_data['clusters'],
            'top_skills': analysis_data['top_skills'],
            'bottom_skills': analysis_data['bottom_skills'],
            'mercenary_data': merc_data,
            'charts': chart_data,
            'characters': filtered_chars[:50]
        }
        
        # Generate page
        output_path = f"pod-stats/{league}{config['output_filename']}" if league == 'hc' else f"pod-stats/{config['output_filename']}"
        
        success = self.page_generator.generate_special_analysis_page(
            template_data,
            output_path
        )
        
        if success:
            print(f"✅ {config['title']} analysis saved to {output_path}")
        
        return success
    
    def generate_dual_aura_analysis(self, league='sc'):
        """Generate dual aura items analysis"""
        config = self.analysis_configs['dual_aura_items']
        
        print(f"⚡ Generating {config['title']} analysis for {league.upper()}...")
        
        # Load character data
        characters = self.data_processor.load_character_data(league)
        
        # Filter for dual aura item users
        filtered_chars = self.data_processor.filter_multi_aura_users(
            characters,
            config['search_tags'],
            min_items=config['min_items']
        )
        
        if not filtered_chars:
            print(f"No {config['title']} found in {league.upper()}")
            return False
        
        print(f"Found {len(filtered_chars)} {config['title']} characters")
        
        # Perform clustering analysis
        analysis_data = self.data_processor.perform_clustering_analysis(
            filtered_chars,
            config['clusters'],
            config['top_skills']
        )
        
        # Add mercenary analysis
        merc_data = self.data_processor.analyze_mercenaries(filtered_chars)
        
        # Generate charts
        chart_data = self.data_processor.generate_charts(
            analysis_data,
            config['name'],
            league
        )
        
        # Prepare template data
        template_data = {
            'analysis_config': config,
            'league': league.upper(),
            'character_count': len(filtered_chars),
            'clusters': analysis_data['clusters'],
            'top_skills': analysis_data['top_skills'],
            'bottom_skills': analysis_data['bottom_skills'],
            'mercenary_data': merc_data,
            'charts': chart_data,
            'characters': filtered_chars[:50]
        }
        
        # Generate page
        output_path = f"pod-stats/{league}{config['output_filename']}" if league == 'hc' else f"pod-stats/{config['output_filename']}"
        
        success = self.page_generator.generate_special_analysis_page(
            template_data,
            output_path
        )
        
        if success:
            print(f"✅ {config['title']} analysis saved to {output_path}")
        
        return success
    
    def generate_all_special_analyses(self, leagues=['sc', 'hc']):
        """Generate all special analyses for specified leagues"""
        print("🎯 Generating All Special Analysis Pages")
        print("=" * 50)
        
        results = {}
        
        for league in leagues:
            print(f"\n📊 Processing {league.upper()} League...")
            
            league_results = {
                'notazons': self.generate_notazons_analysis(league),
                'unique_projectiles': self.generate_unique_projectiles_analysis(league),
                'dual_aura_items': self.generate_dual_aura_analysis(league)
            }
            
            results[league] = league_results
            
            successful = sum(league_results.values())
            total = len(league_results)
            print(f"✅ {league.upper()}: {successful}/{total} analyses completed successfully")
        
        # Summary
        print(f"\n" + "=" * 50)
        print("📋 GENERATION SUMMARY")
        print("=" * 50)
        
        for league, league_results in results.items():
            print(f"\n{league.upper()} League:")
            for analysis, success in league_results.items():
                status = "✅" if success else "❌"
                config = self.analysis_configs[analysis]
                print(f"  {status} {config['title']}")
        
        # Calculate total success rate
        total_success = sum(sum(league_results.values()) for league_results in results.values())
        total_analyses = sum(len(league_results) for league_results in results.values())
        
        print(f"\n🎯 Overall: {total_success}/{total_analyses} analyses completed")
        
        if total_success == total_analyses:
            print("🎉 All special analysis pages generated successfully!")
        else:
            print("⚠️  Some analyses failed. Check the output above for details.")
        
        return total_success == total_analyses

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate special analysis pages')
    parser.add_argument('--leagues', nargs='+', default=['sc', 'hc'], 
                       choices=['sc', 'hc'], help='Leagues to process')
    parser.add_argument('--analysis', choices=['notazons', 'unique_projectiles', 'dual_aura_items', 'all'],
                       default='all', help='Specific analysis to run')
    
    args = parser.parse_args()
    
    generator = SpecialAnalysisGenerator()
    
    if args.analysis == 'all':
        success = generator.generate_all_special_analyses(args.leagues)
    else:
        # Run specific analysis
        success = True
        for league in args.leagues:
            if args.analysis == 'notazons':
                result = generator.generate_notazons_analysis(league)
            elif args.analysis == 'unique_projectiles':
                result = generator.generate_unique_projectiles_analysis(league)
            elif args.analysis == 'dual_aura_items':
                result = generator.generate_dual_aura_analysis(league)
            
            success = success and result
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()