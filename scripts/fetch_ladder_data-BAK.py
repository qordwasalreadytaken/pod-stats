import requests
import json
import os
import time
from collections import Counter
import matplotlib.pyplot as plt
from datetime import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

def count_classes(characters):
    """Count the class distribution for the top 1,000 characters."""
    return Counter(char.get("charClass", "Unknown") for char in characters)

def generate_pie_chart(class_counts):
    """Generate a pie chart for class distribution of the top 1,000 characters."""
    classes = list(class_counts.keys())
    counts = list(class_counts.values())

    if not counts:
        print("⚠️ No characters found for pie chart.")
        return

    try:
        armory = FontProperties(fname='../armory/font/avqest.ttf')  # Update path for scripts dir
    except:
        armory = None  # Fallback if font not available

    # Class color mapping
    class_color_map = {
        "ama": "rgb(255, 102, 105)",      # Amazon - Red
        "asn": "rgb(255, 255, 255)",      # Assassin - White
        "bar": "rgb(150, 105, 32)",       # Barbarian - Brown
        "dru": "rgb(255, 186, 74)",       # Druid - Orange
        "nec": "rgb(179, 255, 253)",      # Necromancer - Cyan
        "pal": "rgb(255, 243, 112)",      # Paladin - Yellow
        "sor": "rgb(188, 107, 255)"       # Sorceress - Lavender
    }
    
    # Convert RGB strings to matplotlib format and map to classes in order
    def rgb_to_matplotlib(rgb_string):
        # Extract numbers from "rgb(r, g, b)" format
        rgb_values = rgb_string.replace("rgb(", "").replace(")", "").split(",")
        return tuple(int(v.strip()) / 255.0 for v in rgb_values)
    
    colors = [rgb_to_matplotlib(class_color_map.get(class_code, "rgb(128, 128, 128)")) for class_code in classes]

    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f'{pct:.1f}% ({val})'
        return my_autopct

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    plt.figure(figsize=(22, 22))
    plt.subplots_adjust(top=0.5, bottom=0.15)

    wedges, texts, autotexts = plt.pie(
        counts, labels=classes, autopct=make_autopct(counts), startangle=250,
        colors=colors, radius=1.4,
        textprops={'fontsize': 30, 'color': 'white', 'fontproperties': armory if armory else None}
    )

    title = plt.title(
        f"Class Distribution of Top 1,000 Characters\n\nAs of {timestamp}",
        pad=50, fontsize=45, fontproperties=armory if armory else None, loc='left', color="white"
    )
    title.set_fontsize(45)  # 🔹 Force title size after creation

    for text in texts:
        text.set_fontsize(35)  # Class labels
    for autotext in autotexts:
        autotext.set_fontsize(25)  # Percentages on slices
        autotext.set_color('black')

    plt.axis('equal')  # Ensures the pie chart is circular
    os.makedirs("../charts", exist_ok=True)  # Ensure charts directory exists
    plt.savefig("../charts/1kclass_distribution.png", dpi=300, bbox_inches='tight', transparent=True)
    plt.close()  # Avoid memory issues
    print("✅ Pie chart saved as 1kclass_distribution.png")

def fetch_ladder_characters(base_ladder_url, start_page=1, end_page=5):
    all_characters = []
    for page in range(start_page, end_page + 1):
        url = f"{base_ladder_url}{page}"
        print(f"Fetching {url}")
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            all_characters.extend(data.get("ladder", []))
        else:
            print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
    return all_characters

def fetch_1kladder_characters(base_ladder_url, pages):
    """Fetch all characters from multiple pages of the ladder."""
    all_characters = []
    for page in range(0, pages + 1):
        ladder_url = f"{base_ladder_url}{page}"
        print(f"Fetching {ladder_url}")
        response = requests.get(ladder_url)
        if response.status_code == 200:
            ladder_data = response.json()
            all_characters.extend(ladder_data.get("ladder", []))
        else:
            print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
    return all_characters

