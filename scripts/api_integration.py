#!/usr/bin/env python3
"""
Complete API integration for Path of Diablo stats and server data
Updates unified CSV with both character data and server metrics
"""

import requests
import json
import csv
from collections import defaultdict
from datetime import datetime, timezone
import time

def fetch_server_stats():
    """Fetch global server statistics from PoD API"""
    try:
        response = requests.get('https://beta.pathofdiablo.com/api/stats', timeout=10)
        response.raise_for_status()
        data = response.json()
        # API returns an array with the stats object as the first element
        return data[0] if data and len(data) > 0 else None
    except requests.RequestException as e:
        print(f"❌ Error fetching server stats: {e}")
        return None

def fetch_game_servers():
    """Fetch individual game server data from PoD API"""
    try:
        response = requests.get('https://beta.pathofdiablo.com/api/servers', timeout=10)
        response.raise_for_status()
        data = response.json()
        # API returns an array of server objects
        return data if data else []
    except requests.RequestException as e:
        print(f"❌ Error fetching game servers: {e}")
        return []

def get_current_season_info():
    """Get current season number and start time from PoD API"""
    try:
        url = "https://beta.pathofdiablo.com/api/ladder-summaries"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        seasons = response.json()

        # First, try to find a current season
        for season in seasons:
            if season.get("current"):
                start_time_str = season["start"]
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                season_number = season["season"]
                return season_number, start_time, "current"

        # If no current season, find the most recent one and check if we're in post-season
        if seasons:
            latest_season = max(seasons, key=lambda s: s["season"])
            season_number = latest_season["season"]
            start_time_str = latest_season["start"]
            end_time_str = latest_season.get("end")
            
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            
            if end_time_str:
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                
                if now > end_time:
                    return season_number, start_time, "post_season"
                else:
                    return season_number, start_time, "current"
            else:
                return season_number, start_time, "current"

        raise ValueError("No season data found.")
    except requests.RequestException as e:
        print(f"❌ Error fetching season info: {e}")
        return None, None, None

