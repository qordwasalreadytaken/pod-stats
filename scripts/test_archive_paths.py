#!/usr/bin/env python3
"""
Test script for archive path configuration functionality
Tests path mapping, asset resolution, and HTML path conversion
"""

import sys
import os
from pathlib import Path

# Add the current directory to sys.path to import api_integration
sys.path.append(str(Path(__file__).parent))

import api_integration

def test_archive_path_configuration():
    """Test the complete archive path configuration functionality"""
    
    print("🔗 Testing Archive Path Configuration")
    print("=" * 50)
    
    # Test parameters
    season_number = 13
    
    print(f"Testing with Season {season_number}")
    print()
    
    # Test 1: Get path configuration for monthly archive
    print("📋 Test 1: Get Monthly Archive Path Configuration")
    monthly_config = api_integration.get_archive_path_configuration(season_number, "monthly")
    
    if monthly_config["success"]:
        print("✅ Monthly path configuration generated successfully!")
        print(f"  Levels deep: {monthly_config['levels_deep']}")
        print(f"  Root prefix: '{monthly_config['root_prefix']}'")
        print("  Asset paths:")
        for asset_type, path in monthly_config["paths"].items():
            print(f"    {asset_type}: {path}")
        print("  Specific files:")
        for file_type, path in monthly_config["files"].items():
            print(f"    {file_type}: {path}")
    else:
        print(f"❌ Monthly configuration failed: {monthly_config['error']}")
    print()
    
    # Test 2: Get path configuration for final archive
    print("📋 Test 2: Get Final Archive Path Configuration")
    final_config = api_integration.get_archive_path_configuration(season_number, "final")
    
    if final_config["success"]:
        print("✅ Final path configuration generated successfully!")
        print(f"  Archive type: {final_config['archive_info']['archive_type']}")
        print(f"  Archive name: {final_config['archive_info']['archive_name']}")
    else:
        print(f"❌ Final configuration failed: {final_config['error']}")
    print()
    
    # Test 3: Resolve specific asset paths
    print("🔍 Test 3: Resolve Specific Asset Paths")
    test_assets = [
        ("css", "test-css.css"),
        ("icons", "pod.ico"),
        ("templates", "navbar.html"),
        ("charts", "sc_class_distribution.png"),
        ("shared_charts", "build-pages-legend.png"),
        ("js", "pod-stats.js")
    ]
    
    for asset_type, filename in test_assets:
        resolved_path = api_integration.resolve_archive_asset_path(
            asset_type, filename, season_number, "monthly"
        )
        if resolved_path:
            print(f"  ✅ {asset_type}/{filename} → {resolved_path}")
        else:
            print(f"  ❌ Failed to resolve {asset_type}/{filename}")
    print()
    
    # Test 4: HTML Path Conversion
    print("🔄 Test 4: HTML Path Conversion")
    
    # Sample HTML content with live site paths
    sample_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <link rel="shortcut icon" type="image/x-icon" href="icons/pod.ico">
    <link rel="stylesheet" type="text/css" href="./css/test-css.css">
    <script src="js/pod-stats.js"></script>
</head>
<body>
    <div id="navbar-placeholder"></div>
    <script>
    fetch("templates/navbar.html")
        .then(res => res.text())
        .then(html => {
        document.getElementById("navbar-placeholder").innerHTML = html;
        });
    </script>
    
    <div>
        <img src="charts/sc_class_distribution.png">
        <img src="charts/build-pages-legend.png">
    </div>
</body>
</html>'''
    
    print("Converting sample HTML content...")
    conversion_result = api_integration.convert_live_site_paths_to_archive(
        sample_html, season_number, "monthly"
    )
    
    if conversion_result["success"]:
        print(f"✅ HTML conversion successful!")
        print(f"  Total conversions: {conversion_result['total_conversions']}")
        print("  Conversions made:")
        for conv in conversion_result["conversions"]:
            print(f"    {conv['type']}: {conv['matches']} matches")
            print(f"      Pattern: {conv['pattern']}")
            print(f"      Replacement: {conv['replacement']}")
        
        print("\n📝 Converted HTML Preview:")
        print("-" * 40)
        # Show first few lines of converted HTML
        converted_lines = conversion_result["converted_html"].split('\n')
        for i, line in enumerate(converted_lines[:15]):
            if 'href=' in line or 'src=' in line or 'fetch(' in line:
                print(f"  {i+1:2d}: {line}")
        print("    ... (truncated)")
        
    else:
        print(f"❌ HTML conversion failed: {conversion_result['error']}")
    print()
    
    # Test 5: Test different archive types
    print("🔄 Test 5: Compare Monthly vs Final Paths")
    monthly_css = api_integration.resolve_archive_asset_path("css", "test-css.css", season_number, "monthly")
    final_css = api_integration.resolve_archive_asset_path("css", "test-css.css", season_number, "final")
    
    print(f"Monthly CSS path: {monthly_css}")
    print(f"Final CSS path:   {final_css}")
    print(f"Paths identical: {monthly_css == final_css}")
    print()
    
    # Test 6: Error handling
    print("⚠️  Test 6: Error Handling")
    invalid_config = api_integration.get_archive_path_configuration(999, "invalid_type")
    
    if not invalid_config["success"]:
        print(f"✅ Error handling works: {invalid_config['error']}")
    else:
        print("❌ Expected error handling to fail with invalid parameters")
    print()
    
    print("🎉 Archive Path Configuration Testing Complete!")

if __name__ == "__main__":
    test_archive_path_configuration()