import json
from pathlib import Path
from collections import Counter
import math
from statistics import median

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "season_cache"
OUT_FILE = SCRIPT_DIR / "meta_analysis.json"

SEASONS = range(1, 14)

CLASS_LABELS = {
    "ama": "Amazon",
    "asn": "Assassin",
    "bar": "Barbarian",
    "dru": "Druid",
    "nec": "Necromancer",
    "pal": "Paladin",
    "sor": "Sorceress",
}

SEASON_LENGTH = {
    1: 5,
    2: 4,
    3: 5,
    4: 5,
    5: 6,
    6: 7,
    7: 8,
    8: 6,
    9: 8,
    10: 8,
    11: 36,
    12: 9,
    13: 16
}

TOP_CUTOFFS = [1000, 500, 250, 100]
LEVELS = [80, 90, 95, 96, 97, 98, 99]

def dominance_index(counts):
    total = sum(counts.values())
    if total == 0:
        return 0

    # Herfindahl-style concentration
    return sum((v / total) ** 2 for v in counts.values())

def load(mode, season):
    path = CACHE_DIR / f"{mode}_season_{season}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def count(chars, min_level):
    c = Counter()
    total = 0

    for ch in chars:
        if ch.get("level", 0) >= min_level:
            cls = ch.get("charClass")
            if cls:
                c[cls] += 1
            total += 1

    return total, c


def build():
    out = {
        "sc": {},
        "hc": {},
        "classes": CLASS_LABELS
    }

    for mode in ["sc", "hc"]:
        for season in SEASONS:
            chars = load(mode, season)

            if not chars:
                continue

            out[mode][season] = {
                "season_length": SEASON_LENGTH.get(season)
            }

            for cutoff in TOP_CUTOFFS:
                out[mode][season][str(cutoff)] = {}

                # Top N by rank
                subset = chars[:cutoff]

                for min_level in LEVELS:
                    out[mode][season][str(cutoff)][str(min_level)] = summarize(
                        subset,
                        min_level
                    )

    OUT_FILE.write_text(json.dumps(out, indent=2))
    print(f"Saved {OUT_FILE}")

def summarize(chars, min_level):
    counts = Counter()
    levels = []

    accounts = set()
    unknown_accounts = 0

    for ch in chars:
        level = ch.get("level", 0)

        if level < min_level:
            continue

        levels.append(level)

        cls = ch.get("charClass")
        if cls:
            counts[cls] += 1

        account = ch.get("account")

        if account:
            accounts.add(account)
        else:
            unknown_accounts += 1

    total = len(levels)

    if total:
        avg_level = round(sum(levels) / total, 1)
        med_level = median(levels)
    else:
        avg_level = 0
        med_level = 0

    known_accounts = len(accounts)

    if total:
        coverage = round(
            100 * (total - unknown_accounts) / total,
            1
        )
    else:
        coverage = 0

    return {
        "total": total,
        "counts": dict(counts),
        "dominance": dominance_index(counts),
        "average_level": avg_level,
        "median_level": med_level,
        "unique_accounts": known_accounts,
        "unknown_accounts": unknown_accounts,
        "account_coverage": coverage,
    }

if __name__ == "__main__":
    build()