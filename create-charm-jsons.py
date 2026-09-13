import json


def extract_charm_data(input_file, output_file):
    print(f"Reading {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        characters = json.load(f)

    output = []

    for character in characters:
        name = character.get("Name")
        char_class = character.get("Class")
        level = character.get("Stats", {}).get("Level")

        inventory = character.get("Inventory", [])

        # Keep only items in the bottom four inventory rows
        active_inventory = [
            item
            for item in inventory
            if 5 <= item.get("Position", {}).get("y", -1) <= 8
        ]

        for item in active_inventory:
            output.append({
                "Name": name,
                "Class": char_class,
                "Level": level,
                "CharmName": item.get("Title"),
                "Tag": item.get("Tag"),
                "QualityCode": item.get("QualityCode"),
                "PropertyList": item.get("PropertyList", []),
                "Position": item.get("Position", {})
            })

    print(f"Writing {output_file}...")
    print(f"Characters: {len(characters):,}")
    print(f"Charm records: {len(output):,}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    print("Done.\n")


if __name__ == "__main__":
    extract_charm_data(
        "jsons/sc_ladder.json",
        "jsons/sc-charms.json"
    )

    extract_charm_data(
        "jsons/hc_ladder.json",
        "jsons/hc-charms.json"
    )