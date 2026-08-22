import json

SOURCE_FILE = "sc_ladder.json"
OUTPUT_FILE = "jsons/Amazon.json"
CLASS_NAME = "Amazon"

with open(SOURCE_FILE) as f:
    ladder_data = json.load(f)

amazon_characters = [char for char in ladder_data if char.get("Class") == CLASS_NAME]

with open(OUTPUT_FILE, "w") as f:
    json.dump(amazon_characters, f, indent=2)

print(f"Wrote {len(amazon_characters)} {CLASS_NAME} characters to {OUTPUT_FILE}")
