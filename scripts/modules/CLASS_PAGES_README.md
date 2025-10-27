# Class Pages Module Documentation

## Overview

The class pages module provides comprehensive analysis and HTML generation for individual Diablo 2 class pages. It supports both softcore and hardcore modes with advanced clustering analysis and visualization.

## Features

- **Machine Learning Clustering**: Uses K-means clustering to identify build archetypes
- **Skill Analysis**: Analyzes maxed skills and build patterns
- **Interactive Charts**: Generates pie charts and scatter plots for build visualization
- **Mode Support**: Full support for both softcore and hardcore with proper prefixing
- **Modular Architecture**: Clean separation of analysis and HTML generation

## Usage

### Generate All Class Pages

```bash
# Softcore (default)
python3 scripts/generate_pages.py --page all

# Hardcore
python3 scripts/generate_pages.py --mode hc --data hc_ladder.json --page all
```

### Generate Single Class Page

```bash
# Softcore Barbarian
python3 scripts/generate_pages.py --page class --class Barbarian

# Hardcore Sorceress
python3 scripts/generate_pages.py --mode hc --data hc_ladder.json --page class --class Sorceress
```

### Available Classes

- Barbarian
- Druid 
- Amazon
- Assassin
- Necromancer
- Paladin
- Sorceress

## File Structure

### Generated Files
- **Softcore**: `{ClassName}.html` (e.g., `Barbarian.html`)
- **Hardcore**: `hc{ClassName}.html` (e.g., `hcBarbarian.html`)

### Charts Generated
- **Pie Charts**: `charts/{prefix}{classname}_distribution_pie.png`
- **Scatter Plots**: `charts/{prefix}{classname}_clusters_scatter.png`

## Class Configuration

Each class has optimized clustering parameters:

```python
classes = [
    {"what_class": "Barbarian", "howmany_clusters": 10, "howmany_skills": 5},
    {"what_class": "Druid", "howmany_clusters": 7, "howmany_skills": 5},
    {"what_class": "Amazon", "howmany_clusters": 11, "howmany_skills": 5},
    {"what_class": "Assassin", "howmany_clusters": 6, "howmany_skills": 5},
    {"what_class": "Necromancer", "howmany_clusters": 6, "howmany_skills": 5},
    {"what_class": "Paladin", "howmany_clusters": 6, "howmany_skills": 5},
    {"what_class": "Sorceress", "howmany_clusters": 10, "howmany_skills": 5}
]
```

## Class Analysis Output

Each class page includes:

1. **Character Count**: Total analyzed characters
2. **Build Distribution**: Pie chart showing build popularity
3. **Skill Clustering**: PCA-reduced scatter plot visualization
4. **Detailed Analysis**: 
   - Build archetypes with percentages
   - Top skills per build with average point allocation
   - Character counts per build type

## Technical Implementation

### ClassPagesAnalyzer
- Filters characters by class
- Performs K-means clustering on skill data
- Calculates build statistics and percentages
- Uses PCA for 2D visualization

### ClassPagesHTMLGenerator
- Creates responsive HTML pages
- Generates interactive charts using Plotly
- Handles both SC/HC mode prefixing
- Integrates with existing CSS/JS framework

## Dependencies

- pandas: Data manipulation
- scikit-learn: Machine learning (PCA, K-means)
- plotly: Chart generation
- jinja2: HTML templating
- items_list.py: Game data reference

## Error Handling

- Graceful fallback for insufficient data
- Chart generation error handling
- Missing class validation
- Data loading error recovery

## Integration

The class pages module integrates seamlessly with:
- Main page generation system (`generate_pages.py`)
- Shared utilities (`shared_utils.py`)
- Existing CSS/JS framework
- GitHub Pages deployment structure

## Migration Notes

This module replaces the monolithic `class-test.py` (3200+ lines) with:
- Clean modular architecture
- Unified SC/HC support
- Better error handling
- Improved maintainability
- Full integration with page generation system

## Example Output

```
🎭 Generating Softcore class pages...
Generating Barbarian page...
Analyzing 191 Barbarian characters...
✓ Generated charts for Barbarian
✓ Barbarian page saved as Barbarian.html
...
✅ Generated 7 class pages
```