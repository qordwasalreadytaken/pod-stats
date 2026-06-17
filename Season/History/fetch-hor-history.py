#!/usr/bin/env python3

import json
import requests
from pathlib import Path

MAX_SEASON = 13
PAGES = range(1, 6)  # 1-4 = top 1000

MODES = {
    0: "sc",
    1: "hc",
}

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "season_cache"


def fetch_season_ladder(season, mode):
    """
    Fetch the top 1000 ladder entries for a season/mode.
    Returns a list of ladder entries.
    """
    characters = []

    for page in PAGES:
        url = (
            f"https://beta.pathofdiablo.com/"
            f"api/ladder/{season}/{mode}/0/{page}"
        )

        print(f"Fetching {url}")

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(
                f"Season {season} mode {mode} "
                f"page {page} failed: HTTP {response.status_code}"
            )

        data = response.json()
        ladder = data.get("ladder", [])

        print(f"  Page {page}: {len(ladder)} entries")

        characters.extend(ladder)

    return characters


def save_cache(season, mode_name, characters):
    CACHE_DIR.mkdir(exist_ok=True)

    filename = CACHE_DIR / f"{mode_name}_season_{season}.json"

    with open(filename, "w") as f:
        json.dump(characters, f, indent=2)

    print(
        f"✅ Saved {len(characters)} characters "
        f"to {filename}"
    )


def fetch_all(force=False):
    CACHE_DIR.mkdir(exist_ok=True)

    for mode, mode_name in MODES.items():
        print(f"\n===== {mode_name.upper()} =====")

        for season in range(1, MAX_SEASON + 1):
            filename = CACHE_DIR / f"{mode_name}_season_{season}.json"

            if filename.exists() and not force:
                print(
                    f"Skipping Season {season} "
                    f"({mode_name}) - cache exists"
                )
                continue

            print(
                f"\n=== Season {season} "
                f"({mode_name.upper()}) ==="
            )

            characters = fetch_season_ladder(
                season,
                mode
            )

            save_cache(
                season,
                mode_name,
                characters
            )


def main():
    fetch_all(force=False)


if __name__ == "__main__":
    main()