def generate_snapshot_label():
    """Generate snapshot label based on current season progress (matches github-update-csv-web.py logic)"""
    season_number, start_time, season_status = get_current_season_info()
    
    if not season_number or not start_time:
        # Fallback to simple month name if API fails
        return datetime.now().strftime("%B")
    
    now = datetime.now(timezone.utc)
    
    if season_status == "post_season":
        return f"Post Season {season_number}"
    
    delta_days = (now - start_time).days

    if delta_days < 14:
        return f"S{season_number} Day {delta_days + 1}"
    elif delta_days < 49:
        week_number = ((delta_days - 14) // 7) + 2
        return f"S{season_number} Week {week_number}"
    else:
        month_name = now.strftime("%B")
        return f"S{season_number} {month_name}"

def fetch_character_data(league='sc'):
    """
    Fetch character ladder data (you'll need to implement this based on your existing method)
    For now, this loads from local files as a placeholder
    """
    filename = f"{league}_ladder.json"
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ {filename} not found, skipping {league.upper()} character data")
        return None

def update_unified_csv_from_character_data(characters, league, snapshot_label):
    """
    Update character skill/item data in unified CSV
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load existing CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Add new snapshot column if needed
    if snapshot_label not in fieldnames:
        fieldnames = list(fieldnames) + [snapshot_label]
        for row in rows:
            row[snapshot_label] = '0'
    
    # Create lookup for efficient updates
    row_lookup = {}
    for i, row in enumerate(rows):
        key = (row['Type'], row['League'], row['Class'], row['Name'])
        row_lookup[key] = i
    
    # Count character usage
    usage_counter = defaultdict(lambda: [0, 0])  # [normal, synth]
    
    for char in characters:
        cls = char.get("Class")
        
        # Count skills
        for tab in char.get("SkillTabs", []):
            for skill in tab.get("Skills", []):
                key = (skill["Name"], cls, "Skill", league)
                usage_counter[key][0] += skill["Level"]
        
        # Count equipped items
        for item in char.get("Equipped", []):
            quality_code = item.get("QualityCode")
            name = item.get("Title")
            if not name:
                continue
            
            if quality_code == "q_runeword":
                key = (name, "", "Runeword", league)
            elif quality_code == "q_set":
                key = (name, "", "Set", league)
            elif quality_code == "q_unique":
                key = (name, "", "Unique", league)
            else:
                continue
            
            is_synth = "Synthesized" in item.get("Tag", "")
            usage_counter[key][1 if is_synth else 0] += 1
        
        # Count mercenary items
        for item in char.get("MercenaryEquipped", []):
            quality_code = item.get("QualityCode")
            name = item.get("Title")
            if not name:
                continue
            
            if quality_code == "q_runeword":
                key = (name, "", "Mercenary Runeword", league)
            elif quality_code == "q_set":
                key = (name, "", "Mercenary Set", league)
            elif quality_code == "q_unique":
                key = (name, "", "Mercenary Unique", league)
            else:
                continue
            
            is_synth = "Synthesized" in item.get("Tag", "")
            usage_counter[key][1 if is_synth else 0] += 1
    
    # Update existing rows or create new ones
    for (name, cls, typ, lg), (normal, synth) in usage_counter.items():
        lookup_key = (typ, lg, cls, name)
        
        if lookup_key in row_lookup:
            # Update existing row
            row_idx = row_lookup[lookup_key]
            if synth:
                value = f"{normal}(+{synth})"
            else:
                value = str(normal)
            rows[row_idx][snapshot_label] = value
        else:
            # Create new row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = typ
            new_row['League'] = lg
            new_row['Class'] = cls
            new_row['Name'] = name
            if synth:
                value = f"{normal}(+{synth})"
            else:
                value = str(normal)
            new_row[snapshot_label] = value
            rows.append(new_row)
    
    # Save updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Updated {league.upper()} character data for {snapshot_label}")

def update_server_data_in_unified_csv(server_stats, game_servers, snapshot_label):
    """
    Update server metrics in unified CSV
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load existing CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Add new snapshot column if needed
    if snapshot_label not in fieldnames:
        fieldnames = list(fieldnames) + [snapshot_label]
        for row in rows:
            row[snapshot_label] = '0'
    
    # Create lookup
    row_lookup = {}
    for i, row in enumerate(rows):
        key = (row['Type'], row['League'], row['Class'], row['Name'])
        row_lookup[key] = i
    
    # Update global server stats
    server_mapping = {
        'online_now': 'Online_Now',
        'online_last_hour': 'Online_Last_Hour',
        'online_last_day': 'Online_Last_Day', 
        'online_last_week': 'Online_Last_Week',
        'online_last_fornight': 'Online_Last_Fortnight',
        'online_in_any_games': 'Online_In_Games',
        'games_open': 'Games_Open'
    }
    
    for api_key, csv_name in server_mapping.items():
        if api_key in server_stats:
            key = ('Server', 'ALL', '', csv_name)
            # Clean the value (remove quotes)
            value = str(server_stats[api_key]).strip('"')
            
            if key in row_lookup:
                rows[row_lookup[key]][snapshot_label] = value
            else:
                # Create new server metric row
                new_row = {col: '0' for col in fieldnames}
                new_row['Type'] = 'Server'
                new_row['League'] = 'ALL'
                new_row['Class'] = ''
                new_row['Name'] = csv_name
                new_row[snapshot_label] = value
                rows.append(new_row)
                print(f"📝 Created new server metric: {csv_name}")
    
    # Update individual game server stats
    for server in game_servers:
        country = server.get('country', 'Unknown').strip('"')
        location = server.get('location', 'Unknown').strip('"')
        
        # Extract city name from location (before comma)
        city = location.split(',')[0].strip() if ',' in location else location
        city = city.replace(' ', '_').replace('\t', '').replace('&#9899;', '')  # Clean up
        
        # Update players on this server
        players_key = ('GameServer', 'ALL', country, f'{city}_Players')
        players_value = str(server.get('players', 0))
        
        if players_key in row_lookup:
            rows[row_lookup[players_key]][snapshot_label] = players_value
        else:
            # Create new game server row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = 'GameServer'
            new_row['League'] = 'ALL'
            new_row['Class'] = country
            new_row['Name'] = f'{city}_Players'
            new_row[snapshot_label] = players_value
            rows.append(new_row)
            print(f"📝 Created new game server metric: {country} {city}_Players")
        
        # Update games on this server
        games_key = ('GameServer', 'ALL', country, f'{city}_Games')
        games_value = str(server.get('games', 0))
        
        if games_key in row_lookup:
            rows[row_lookup[games_key]][snapshot_label] = games_value
        else:
            # Create new game server row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = 'GameServer'
            new_row['League'] = 'ALL'
            new_row['Class'] = country
            new_row['Name'] = f'{city}_Games'
            new_row[snapshot_label] = games_value
            rows.append(new_row)
            print(f"📝 Created new game server metric: {country} {city}_Games")
    
    # Save updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Updated server data for {snapshot_label}")

def generate_web_pages():
    """
    Generate HTML pages from unified CSV data (similar to original sc/hc web generation)
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load CSV data
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    
    # Get time columns (exclude Type, League, Class, Name)
    time_columns = [h for h in headers if h not in ['Type', 'League', 'Class', 'Name']]
    
    # Organize data by league and type
    data_by_league = {
        'SC': {'Skills': {}, 'Uniques': [], 'Sets': [], 'Runewords': [], 'Mercenary Uniques': [], 'Mercenary Sets': [], 'Mercenary Runewords': []},
        'HC': {'Skills': {}, 'Uniques': [], 'Sets': [], 'Runewords': [], 'Mercenary Uniques': [], 'Mercenary Sets': [], 'Mercenary Runewords': []},
        'ALL': {'Server': [], 'GameServer': []}
    }
    
    for row in rows:
        league = row['League']
        data_type = row['Type']
        char_class = row.get('Class', '').strip()
        name = row['Name']
        
        # Get usage data for all time periods
        usage_data = {col: row[col] for col in time_columns}
        
        if league in ['SC', 'HC']:
            if data_type == 'Skill':
                if char_class not in data_by_league[league]['Skills']:
                    data_by_league[league]['Skills'][char_class] = []
                data_by_league[league]['Skills'][char_class].append((name, usage_data))
            elif data_type in ['Unique', 'Set', 'Runeword', 'Mercenary Unique', 'Mercenary Set', 'Mercenary Runeword']:
                data_by_league[league][data_type + 's' if not data_type.endswith('s') else data_type].append((name, usage_data))
        elif league == 'ALL':
            data_by_league['ALL'][data_type].append((name, usage_data))
    
    # Generate HTML for SC and HC
    for league in ['SC', 'HC']:
        generate_league_html(league, data_by_league[league], time_columns)
    
    # Generate HTML for server data
    generate_server_html(data_by_league['ALL'], time_columns)
    
    print("✅ Generated web pages:")
    print("   📄 sc-usage-over-time.html")
    print("   📄 hc-usage-over-time.html") 
    print("   📄 server-stats-over-time.html")

def generate_league_html(league, league_data, time_columns):
    """Generate HTML page for a specific league (SC or HC)"""
    
    filename = f"{league.lower()}-usage-over-time.html"
    title = f"{league} - Usage Over Time"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; cursor: pointer; }}
        th:hover {{ background-color: #e2e2e2; }}
        .usage-label {{ cursor: pointer; color: #0066cc; }}
        .usage-label:hover {{ background-color: #f0f8ff; }}
        #tooltipChart {{
            position: absolute;
            display: none;
            border: 1px solid #aaa;
            background-color: #fff;
            z-index: 9999;
            padding: 6px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        }}
        .league-header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .section-header {{
            background-color: #f8f9fa;
            padding: 10px;
            border-left: 4px solid #007bff;
            margin: 20px 0 10px 0;
        }}
    </style>
</head>
<body>
    <canvas id="tooltipChart" width="300" height="150"></canvas>
    
    <div class="league-header">
        <h1>🎮 Path of Diablo - {title}</h1>
        <p>Interactive skill and item usage analytics</p>
        <p><em>Hover over items to see usage trends • Click columns to sort</em></p>
    </div>
""")

        # Skills grouped by class
        f.write('<div class="section-header"><h2>⚔️ Skills by Class</h2></div>\n')
        for char_class, skills in league_data['Skills'].items():
            f.write(f'<h3>🏛️ {char_class}</h3>\n')
            f.write('<table>\n')
            f.write('<tr><th onclick="sortTable(this, \'str\')">Skill Name</th>')
            for col in time_columns:
                f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
            f.write('</tr>\n')
            
            for name, usage_data in skills:
                usage_json = json.dumps(usage_data)
                f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{name}</td>')
                for col in time_columns:
                    f.write(f'<td>{usage_data.get(col, "0")}</td>')
                f.write('</tr>\n')
            f.write('</table>\n')
        
        # Items by category
        item_categories = [
            ('Uniques', '💎'),
            ('Sets', '📦'), 
            ('Runewords', '🔮'),
            ('Mercenary Uniques', '⚔️💎'),
            ('Mercenary Sets', '⚔️📦'),
            ('Mercenary Runewords', '⚔️🔮')
        ]
        
        for category, emoji in item_categories:
            if league_data[category]:
                f.write(f'<div class="section-header"><h2>{emoji} {category}</h2></div>\n')
                f.write('<table>\n')
                f.write('<tr><th onclick="sortTable(this, \'str\')">Item Name</th>')
                for col in time_columns:
                    f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
                f.write('</tr>\n')
                
                for name, usage_data in league_data[category]:
                    usage_json = json.dumps(usage_data)
                    f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{name}</td>')
                    for col in time_columns:
                        f.write(f'<td>{usage_data.get(col, "0")}</td>')
                    f.write('</tr>\n')
                f.write('</table>\n')
        
        # Add JavaScript for interactivity
        f.write("""
<script>
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('tooltipChart');
    const ctx = canvas.getContext('2d');
    let chart;

    // Hover charts for usage trends
    document.querySelectorAll('.usage-label').forEach(label => {
        label.addEventListener('mouseenter', e => {
            const data = JSON.parse(label.dataset.usage);
            const labels = Object.keys(data);
            const values = Object.values(data).map(v => {
                // Handle values like "123(+5)" for synthesized items
                const match = v.match(/^(\\d+)/);
                return match ? parseInt(match[1]) : 0;
            });

            canvas.style.display = 'block';
            canvas.style.left = e.pageX + 10 + 'px';
            canvas.style.top = e.pageY - 80 + 'px';

            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label.textContent + ' Usage',
                        data: values,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: false,
                    animation: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: label.textContent + ' - Usage Trend',
                            font: { size: 12, weight: 'bold' }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true },
                        x: { ticks: { maxRotation: 45, minRotation: 45 } }
                    }
                }
            });
        });

        label.addEventListener('mouseleave', () => {
            canvas.style.display = 'none';
        });
    });

    // Table sorting functionality
    window.sortTable = function(header, type) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody') || table;
        const rows = Array.from(tbody.querySelectorAll('tr')).slice(1); // Skip header
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        
        rows.sort((a, b) => {
            const aVal = a.children[columnIndex].textContent.trim();
            const bVal = b.children[columnIndex].textContent.trim();
            
            if (type === 'num') {
                const aNum = parseInt(aVal.match(/^(\\d+)/) ? aVal.match(/^(\\d+)/)[1] : '0');
                const bNum = parseInt(bVal.match(/^(\\d+)/) ? bVal.match(/^(\\d+)/)[1] : '0');
                return bNum - aNum; // Descending
            } else {
                return aVal.localeCompare(bVal); // Ascending
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    };
});
</script>
</body>
</html>""")

