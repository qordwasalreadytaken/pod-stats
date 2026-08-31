import json

import json
import os

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

for mode, source_file in modes.items():

#    output_dir = f"jsons/{mode}"
    output_dir = f"jsons"
    os.makedirs(output_dir, exist_ok=True)

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