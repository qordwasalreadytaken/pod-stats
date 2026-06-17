#!/usr/bin/env python3

import json
from pathlib import Path
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import numpy as np


# -----------------------------
# CONFIG
# -----------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "season_cache"

SEASONS = range(1, 14)

MODES = {
    "sc": "Softcore",
    "hc": "Hardcore",
}

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
    # fill yours in here
    1: 4,
    2: 3,
    3: 6,
    4: 5,
    5: 4,
    6: 7,
    7: 8,
    8: 6,
    9: 5,
    10: 7,
    11: 6,
    12: 8,
    13: 9,
}


# -----------------------------
# LOAD DATA
# -----------------------------

def load_season(mode, season):
    path = CACHE_DIR / f"{mode}_season_{season}.json"

    if not path.exists():
        return []

    with open(path) as f:
        return json.load(f)


def load_all(mode):
    data = {}

    for season in SEASONS:
        chars = load_season(mode, season)

        if chars:
            data[season] = chars

    return data


# -----------------------------
# CORE ANALYSIS
# -----------------------------

def filter_by_level(chars, min_level):
    return [
        c for c in chars
        if c.get("level", 0) >= min_level
    ]


def count_classes(chars):
    counts = Counter()

    for c in chars:
        cls = c.get("charClass")
        if cls:
            counts[cls] += 1

    return counts


def season_summary(data, min_level):
    summary = {}

    for season, chars in data.items():
        filtered = filter_by_level(chars, min_level)

        summary[season] = {
            "total": len(filtered),
            "counts": count_classes(filtered)
        }

    return summary


# -----------------------------
# PLOTTING
# -----------------------------

def plot_class_counts(summary, mode, min_level):
    seasons = sorted(summary.keys())

    plt.figure(figsize=(12, 6))

    for cls, label in CLASS_LABELS.items():
        values = [
            summary[s]["counts"].get(cls, 0)
            for s in seasons
        ]

        plt.plot(seasons, values, marker="o", label=label)

    plt.title(f"{mode.upper()} Class Counts (Level {min_level}+)")
    plt.xlabel("Season")
    plt.ylabel("Count in Top 1000")
    plt.legend()
    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_counts_{min_level}.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"Saved {out}")


def plot_class_share(summary, mode, min_level):
    seasons = sorted(summary.keys())

    plt.figure(figsize=(12, 6))

    for cls, label in CLASS_LABELS.items():
        values = []

        for s in seasons:
            total = summary[s]["total"] or 1
            count = summary[s]["counts"].get(cls, 0)

            values.append(count / total * 100)

        plt.plot(seasons, values, marker="o", label=label)

    plt.title(f"{mode.upper()} Class Share % (Level {min_level}+)")
    plt.xlabel("Season")
    plt.ylabel("Share (%)")
    plt.legend()
    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_share_{min_level}.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"Saved {out}")


def plot_season_length_vs_pop(summary, mode, min_level):
    x = []
    y = []

    for season in sorted(summary.keys()):
        if season not in SEASON_LENGTHS:
            continue

        x.append(SEASON_LENGTHS[season])
        y.append(summary[season]["total"])

    plt.figure(figsize=(8, 6))
    plt.scatter(x, y)

    for i, season in enumerate(sorted(summary.keys())):
        if season in SEASON_LENGTHS:
            plt.annotate(season, (x[i], y[i]))

    plt.title(f"{mode.upper()} Season Length vs Pop (Level {min_level}+)")
    plt.xlabel("Season Length (months)")
    plt.ylabel("Population (Top 1000 filtered)")
    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_length_vs_pop_{min_level}.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"Saved {out}")


# -----------------------------
# RUN ALL ANALYSIS
# -----------------------------

def run(mode="sc", min_level=95):
    print(f"\n===== ANALYZING {mode.upper()} | LEVEL {min_level}+ =====")

    data = load_all(mode)
    summary = season_summary(data, min_level)

    plot_class_counts(summary, mode, min_level)
    plot_class_share(summary, mode, min_level)
    plot_season_length_vs_pop(summary, mode, min_level)


def main():
    for mode in ["sc", "hc"]:
        for level in [80, 90, 95]:
            run(mode, level)


if __name__ == "__main__":
    main()#!/usr/bin/env python3

import json
from pathlib import Path
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import numpy as np


# -----------------------------
# CONFIG
# -----------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "season_cache"

SEASONS = range(1, 14)

MODES = {
    "sc": "Softcore",
    "hc": "Hardcore",
}

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


