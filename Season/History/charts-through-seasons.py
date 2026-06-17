import requests
from collections import Counter, defaultdict
import matplotlib.pyplot as plt

CLASS_LABELS = {
    "ama": "Amazon",
    "asn": "Assassin",
    "bar": "Barbarian",
    "dru": "Druid",
    "nec": "Necromancer",
    "pal": "Paladin",
    "sor": "Sorceress",
}

SEASON_LENGTHS = {
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


def fetch_ladder_characters(season, mode, start_page=1, end_page=5):
    all_characters = []

    for page in range(start_page, end_page + 1):
        url = f"https://beta.pathofdiablo.com/api/ladder/{season}/{mode}/0/{page}"
        print(f"Fetching {url}")

        response = requests.get(url)

        if response.status_code != 200:
            print(f"⚠️ Failed: {response.status_code}")
            break

        data = response.json()
        ladder = data.get("ladder", [])

        if not ladder:
            break

        all_characters.extend(ladder)

    return all_characters

def count_classes(characters, min_level=80):
    counts = Counter()

    for char in characters:
        if char.get("level", 0) < min_level:
            continue

        cls = char.get("charClass")
        if cls:
            counts[cls] += 1

    return counts

def get_all_season_counts(hardcore=False):
    mode = 1 if hardcore else 0
    season_counts = {}

    MAX_SEASON = 13

    for season in range(1, MAX_SEASON + 1):
        print(f"\n=== Season {season} ===")

        chars = fetch_ladder_characters(season, mode)

        if not chars:
            print(f"Season {season}: no data")
            continue

        print(f"Fetched {len(chars)} characters")

#        season_counts[season] = count_classes(chars)
        season_counts[season] = count_classes(chars, min_level=95)

    return season_counts

def plot_class_history(season_counts, filename):
    if not season_counts:
        print(f"⚠️ No data to plot for {filename}")
        return

    seasons = sorted(season_counts.keys())

    bottoms = [0] * len(seasons)

    plt.figure(figsize=(12, 6))

    for code, label in CLASS_LABELS.items():
        values = [
            season_counts[season].get(code, 0)
            for season in seasons
        ]

        print(f"{label}: {values}")

        plt.bar(
            seasons,
            values,
            bottom=bottoms,
            label=label
        )

        bottoms = [
            b + v
            for b, v in zip(bottoms, values)
        ]

    plt.xlabel("Season")
    plt.ylabel("Characters in Top 1000")
    plt.title("Class Distribution by Season")
    plt.xticks(seasons)
    plt.legend(title="Class")

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()

    print(f"✅ Saved chart to {filename}")

def plot_class_lines(season_counts, filename):
    seasons = sorted(season_counts.keys())

    plt.figure(figsize=(12, 6))

    for code, label in CLASS_LABELS.items():
        values = [
            season_counts[s].get(code, 0)
            for s in seasons
        ]

        plt.plot(seasons, values, marker='o', label=label)

    plt.xlabel("Season")
    plt.ylabel("Top 1000 Count (Level ≥ 80)")
    plt.title("Class Meta Over Seasons")
    plt.xticks(seasons)
    plt.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()

def plot_class_percentage_lines(season_counts, filename):
    seasons = sorted(season_counts.keys())

    plt.figure(figsize=(12, 6))

    for code, label in CLASS_LABELS.items():
        values = []

        for s in seasons:
            counts = season_counts[s]
            total = sum(counts.values()) or 1

            values.append(
                100 * counts.get(code, 0) / total
            )

        plt.plot(seasons, values, marker='o', label=label)

    plt.xlabel("Season")
    plt.ylabel("Share of Top 1000 (%)")
    plt.title("Class Meta Share Over Seasons (Level ≥ 80)")
    plt.xticks(seasons)
    plt.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()

import numpy as np

def plot_class_heatmap(season_counts, filename):
    seasons = sorted(season_counts.keys())
    classes = list(CLASS_LABELS.keys())

    data = []

    for code in classes:
        row = [
            season_counts[s].get(code, 0)
            for s in seasons
        ]
        data.append(row)

    data = np.array(data)

    plt.figure(figsize=(12, 5))

    plt.imshow(data, aspect="auto")

    plt.yticks(range(len(classes)), [CLASS_LABELS[c] for c in classes])
    plt.xticks(range(len(seasons)), seasons)

    plt.colorbar(label="Count (Level ≥ 80)")

    plt.title("Class Meta Heatmap Over Seasons")

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()    


def main():
    print("Getting SC counts...")
    sc_counts = get_all_season_counts(False)

    print("SC done.")
    print(sc_counts)

    print("About to plot SC...")
    plot_class_history(sc_counts, "sc_class_history.png")
    plot_class_lines(sc_counts, "sc_class_lines.png")
    plot_class_percentage_lines(sc_counts, "sc_class_percentage_lines.png")
#    plot_class_heatmap(sc_counts, "sc_class_heatmap.png")
    print("SC plotted.")

    print("Getting HC counts...")
    hc_counts = get_all_season_counts(True)

    print("HC done.")
    print(hc_counts)

    print("About to plot HC...")
    plot_class_history(hc_counts, "hc_class_history.png")
    plot_class_lines(hc_counts, "hc_class_lines.png")
    plot_class_percentage_lines(hc_counts, "hc_class_percentage_lines.png")
#    plot_class_heatmap(hc_counts, "hc_class_heatmap.png")
    print("HC plotted.")


if __name__ == "__main__":
    main()