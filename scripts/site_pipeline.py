#!/usr/bin/env python3
"""Collect, publish and archive consistent snapshots of the Trends site."""

import argparse
import importlib.util
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
API = "https://beta.pathofdiablo.com/api"
CLASSES = {1: "Amazon", 7: "Assassin", 5: "Barbarian", 6: "Druid",
           3: "Necromancer", 4: "Paladin", 2: "Sorceress"}
CODES = {"ama": "Amazon", "asn": "Assassin", "bar": "Barbarian",
         "dru": "Druid", "nec": "Necromancer", "pal": "Paladin",
         "sor": "Sorceress"}
PAGES = ("home.html", "class.html", "items.html", "charms.html",
         "mercenaries.html", "funfacts.html", "advancedsearch.html",
         "sc-usage-over-time.html", "hc-usage-over-time.html")
ASSET_DIRS = ("css", "icons", "armory", "d2images", "templates", "js")
STATE = Path("data/snapshot.json")
MANIFEST = Path("data/history.json")


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, separators=(",", ":"))
        file.write("\n")


def get_json(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_season(session):
    seasons = get_json(session, f"{API}/ladder-summaries")
    if not isinstance(seasons, list) or not seasons:
        raise ValueError("The season API returned no seasons")
    current = [season for season in seasons if season.get("current")]
    if len(current) > 1:
        raise ValueError("The season API returned multiple current seasons")
    season = current[0] if current else max(seasons, key=lambda row: int(row["season"]))
    number = int(season["season"])
    return {"season": number, "status": "active" if current else "post-season",
            "end": season.get("end")}


def ladder_page(session, season, mode, class_id, page):
    url = f"{API}/ladder/{season}/{mode}/{class_id}/{page}"
    data = get_json(session, url)
    if not isinstance(data, dict) or not isinstance(data.get("ladder"), list):
        raise ValueError(f"Invalid ladder response: {url}")
    return data["ladder"]


def load_extractor(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_mode(session, season, mode, destination, firsts):
    prefix = "hc" if mode else "sc"
    print(f"Collecting {prefix.upper()} Season {season}", flush=True)
    pages = [ladder_page(session, season, mode, 0, page) for page in range(6)]
    class_pages = {class_id: ladder_page(session, season, mode, class_id, 0)
                   for class_id in CLASSES}
    class_extra = [ladder_page(session, season, mode, class_id, page)
                   for class_id in CLASSES for page in range(1, 6)]
    rows = [row for page in pages + class_extra for row in page]
    names = {row["charName"] for row in rows if row.get("charName")}
    if not names or not pages[0]:
        raise ValueError(f"No {prefix.upper()} ladder characters returned")
    characters = []
    for index, name in enumerate(sorted(names), 1):
        character = get_json(session, f"{API}/characters/{quote(name, safe='')}/summary")
        if not isinstance(character, dict) or not character.get("Name") or not character.get("Class"):
            raise ValueError(f"Invalid character summary for {name}")
        characters.append(character)
        if index % 100 == 0:
            print(f"  {index}/{len(names)} characters", flush=True)
    write_json(destination / f"{prefix}_ladder.json", characters)
    json_dir = destination / "jsons"
    json_dir.mkdir(parents=True, exist_ok=True)
    # Some pages use the root data path; others use jsons/.
    shutil.copyfile(destination / f"{prefix}_ladder.json", json_dir / f"{prefix}_ladder.json")
    for class_name in CLASSES.values():
        matching = [character for character in characters
                    if character.get("Class") == class_name
                    and (character.get("Stats") or {}).get("Level", 0) > 60]
        write_json(json_dir / f"{prefix}{class_name.lower()}.json", matching)

    top1k = []
    for row in [row for page in pages[1:] for row in page]:
        top1k.append({"rank": row.get("rank"), "name": row.get("charName") or row.get("name"),
                      "account": row.get("account"), "charClass": row.get("charClass"),
                      "class": CODES.get(row.get("charClass"), row.get("charClass")),
                      "level": row.get("level"), "exp": row.get("exp")})
    leaders = {}
    for class_id, class_name in CLASSES.items():
        leaders[class_name] = [
            {"rank": row.get("rank"), "name": row.get("charName") or row.get("name"),
             "level": row.get("level"), "account": row.get("account"), "exp": row.get("exp")}
            for row in class_pages[class_id][:5]
        ]
    write_json(json_dir / f"{prefix}-top1k.json", top1k)
    write_json(json_dir / f"{prefix}-classleaders.json", leaders)

    top10 = [{"name": row.get("charName", "Unknown"), "level": row.get("level", 0),
              "className": CODES.get(row.get("charClass"), row.get("charClass", "Unknown")),
              "rank": row.get("rank", 0), "maxLevelDate": row.get("maxLevelDate")}
             for row in pages[0][:10]]
    grouped = {}
    for row in firsts:
        if row.get("season") != season or row.get("gameMode") != mode:
            continue
        key = (row.get("charName"), row.get("charLevel"), row.get("charClass"))
        entry = grouped.setdefault(key, {"name": row.get("charName", "Unknown"),
                                        "level": row.get("charLevel", 0),
                                        "className": row.get("charClass", "Unknown"),
                                        "kills": []})
        difficulty, boss = row.get("difficulty", "Unknown"), row.get("bossName", "Unknown")
        entry["kills"].append(f"First {boss} Kill" if difficulty == "Hell"
                              else f"First {difficulty} {boss} Kill")
    write_json(json_dir / f"{prefix}_ladder_summary.json",
               {"season": season, "mode": prefix, "top10": top10,
                "ladderFirsts": list(grouped.values())})
    for script, function, suffix in (
        ("create-charm-jsons.py", "extract_charm_data", "charms"),
        ("create-mercenary-jsons.py", "extract_mercenary_data", "mercs"),
        ("create-funfacts-jsons.py", "extract_funfacts_data", "funfacts"),
    ):
        extractor = load_extractor(script)
        getattr(extractor, function)(destination / f"{prefix}_ladder.json",
                                     json_dir / f"{prefix}-{suffix}.json")
    return len(characters)


def collect_snapshot(session, season, destination, now):
    firsts = get_json(session, f"{API}/ladder-firsts")
    if not isinstance(firsts, list):
        raise ValueError("Invalid ladder-firsts response")
    counts = {prefix: collect_mode(session, season["season"], mode, destination, firsts)
              for prefix, mode in (("sc", 0), ("hc", 1))}
    metadata = {**season, "capture_started_at": now.isoformat(),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "counts": counts, "version": 1}
    write_json(destination / STATE, metadata)
    return metadata


def copy_data(source, target, include_duplicate_ladders=True):
    for mode in ("sc", "hc"):
        shutil.copy2(source / f"{mode}_ladder.json", target / f"{mode}_ladder.json")
    (target / "jsons").mkdir(parents=True, exist_ok=True)
    for path in (source / "jsons").iterdir():
        if path.is_file() and (include_duplicate_ladders or path.name not in
                               ("sc_ladder.json", "hc_ladder.json")):
            shutil.copy2(path, target / "jsons" / path.name)
    write_json(target / STATE, read_json(source / STATE))


def create_archive(root, source, metadata, kind, month=None):
    season = metadata["season"]
    if kind == "final":
        path = root / "Season" / str(season) / "Final"
    else:
        path = root / "Season" / str(season) / "snapshots" / month
    if path.exists():
        print(f"Archive already exists, leaving it unchanged: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    # A temporary sibling prevents an interrupted run leaving an incomplete archive.
    with tempfile.TemporaryDirectory(prefix=".archive-", dir=path.parent) as temp:
        staging = Path(temp) / "snapshot"
        staging.mkdir()
        for page in PAGES:
            content = (root / page).read_text(encoding="utf-8")
            if page not in ("sc-usage-over-time.html", "hc-usage-over-time.html"):
                navbar_root = 'data-site-root="./"'
                if navbar_root not in content:
                    raise ValueError(f"{page} is missing the site navbar root")
                relative_root = os.path.relpath(root, path).replace(os.sep, "/") + "/"
                content = content.replace(navbar_root, f'data-site-root="{relative_root}"', 1)
            if page == "items.html":
                old_path = "fetch(`jsons/${filename}`)"
                if old_path not in content:
                    raise ValueError("Items page ladder path changed; snapshot conversion needs updating")
                content = content.replace(old_path, "fetch(`${filename}`)", 1)
            if page not in ("sc-usage-over-time.html", "hc-usage-over-time.html"):
                content = content.replace("</head>", '<script defer src="js/archive-banner.js"></script>\n</head>', 1)
            (staging / page).write_text(content, encoding="utf-8")
        for directory in ASSET_DIRS:
            shutil.copytree(root / directory, staging / directory)
        shutil.copy2(root / "item-bases.js", staging / "item-bases.js")
        for filename in ("full-sets.js", "items_list.json"):
            (staging / "jsons").mkdir(exist_ok=True)
            shutil.copy2(root / "jsons" / filename, staging / "jsons" / filename)
        copy_data(source, staging, include_duplicate_ladders=False)
        archive_metadata = {**metadata, "kind": kind, "month": month,
                            "archived_at": datetime.now(timezone.utc).isoformat()}
        write_json(staging / "archive_metadata.json", archive_metadata)
        history_url = os.path.relpath(root / "history.html", path)
        (staging / "history.html").write_text(
            f'<!doctype html><meta http-equiv="refresh" content="0; url={history_url}">'
            f'<a href="{history_url}">View all history</a>\n', encoding="utf-8")
        (staging / "index.html").write_text(
            '<!doctype html><meta http-equiv="refresh" content="0; url=home.html">'
            '<a href="home.html">Open snapshot</a>\n', encoding="utf-8")
        staging.rename(path)
    print(f"Created {kind} archive: {path}")
    return True


def generate_manifest(root):
    entries = []
    season_dir = root / "Season"
    for season in sorted(season_dir.iterdir(), key=lambda path: path.name):
        if not season.is_dir() or not season.name.isdigit():
            continue
        number = int(season.name)
        if (season / "Home.html").exists():
            entries.append({"season": number, "kind": "legacy", "label": "Season archive",
                            "url": f"Season/{number}/Home.html"})
        for folder in sorted(season.iterdir(), key=lambda path: path.name):
            if not folder.is_dir() or folder.name == "snapshots":
                continue
            home = folder / "Home.html"
            if not home.exists() and folder.name.lower() == "final":
                home = folder / "home.html"
            if not home.exists():
                continue
            kind = "final" if folder.name.lower() == "final" else "legacy"
            label = "Final ladder" if kind == "final" else folder.name
            month = None
            if kind == "legacy":
                content = home.read_text(encoding="utf-8", errors="replace")
                if "Viewing Post Season" in content:
                    kind = "post-season"
                match = re.search(r"Monthly Archive - (\d{4})-(\d{2})", content)
                if match:
                    month = f"{match.group(1)}-{match.group(2)}"
                    label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
            entries.append({"season": number, "kind": kind,
                            "label": label, "month": month,
                            "url": f"Season/{number}/{folder.name}/{home.name}"})
        snapshots = season / "snapshots"
        if not snapshots.exists():
            continue
        for folder in sorted(snapshots.iterdir(), reverse=True):
            metadata_file = folder / "archive_metadata.json"
            if not metadata_file.is_file() or not (folder / "home.html").is_file():
                continue
            metadata = read_json(metadata_file)
            month = metadata["month"]
            date = datetime.strptime(month, "%Y-%m")
            entries.append({"season": number, "kind": metadata["status"],
                            "label": date.strftime("%B %Y"),
                            "url": f"Season/{number}/snapshots/{folder.name}/home.html",
                            "month": month})
    write_json(root / MANIFEST, {"version": 1, "archives": entries})
    return entries


def run(root, config, now):
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    season = get_season(session)
    print(f"Detected Season {season['season']}: {season['status']}")
    state_path = root / STATE
    previous = read_json(state_path) if state_path.exists() else None
    if previous and previous["status"] == "active" and (
        season["status"] == "post-season" or season["season"] != previous["season"]
    ):
        create_archive(root, root, previous, "final")
    if season["status"] == "post-season" and not (
        root / "Season" / str(season["season"]) / "Final"
    ).exists():
        print(f"::warning::No Final archive or saved active-season snapshot exists for Season {season['season']}; "
              "post-season data cannot reconstruct the final ladder.")
    if previous and (config["post_season_updates"] or previous["status"] == "active"):
        previous_time = datetime.fromisoformat(previous["captured_at"])
        previous_month = previous_time.year * 12 + previous_time.month
        current_month = now.year * 12 + now.month
        if current_month - previous_month == 1:
            create_archive(root, root, previous, "monthly", previous_time.strftime("%Y-%m"))
    if season["status"] == "post-season" and not config["post_season_updates"]:
        print("Season ended; live data is frozen.")
        generate_manifest(root)
        return
    with tempfile.TemporaryDirectory(prefix="pod-stats-") as temp:
        staging = Path(temp)
        metadata = collect_snapshot(session, season, staging, now)
        if get_season(session) != season:
            raise RuntimeError("Season status changed during collection; retry without publishing partial data")
        captured = datetime.fromisoformat(metadata["captured_at"])
        if captured.day >= config["archive_day"]:
            create_archive(root, staging, metadata, "monthly", captured.strftime("%Y-%m"))
        copy_data(staging, root)
    generate_manifest(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-manifest", action="store_true")
    args = parser.parse_args()
    if args.refresh_manifest:
        print(f"Indexed {len(generate_manifest(ROOT))} archives")
        return
    config = read_json(ROOT / "site_config.json")
    if not isinstance(config.get("post_season_updates"), bool):
        raise ValueError("post_season_updates must be true or false")
    if not isinstance(config.get("archive_day"), int) or not 1 <= config["archive_day"] <= 28:
        raise ValueError("archive_day must be between 1 and 28")
    run(ROOT, config, datetime.now(timezone.utc))


if __name__ == "__main__":
    main()
