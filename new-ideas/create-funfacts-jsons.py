"""
Prebuild data for new-funfacts.html.

Extracts trimmed per-character stat/equipment data from the local ladder
JSON (for client-side stat/undead/CBF/build analysis), and fetches the
live top-1000 ladder + per-class ladder leaders from the API (for the
account-domination and class-ladder-leader sections, which need fresh
ranked data that isn't present in the bulk ladder scrape).
"""

import json
import requests

CLASS_CODE_MAP = {
    "ama": "Amazon",
    "asn": "Assassin",
    "bar": "Barbarian",
    "dru": "Druid",
    "nec": "Necromancer",
    "pal": "Paladin",
    "sor": "Sorceress"
}

CLASS_ID_MAP = {
    1: "Amazon",
    7: "Assassin",
    5: "Barbarian",
    6: "Druid",
    3: "Necromancer",
    4: "Paladin",
    2: "Sorceress"
}


def get_current_season():
    try:
        response = requests.get("https://beta.pathofdiablo.com/api/ladder-summaries", timeout=10)
        response.raise_for_status()
        seasons = response.json()
        return next((s["season"] for s in seasons if s.get("current")), None)
    except requests.RequestException as e:
        print(f"⚠️ Error fetching season: {e}")
        return None


def extract_funfacts_data(input_file, output_file):

    print(f"Reading {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        characters = json.load(f)

    output = []

    for character in characters:
        if not isinstance(character, dict):
            continue

        stats = character.get("Stats", {}) or {}
        bonus = character.get("Bonus", {}) or {}

        equipped = []
        for item in character.get("Equipped", []) or []:
            equipped.append({
                "Title": item.get("Title"),
                "PropertyList": item.get("PropertyList", []),
                "Sockets": [
                    {
                        "Title": socket.get("Title"),
                        "PropertyList": socket.get("PropertyList", [])
                    }
                    for socket in item.get("Sockets", []) or []
                ]
            })

        skill_tabs = []
        for tab in character.get("SkillTabs", []) or []:
            skills = [
                {"Name": skill.get("Name"), "Level": skill.get("Level")}
                for skill in tab.get("Skills", []) or []
            ]
            if skills:
                skill_tabs.append({"Skills": skills})

        output.append({
            "Name": character.get("Name"),
            "Class": character.get("Class"),
            "IsDead": character.get("IsDead"),
            "Stats": {
                "Level": stats.get("Level"),
                "Strength": stats.get("Strength"),
                "Dexterity": stats.get("Dexterity"),
                "Vitality": stats.get("Vitality"),
                "Energy": stats.get("Energy"),
                "Life": stats.get("Life"),
                "Mana": stats.get("Mana")
            },
            "Bonus": {
                "MagicFind": bonus.get("MagicFind"),
                "GoldFind": bonus.get("GoldFind")
            },
            "Equipped": equipped,
            "SkillTabs": skill_tabs
        })

    print(f"Writing {output_file}...")
    print(f"Characters: {len(output):,}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    print("Done.\n")


def fetch_top1k(is_hardcore, season):

    game_mode = 1 if is_hardcore else 0
    season = season or 13
    base_url = f"https://beta.pathofdiablo.com/api/ladder/{season}/{game_mode}/0/"

    entries = []

    for page in range(1, 6):
        url = f"{base_url}{page}"
        print(f"Fetching {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                for char in response.json().get("ladder", []):
                    entries.append({
                        "rank": char.get("rank"),
                        "name": char.get("charName") or char.get("name"),
                        "account": char.get("account"),
                        "charClass": char.get("charClass"),
                        "class": CLASS_CODE_MAP.get(char.get("charClass"), char.get("charClass")),
                        "level": char.get("level"),
                        "exp": char.get("exp")
                    })
            else:
                print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
        except requests.RequestException as e:
            print(f"⚠️ Error fetching page {page}: {e}")

    return entries


def fetch_class_leaders(is_hardcore, season, top_n=5):

    game_mode = 1 if is_hardcore else 0
    season = season or 13

    leaders = {}

    for class_id, class_name in CLASS_ID_MAP.items():
        url = f"https://beta.pathofdiablo.com/api/ladder/{season}/{game_mode}/{class_id}/0"
        print(f"Fetching {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                chars = response.json().get("ladder", [])[:top_n]
                leaders[class_name] = [
                    {
                        "rank": char.get("rank"),
                        "name": char.get("charName") or char.get("name"),
                        "level": char.get("level"),
                        "account": char.get("account"),
                        "exp": char.get("exp")
                    }
                    for char in chars
                ]
            else:
                print(f"⚠️ Failed to fetch {class_name} ladder: {response.status_code}")
                leaders[class_name] = []
        except requests.RequestException as e:
            print(f"⚠️ Error fetching {class_name} ladder: {e}")
            leaders[class_name] = []

    return leaders


if __name__ == "__main__":

    extract_funfacts_data("jsons/sc_ladder.json", "jsons/sc-funfacts.json")
    extract_funfacts_data("jsons/hc_ladder.json", "jsons/hc-funfacts.json")

    season = get_current_season()

    for is_hardcore, prefix in [(False, "sc"), (True, "hc")]:

        top1k = fetch_top1k(is_hardcore, season)
        with open(f"jsons/{prefix}-top1k.json", "w", encoding="utf-8") as f:
            json.dump(top1k, f, separators=(",", ":"))
        print(f"✓ Wrote jsons/{prefix}-top1k.json ({len(top1k):,} characters)\n")

        leaders = fetch_class_leaders(is_hardcore, season)
        with open(f"jsons/{prefix}-classleaders.json", "w", encoding="utf-8") as f:
            json.dump(leaders, f, separators=(",", ":"))
        print(f"✓ Wrote jsons/{prefix}-classleaders.json\n")
