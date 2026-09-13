import json


def extract_mercenary_data(input_file, output_file):
    print(f"Reading {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        characters = json.load(f)

    output = []

    for character in characters:
        if not isinstance(character, dict):
            continue

        mercenary_type = character.get("MercenaryType")
        if not mercenary_type:
            continue

        merc_equipped = (
            character.get("MercenaryEquipped")
            or character.get("mercenary_equipped")
            or character.get("mercenary")
            or []
        )

        # Normalize to a list of {Worn, ...item} entries
        equipped_list = []
        if isinstance(merc_equipped, dict):
            for worn, item in merc_equipped.items():
                if not isinstance(item, dict):
                    continue
                entry = dict(item)
                entry.setdefault("Worn", worn)
                equipped_list.append(entry)
        elif isinstance(merc_equipped, list):
            for i, item in enumerate(merc_equipped):
                if not isinstance(item, dict):
                    continue
                entry = dict(item)
                entry.setdefault("Worn", f"slot_{i}")
                equipped_list.append(entry)

        # Keep only the fields the mercenary analysis needs
        trimmed_equipped = []
        for item in equipped_list:
            trimmed_sockets = [
                {
                    "Title": socket.get("Title"),
                    "QualityCode": socket.get("QualityCode"),
                    "PropertyList": socket.get("PropertyList", [])
                }
                for socket in item.get("Sockets", [])
            ]

            trimmed_equipped.append({
                "Worn": item.get("Worn"),
                "Title": item.get("Title"),
                "Tag": item.get("Tag"),
                "TextTag": item.get("TextTag"),
                "QualityCode": item.get("QualityCode"),
                "SocketCount": item.get("SocketCount"),
                "Sockets": trimmed_sockets
            })

        output.append({
            "Name": character.get("Name"),
            "Class": character.get("Class"),
            "Stats": {"Level": character.get("Stats", {}).get("Level")},
            "MercenaryType": mercenary_type,
            "MercenaryName": character.get("MercenaryName"),
            "MercenaryLevel": character.get("MercenaryLevel"),
            "MercenaryEquipped": trimmed_equipped
        })

    print(f"Writing {output_file}...")
    print(f"Characters: {len(characters):,}")
    print(f"Characters with mercenaries: {len(output):,}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    print("Done.\n")


if __name__ == "__main__":
    extract_mercenary_data(
        "jsons/sc_ladder.json",
        "jsons/sc-mercs.json"
    )

    extract_mercenary_data(
        "jsons/hc_ladder.json",
        "jsons/hc-mercs.json"
    )
