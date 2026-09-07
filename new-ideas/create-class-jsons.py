import json
import os
import requests


classes = [
    "Amazon",
    "Assassin",
    "Barbarian",
    "Druid",
    "Necromancer",
    "Paladin",
    "Sorceress"
]

modes = {
    "sc": "../sc_ladder.json",
    "hc": "../hc_ladder.json"
}

SEASON = 13

CLASS_NAME_MAP = {
    "ama": "Amazon",
    "asn": "Assassin",
    "bar": "Barbarian",
    "dru": "Druid",
    "nec": "Necromancer",
    "pal": "Paladin",
    "sor": "Sorceress"
}


for mode, source_file in modes.items():

    output_dir = "jsons"
    os.makedirs(output_dir, exist_ok=True)

    game_mode = 1 if mode == "hc" else 0

    # ---------------------------------------------------------
    # Existing class JSON generation
    # ---------------------------------------------------------

    with open(source_file) as f:
        ladder_data = json.load(f)

    for class_name in classes:

        characters = [
            char
            for char in ladder_data
            if char.get("Class") == class_name
            and char.get("Stats", {}).get("Level", 0) > 60
        ]

        output_file = f"{output_dir}/{mode}{class_name.lower()}.json"

        with open(output_file, "w") as f:
            json.dump(characters, f, indent=2)

        print(
            f"Wrote {len(characters)} "
            f"{class_name} {mode.upper()} characters "
            f"to {output_file}"
        )

    # ---------------------------------------------------------
    # Ladder summary
    # ---------------------------------------------------------

    ladder_url = (
        f"https://beta.pathofdiablo.com/api/ladder/"
        f"{SEASON}/{game_mode}/0/"
    )

    firsts_url = (
        "https://beta.pathofdiablo.com/api/ladder-firsts"
    )

    try:

        print(
            f"Fetching {mode.upper()} ladder summary..."
        )

        ladder_response = requests.get(ladder_url)
        ladder_response.raise_for_status()

        firsts_response = requests.get(firsts_url)
        firsts_response.raise_for_status()

        ladder_json = ladder_response.json()
        firsts_data = firsts_response.json()

        ladder = ladder_json.get("ladder", [])

        # -----------------------------------------------------
        # Top 10
        # -----------------------------------------------------

        top10 = []

        for entry in ladder[:10]:

            top10.append({
                "name": entry.get("charName", "Unknown"),
                "level": entry.get("level", 0),
                "className": (
                    CLASS_NAME_MAP.get(
                        entry.get("charClass")
                    )
                    or entry.get("charClass", "Unknown")
                ),
                "rank": entry.get("rank", 0),
                "maxLevelDate": entry.get("maxLevelDate")
            })

        # -----------------------------------------------------
        # Ladder firsts
        # -----------------------------------------------------

        firsts = [
            entry
            for entry in firsts_data
            if entry.get("season") == SEASON
            and entry.get("gameMode") == game_mode
        ]

        # Group multiple firsts for the same character
        grouped_firsts = {}

        for entry in firsts:

            key = (
                entry.get("charName"),
                entry.get("charLevel"),
                entry.get("charClass")
            )

            if key not in grouped_firsts:
                grouped_firsts[key] = {
                    "name": entry.get(
                        "charName",
                        "Unknown"
                    ),
                    "level": entry.get(
                        "charLevel",
                        0
                    ),
                    "className": entry.get(
                        "charClass",
                        "Unknown"
                    ),
                    "kills": []
                }

            difficulty = entry.get(
                "difficulty",
                "Unknown"
            )

            boss = entry.get(
                "bossName",
                "Unknown"
            )

            if difficulty == "Hell":
                kill_description = (
                    f"First {boss} Kill"
                )
            else:
                kill_description = (
                    f"First {difficulty} {boss} Kill"
                )

            grouped_firsts[key]["kills"].append(
                kill_description
            )

        # -----------------------------------------------------
        # Convert grouped firsts to a list
        # -----------------------------------------------------

        ladder_firsts = list(
            grouped_firsts.values()
        )

        # -----------------------------------------------------
        # Write summary JSON
        # -----------------------------------------------------

        summary = {
            "season": SEASON,
            "mode": mode,
            "top10": top10,
            "ladderFirsts": ladder_firsts
        }

        output_file = (
            f"{output_dir}/{mode}_ladder_summary.json"
        )

        with open(output_file, "w") as f:
            json.dump(
                summary,
                f,
                indent=2
            )

        print(
            f"Wrote ladder summary to {output_file}"
        )

    except requests.RequestException as error:

        print(
            f"ERROR fetching {mode.upper()} "
            f"ladder summary: {error}"
        )