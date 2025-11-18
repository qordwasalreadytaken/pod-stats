#!/usr/bin/env python3
"""
Test script for dynamic banner system functionality
Tests banner generation, text creation, and HTML injection
"""

import sys
import os
from pathlib import Path

# Add the current directory to sys.path to import api_integration
sys.path.append(str(Path(__file__).parent))

import api_integration

def test_banner_system():
    """Test the complete dynamic banner system functionality"""
    
    print("🏷️  Testing Dynamic Banner System")
    print("=" * 50)
    
    # Test parameters
    season_number = 13
    
    print(f"Testing with Season {season_number}")
    print()
    
    # Test 1: Generate banner text for different scenarios
    print("📝 Test 1: Generate Banner Text for Different Scenarios")
    
    test_scenarios = [
        ("monthly", "Monthly archive"),
        ("final", "Final archive")
    ]
    
    for archive_type, description in test_scenarios:
        banner_result = api_integration.generate_archive_banner_text(season_number, archive_type)
        
        if banner_result["success"]:
            print(f"✅ {description} banner text:")
            print(f"   Text: '{banner_result['banner_text']}'")
            print(f"   Season: {banner_result['season_number']}")
            print(f"   Status: {banner_result['season_status']}")
            print(f"   Folder: {banner_result['archive_folder']}")
        else:
            print(f"❌ {description} banner failed: {banner_result['error']}")
        print()
    
    # Test 2: Generate banner HTML
    print("🏷️  Test 2: Generate Banner HTML")
    
    for archive_type, description in test_scenarios:
        banner_html_result = api_integration.generate_archive_banner_html(season_number, archive_type)
        
        if banner_html_result["success"]:
            print(f"✅ {description} HTML banner generated:")
            print(f"   HTML: {banner_html_result['banner_html']}")
        else:
            print(f"❌ {description} HTML banner failed: {banner_html_result['error']}")
        print()
    
    # Test 3: Generate freeze banner
    print("🚨 Test 3: Generate Freeze Banner")
    freeze_banner_result = api_integration.generate_freeze_banner_html()
    
    if freeze_banner_result["success"]:
        print("✅ Freeze banner generated successfully:")
        print(f"   Text: '{freeze_banner_result['freeze_text']}'")
        print(f"   HTML: {freeze_banner_result['freeze_banner_html']}")
    else:
        print(f"❌ Freeze banner failed: {freeze_banner_result['error']}")
    print()
    
    # Test 4: Auto-detection with current season
    print("🔍 Test 4: Auto-Detection with Current Season")
    auto_banner = api_integration.generate_archive_banner_html(archive_type="monthly")
    
    if auto_banner["success"]:
        print("✅ Auto-detection successful:")
        print(f"   Detected season: {auto_banner['season_number']}")
        print(f"   Banner text: '{auto_banner['banner_text']}'")
    else:
        print(f"❌ Auto-detection failed: {auto_banner['error']}")
    print()
    
    # Test 5: HTML Banner Injection
    print("💉 Test 5: HTML Banner Injection")
    
    # Sample HTML content (simplified)
    sample_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page</title>
</head>
<body class="special-background">
    <nav class="navbar">
        <div>Navigation content</div>
    </nav>
    
    <div class="main page-intro">
        <h1>Main Content</h1>
        <p>This is the main content area.</p>
    </div>
</body>
</html>'''
    
    # Test different injection methods
    injection_methods = ["after_navbar", "after_body", "before_main"]
    
    for method in injection_methods:
        banner_html = '<div class="banner" style="top:50px; left:25%; width:50%;">Test Banner for ' + method + '</div>'
        
        injection_result = api_integration.inject_banner_into_html(sample_html, banner_html, method)
        
        if injection_result["success"]:
            print(f"✅ Injection method '{method}' successful")
            # Show a snippet of the modified HTML
            modified_lines = injection_result["modified_html"].split('\n')
            banner_line = next((i for i, line in enumerate(modified_lines) if 'Test Banner' in line), -1)
            if banner_line >= 0:
                print(f"   Banner injected at line {banner_line + 1}")
                # Show context around the banner
                start = max(0, banner_line - 2)
                end = min(len(modified_lines), banner_line + 3)
                for i in range(start, end):
                    marker = " -> " if i == banner_line else "    "
                    print(f"{marker}{i+1:2d}: {modified_lines[i]}")
        else:
            print(f"❌ Injection method '{method}' failed: {injection_result['error']}")
        print()
    
    # Test 6: Complete workflow
    print("🔄 Test 6: Complete Banner Workflow")
    
    # Generate a monthly archive banner and inject it
    complete_banner = api_integration.generate_archive_banner_html(season_number, "monthly")
    
    if complete_banner["success"]:
        injection = api_integration.inject_banner_into_html(
            sample_html, 
            complete_banner["banner_html"], 
            "after_navbar"
        )
        
        if injection["success"]:
            print("✅ Complete workflow successful!")
            print(f"   Generated banner: '{complete_banner['banner_text']}'")
            print("   Banner successfully injected into HTML")
            
            # Save a sample output file
            output_file = "test_banner_output.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(injection["modified_html"])
            print(f"   Sample output saved to: {output_file}")
        else:
            print(f"❌ Banner injection failed: {injection['error']}")
    else:
        print(f"❌ Banner generation failed: {complete_banner['error']}")
    print()
    
    # Test 7: Error handling
    print("⚠️  Test 7: Error Handling")
    
    # Test with invalid HTML
    invalid_html = "<html><body>No nav tag</body></html>"
    error_injection = api_integration.inject_banner_into_html(
        invalid_html, 
        "<div>Test Banner</div>", 
        "after_navbar"
    )
    
    if not error_injection["success"]:
        print(f"✅ Error handling works: {error_injection['error']}")
    else:
        print("❌ Expected error handling to fail with invalid HTML")
    print()
    
    print("🎉 Dynamic Banner System Testing Complete!")

if __name__ == "__main__":
    test_banner_system()