def generate_server_html(server_data, time_columns):
    """Generate HTML page for server statistics"""
    
    filename = "server-stats-over-time.html"
    title = "Server Statistics Over Time"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; cursor: pointer; }}
        th:hover {{ background-color: #e2e2e2; }}
        .usage-label {{ cursor: pointer; color: #0066cc; }}
        .usage-label:hover {{ background-color: #f0f8ff; }}
        #tooltipChart {{
            position: absolute;
            display: none;
            border: 1px solid #aaa;
            background-color: #fff;
            z-index: 9999;
            padding: 6px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        }}
        .server-header {{ 
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .section-header {{
            background-color: #f8f9fa;
            padding: 10px;
            border-left: 4px solid #28a745;
            margin: 20px 0 10px 0;
        }}
    </style>
</head>
<body>
    <canvas id="tooltipChart" width="300" height="150"></canvas>
    
    <div class="server-header">
        <h1>🖥️ Path of Diablo - Server Analytics</h1>
        <p>Real-time server population and infrastructure monitoring</p>
        <p><em>Hover over metrics to see trends • Click columns to sort</em></p>
    </div>
""")

        # Global server stats
        if server_data['Server']:
            f.write('<div class="section-header"><h2>🌐 Global Server Statistics</h2></div>\n')
            f.write('<table>\n')
            f.write('<tr><th onclick="sortTable(this, \'str\')">Metric</th>')
            for col in time_columns:
                f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
            f.write('</tr>\n')
            
            for name, usage_data in server_data['Server']:
                usage_json = json.dumps(usage_data)
                display_name = name.replace('_', ' ').title()
                f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{display_name}</td>')
                for col in time_columns:
                    f.write(f'<td>{usage_data.get(col, "0")}</td>')
                f.write('</tr>\n')
            f.write('</table>\n')
        
        # Game server stats grouped by region
        if server_data['GameServer']:
            f.write('<div class="section-header"><h2>🗺️ Game Servers by Region</h2></div>\n')
            
            # Group by country
            servers_by_country = {}
            for name, usage_data in server_data['GameServer']:
                # Extract country from the data structure
                # GameServer rows have country in the 'Class' field when we organized the data
                country = 'Unknown'
                for row in server_data['GameServer']:
                    if row[0] == name:  # Find matching row
                        break
                
                # Get country from original CSV data by looking at the first part of name
                if '_Players' in name or '_Games' in name:
                    city = name.replace('_Players', '').replace('_Games', '')
                    # We need to find the country - let's group by the first part for now
                    country = 'Various'  # We'll improve this
                
                if country not in servers_by_country:
                    servers_by_country[country] = []
                servers_by_country[country].append((name, usage_data))
            
            # Generate tables for each country
            for country, server_list in servers_by_country.items():
                f.write(f'<h3>🌍 {country} Servers</h3>\n')
                f.write('<table>\n')
                f.write('<tr><th onclick="sortTable(this, \'str\')">Server Metric</th>')
                for col in time_columns:
                    f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
                f.write('</tr>\n')
                
                for name, usage_data in server_list:
                    usage_json = json.dumps(usage_data)
                    display_name = name.replace('_', ' ').title()
                    f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{display_name}</td>')
                    for col in time_columns:
                        f.write(f'<td>{usage_data.get(col, "0")}</td>')
                    f.write('</tr>\n')
                f.write('</table>\n')
        
        # Add the same JavaScript as the league pages
        f.write("""
<script>
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('tooltipChart');
    const ctx = canvas.getContext('2d');
    let chart;

    document.querySelectorAll('.usage-label').forEach(label => {
        label.addEventListener('mouseenter', e => {
            const data = JSON.parse(label.dataset.usage);
            const labels = Object.keys(data);
            const values = Object.values(data).map(v => parseInt(v) || 0);

            canvas.style.display = 'block';
            canvas.style.left = e.pageX + 10 + 'px';
            canvas.style.top = e.pageY - 80 + 'px';

            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label.textContent + ' Trend',
                        data: values,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: false,
                    animation: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: label.textContent + ' - Server Trend',
                            font: { size: 12, weight: 'bold' }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true },
                        x: { ticks: { maxRotation: 45, minRotation: 45 } }
                    }
                }
            });
        });

        label.addEventListener('mouseleave', () => {
            canvas.style.display = 'none';
        });
    });

    window.sortTable = function(header, type) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody') || table;
        const rows = Array.from(tbody.querySelectorAll('tr')).slice(1);
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        
        rows.sort((a, b) => {
            const aVal = a.children[columnIndex].textContent.trim();
            const bVal = b.children[columnIndex].textContent.trim();
            
            if (type === 'num') {
                return parseInt(bVal) - parseInt(aVal); // Descending
            } else {
                return aVal.localeCompare(bVal); // Ascending
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    };
});
</script>
</body>
</html>""")

def full_data_update(snapshot_label=None):
    """
    Complete data update: fetch all API data and update CSV
    """
    if not snapshot_label:
        # Generate smart label based on season progress (matching github-update-csv-web.py)
        snapshot_label = generate_snapshot_label()
    
    print(f"🚀 Starting full data update for {snapshot_label}")
    print("=" * 60)
    
    # Fetch server data
    print("📡 Fetching server statistics...")
    server_stats = fetch_server_stats()
    if server_stats:
        print(f"   Online now: {server_stats.get('online_now', 'N/A')}")
        print(f"   Games open: {server_stats.get('games_open', 'N/A')}")
    
    print("🖥️  Fetching game server data...")
    game_servers = fetch_game_servers()
    if game_servers:
        print(f"   Found {len(game_servers)} game servers")
        for server in game_servers:
            country = server.get('country', 'Unknown').strip('"')
            players = server.get('players', 0)
            games = server.get('games', 0)
            print(f"   {country}: {players} players, {games} games")
    
    # Fetch character data
    print("👥 Fetching character data...")
    sc_characters = fetch_character_data('sc')
    if sc_characters:
        print(f"   SC: {len(sc_characters)} characters")
    
    hc_characters = fetch_character_data('hc')
    if hc_characters:
        print(f"   HC: {len(hc_characters)} characters")
    
    # Update CSV
    print("💾 Updating unified CSV...")
    
    if sc_characters:
        update_unified_csv_from_character_data(sc_characters, 'SC', snapshot_label)
    
    if hc_characters:
        update_unified_csv_from_character_data(hc_characters, 'HC', snapshot_label)
    
    if server_stats or game_servers:
        update_server_data_in_unified_csv(server_stats or {}, game_servers or [], snapshot_label)
    
    # Generate web pages
    print("🌐 Generating web pages...")
    generate_web_pages()
    
    print("=" * 60)
    print(f"🎉 Data update complete for {snapshot_label}!")
    
    # Show summary
    if server_stats:
        print(f"📊 Current server status:")
        print(f"   Players online: {server_stats.get('online_now', 'N/A')}")
        print(f"   Games open: {server_stats.get('games_open', 'N/A')}")
        print(f"   Last day activity: {server_stats.get('online_last_day', 'N/A')}")

def monitor_servers(interval_minutes=60, max_updates=24):
    """
    Continuously monitor server stats at regular intervals
    
    interval_minutes: How often to check (default: every hour)
    max_updates: Maximum number of updates before stopping (default: 24 hours)
    """
    print(f"🔄 Starting server monitoring (every {interval_minutes} minutes)")
    print(f"📅 Will run for {max_updates} updates")
    print("Press Ctrl+C to stop")
    
    for i in range(max_updates):
        try:
            # Use meaningful monitoring labels instead of timestamps
            current_time = datetime.now()
            if interval_minutes >= 60:
                # For hourly or longer intervals, use hour-based labels
                timestamp = f"Monitor_Hour_{current_time.hour:02d}"
            else:
                # For shorter intervals, use hour:minute format
                timestamp = f"Monitor_{current_time.hour:02d}_{current_time.minute:02d}"
            
            print(f"\n⏰ Update {i+1}/{max_updates} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Only update server data for monitoring (not character data)
            server_stats = fetch_server_stats()
            game_servers = fetch_game_servers()
            
            if server_stats or game_servers:
                update_server_data_in_unified_csv(server_stats or {}, game_servers or [], timestamp)
            
            if i < max_updates - 1:  # Don't sleep after the last update
                print(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            print("Continuing...")

def suggest_snapshot_labels():
    """
    Suggest snapshot labels based on current season progress and show auto-generated label
    """
    # Show what the auto-generated label would be
    auto_label = generate_snapshot_label()
    season_number, start_time, season_status = get_current_season_info()
    
    print("🤖 AUTO-GENERATED LABEL:")
    print(f"   {auto_label}")
    
    if season_number and start_time:
        now = datetime.now(timezone.utc)
        delta_days = (now - start_time).days
        print(f"   (Season {season_number}, Day {delta_days + 1}, Status: {season_status})")
    
    print()
    print("💡 MANUAL LABEL OPTIONS:")
    
    current_month = datetime.now().strftime("%B")
    
    if season_number:
        if season_status == "post_season":
            suggestions = [
                f"Post Season {season_number}",
                f"S{season_number + 1} Pre-Season",
                current_month,
                "Off Season",
            ]
        else:
            suggestions = [
                f"S{season_number} {current_month}",  # e.g., "S14 October"
                f"S{season_number} Mid Season",
                f"S{season_number} End of Season", 
                f"Post Season {season_number}",
                current_month,  # e.g., "October"
                "Mid Season",
                "End of Season",
            ]
            
            # Add day/week suggestions based on current progress
            if start_time and delta_days < 14:
                suggestions.insert(1, f"S{season_number} Day {delta_days + 1}")
            elif start_time and delta_days < 49:
                week_number = ((delta_days - 14) // 7) + 2
                suggestions.insert(1, f"S{season_number} Week {week_number}")
    else:
        suggestions = [
            current_month,
            "Mid Season",
            "End of Season",
            "Week 1",
            "Day 30",
        ]
    
    for i, label in enumerate(suggestions, 1):
        print(f"   {i}. {label}")
    
    print()
    print("📅 Usage: python3 api_integration.py \"<label>\"")
    print("📅 Default: python3 api_integration.py (uses auto-generated label)")
    
    return suggestions

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "monitor":
            # Usage: python api_integration.py monitor [interval_minutes] [max_updates]
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            max_updates = int(sys.argv[3]) if len(sys.argv) > 3 else 24
            monitor_servers(interval, max_updates)
        elif sys.argv[1] == "test":
            # Just test the API endpoints
            print("🧪 Testing API endpoints...")
            stats = fetch_server_stats()
            servers = fetch_game_servers()
            print(f"Stats API: {'✅' if stats else '❌'}")
            print(f"Servers API: {'✅' if servers else '❌'}")
            if stats:
                print(f"Current players: {stats.get('online_now')}")
            if servers:
                print(f"Active servers: {len(servers)}")
        elif sys.argv[1] == "suggest":
            # Show suggested snapshot labels
            suggest_snapshot_labels()
        elif sys.argv[1] == "web":
            # Generate web pages only (without updating data)
            print("🌐 Generating web pages from current CSV data...")
            generate_web_pages()
        else:
            # Custom snapshot label
            full_data_update(sys.argv[1])
    else:
        # Default: full update with current month
        full_data_update()