def strip_item_ids(char_data):
    """Remove the 'id' property from each item under Equipped/MercenaryEquipped."""
    for key in ("Equipped", "MercenaryEquipped"):
        items = char_data.get(key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item.pop("id", None)
        elif isinstance(items, dict):
            items.pop("id", None)
    return char_data

def fetch_char_summaries(characters):
    char_url = "https://beta.pathofdiablo.com/api/characters/{char_name}/summary"
    final_data = []
    for character in characters:
        char_name = character.get("charName", "unknown")
        char_id = character.get("id", None)

        if char_name == "unknown":
            char_name = f"unknown_{char_id or int(time.time() * 1000)}"

        response = requests.get(char_url.format(char_name=char_name))
        if response.status_code == 200:
            final_data.append(strip_item_ids(response.json()))
        else:
            print(f"⚠️ Failed to fetch character summary: {char_name}")
    return final_data


def generate_class_distribution_chart(characters, output_path):
    class_counts = Counter(char.get("class", "Unknown") for char in characters)
    labels = list(class_counts.keys())
    sizes = list(class_counts.values())

    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
    plt.title("Class Distribution")
    plt.axis("equal")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", transparent=True)
    plt.close()


def GetAllCharData():
    base_ladder_url = "https://beta.pathofdiablo.com/api/ladder/13/0/"  # Softcore
    char_url = "https://beta.pathofdiablo.com/api/characters/{char_name}/summary"

    # Step 1: Fetch top 1,000 characters (pages 0 to 5)
    all_characters = fetch_ladder_characters(f"{base_ladder_url}0/", start_page=0, end_page=5)
#    all_characters = fetch_ladder_characters(base_ladder_url, start_page=0, end_page=5)
#    all_characters = fetch_ladder_characters(base_ladder_url, start_page=1, end_page=5)
    top_1000_characters = {char["charName"]: char for char in all_characters}.values()

    # Step 2: Create pie chart from the top 1,000 characters
    class_counts = count_classes(top_1000_characters)
    generate_pie_chart(class_counts)

    # Step 3: Continue with class-specific characters
    classes = {
        "Amazon": "1/",
        "Assassin": "7/",
        "Barbarian": "5/",
        "Druid": "6/",
        "Necromancer": "3/",
        "Paladin": "4/",
        "Sorceress": "2/"
    }

    for class_name, api_suffix in classes.items():
        class_ladder_url = f"{base_ladder_url}{api_suffix}"
        class_characters = fetch_ladder_characters(class_ladder_url, 1)
        all_characters.extend(class_characters)  # Combine lists

    # Step 4: Remove duplicates by character name
    unique_characters = {char["charName"]: char for char in all_characters}.values()

#    class_counts = count_classes(unique_characters) # if we wanted a pie chart generated here, i think it's fine to keep in makehome
#    generate_pie_chart_all(class_counts)

    # Step 5: Fetch complete character data
    character_data = []
    for character in unique_characters:
        char_name = character.get("charName", "unknown")
        char_id = character.get("id", None)

        if char_name == "unknown":
            char_name = f"unknown_{char_id or int(time.time() * 1000)}"

        response = requests.get(char_url.format(char_name=char_name))
        if response.status_code == 200:
            character_data.append(response.json())
        else:
            print(f"⚠️ Failed to fetch character: {char_name}")

    # Step 6: Save the extended character list
    with open("sc_ladder.json", "w") as file:
        json.dump(character_data, file, indent=2)

    print(f"✅ Saved {len(character_data)} characters to sc_ladder.json (top 1,000 + class-specific)")


def GetAllHCCharData():
    base_ladder_url = "https://beta.pathofdiablo.com/api/ladder/13/1/"  # Softcore
    char_url = "https://beta.pathofdiablo.com/api/characters/{char_name}/summary"

    # Fetch top 1,000 characters
#    all_characters = fetch_ladder_characters(f"{base_ladder_url}0/", 5)
    all_characters = fetch_ladder_characters(base_ladder_url, start_page=0, end_page=5)

    # Fetch top 200 per class
    classes = {
        "Amazon": "1/",
        "Assassin": "7/",
        "Barbarian": "5/",
        "Druid": "6/",
        "Necromancer": "3/",
        "Paladin": "4/",
        "Sorceress": "2/"
    }

    for class_name, api_suffix in classes.items():
#        class_ladder_url = f"{base_ladder_url[:-2]}{api_suffix}"  # Adjusting URL for class-specific calls
        class_ladder_url = f"{base_ladder_url}{api_suffix}"  # Adjusting URL for class-specific calls
        class_characters = fetch_ladder_characters(class_ladder_url, 1)  # Only one page needed
        all_characters.extend(class_characters)

    # Remove duplicates (some characters appear in both top 1,000 and top 200 class rankings)
    unique_characters = {char["charName"]: char for char in all_characters}.values()

    character_data = []
    for character in unique_characters:
        char_name = character.get("charName", "unknown")
        char_id = character.get("id", None)

        if char_name == "unknown":
            char_name = f"unknown_{char_id or int(time.time() * 1000)}"

        response = requests.get(char_url.format(char_name=char_name))
        if response.status_code == 200:
            character_data.append(response.json())
        else:
            print(f"⚠️ Failed to fetch character: https://beta.pathofdiablo.com/api/characters/{char_name}/summary")

    # Save as one big JSON
    with open("hc_ladder.json", "w") as file:
        json.dump(character_data, file, indent=2)

    print(f"✅ Saved {len(character_data)} unique characters to hc_ladder.json")

def copy_ladders_to_dailies():
    """Copy sc_ladder.json and hc_ladder.json to dailies/ with a date-stamped filename."""
    today = datetime.now().strftime('%m-%d')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dailies_dir = os.path.abspath(os.path.join(script_dir, '..', 'dailies'))
    os.makedirs(dailies_dir, exist_ok=True)
    for base in ['sc_ladder.json', 'hc_ladder.json']:
        src = os.path.abspath(os.path.join(script_dir, '..', base))
        if os.path.exists(src):
            if base.startswith('sc_'):
                dst = os.path.join(dailies_dir, f"{today}-sc_ladder.json")
            elif base.startswith('hc_'):
                dst = os.path.join(dailies_dir, f"{today}-hc_ladder.json")
            else:
                continue
            import shutil
            shutil.copy2(src, dst)
            print(f"Copied {src} to {dst}")


def main():
    GetAllCharData()
    GetAllHCCharData()
#    copy_ladders_to_dailies()


if __name__ == "__main__":
    main()