# -----------------------------
# LOAD DATA
# -----------------------------

def load_season(mode, season):
    path = CACHE_DIR / f"{mode}_season_{season}.json"

    if not path.exists():
        return []

    with open(path) as f:
        return json.load(f)


def load_all(mode):
    data = {}

    for season in SEASONS:
        chars = load_season(mode, season)

        if chars:
            data[season] = chars

    return data


# -----------------------------
# CORE ANALYSIS
# -----------------------------

def filter_by_level(chars, min_level):
    return [
        c for c in chars
        if c.get("level", 0) >= min_level
    ]


def count_classes(chars):
    counts = Counter()

    for c in chars:
        cls = c.get("charClass")
        if cls:
            counts[cls] += 1

    return counts


def season_summary(data, min_level):
    summary = {}

    for season, chars in data.items():
        filtered = filter_by_level(chars, min_level)

        summary[season] = {
            "total": len(filtered),
            "counts": count_classes(filtered)
        }

    return summary


# -----------------------------
# PLOTTING
# -----------------------------

def plot_class_counts(summary, mode, min_level):
    seasons = sorted(summary.keys())

    plt.figure(figsize=(12, 6))
    ax = plt.gca()

    # Dark theme
    plt.style.use("dark_background")
    ax.set_facecolor("#222222")
    plt.gcf().set_facecolor("#111111")

    for cls, label in CLASS_LABELS.items():
        values = [
            summary[s]["counts"].get(cls, 0)
            for s in seasons
        ]

        plt.plot(
            seasons,
            values,
            marker="o",
            linewidth=2,
            markersize=6,
            label=label,
            color=CLASS_COLORS[label]
        )

    plt.title(
        f"{mode.upper()} Class Counts (Level {min_level}+)",
        color="#dddddd"
    )
    plt.xlabel("Season", color="#dddddd")
    plt.ylabel("Count in Top 1000", color="#dddddd")

    plt.xticks(seasons, color="#dddddd")
    plt.yticks(color="#dddddd")

    plt.grid(True, alpha=0.2)

    legend = plt.legend()
    legend.get_frame().set_facecolor("#222222")
    legend.get_frame().set_edgecolor("#444444")

    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_counts_{min_level}.png"
    plt.savefig(
        out,
        dpi=300,
        facecolor=plt.gcf().get_facecolor()
    )
    plt.close()

    print(f"Saved {out}")


def plot_class_share(summary, mode, min_level):
    seasons = sorted(summary.keys())

    plt.figure(figsize=(12, 6))

    for cls, label in CLASS_LABELS.items():
        values = []

        for s in seasons:
            total = summary[s]["total"] or 1
            count = summary[s]["counts"].get(cls, 0)

            values.append(count / total * 100)

        plt.plot(seasons, values, marker="o", label=label)

    plt.title(f"{mode.upper()} Class Share % (Level {min_level}+)")
    plt.xlabel("Season")
    plt.ylabel("Share (%)")
    plt.legend()
    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_share_{min_level}.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"Saved {out}")


def plot_season_length_vs_pop(summary, mode, min_level):
    x = []
    y = []

    for season in sorted(summary.keys()):
        if season not in SEASON_LENGTHS:
            continue

        x.append(SEASON_LENGTHS[season])
        y.append(summary[season]["total"])

    plt.figure(figsize=(8, 6))
    plt.scatter(x, y)

    for i, season in enumerate(sorted(summary.keys())):
        if season in SEASON_LENGTHS:
            plt.annotate(season, (x[i], y[i]))

    plt.title(f"{mode.upper()} Season Length vs Pop (Level {min_level}+)")
    plt.xlabel("Season Length (months)")
    plt.ylabel("Population (Top 1000 filtered)")
    plt.tight_layout()

    out = SCRIPT_DIR / f"{mode}_length_vs_pop_{min_level}.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"Saved {out}")


# -----------------------------
# RUN ALL ANALYSIS
# -----------------------------

def run(mode="sc", min_level=95):
    print(f"\n===== ANALYZING {mode.upper()} | LEVEL {min_level}+ =====")

    data = load_all(mode)
    summary = season_summary(data, min_level)

    plot_class_counts(summary, mode, min_level)
#    plot_class_share(summary, mode, min_level)
    plot_season_length_vs_pop(summary, mode, min_level)


def main():
    for mode in ["sc", "hc"]:
        for level in [80, 90, 95, 96, 97, 98, 99]:
            run(mode, level)


if __name__ == "__main__":
    main()