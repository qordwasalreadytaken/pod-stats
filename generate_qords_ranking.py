"""
Generate Qord's Arbitrary Ranking pages (SC and HC).

Data sources:
  - Ladder API (all seasons)  → account mapping, rank, level, exp, charClass
  - Local season JSON files   → current-season item fun tags (Jah runes, runewords, MF, etc.)

Output:
  - QordsRanking.html
  - hcQordsRanking.html

Run from new-analytics/:
  python3 generate_qords_ranking.py
"""

import json
import re
import requests
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from html import escape

BASE_DIR = Path(__file__).parent
BASE_API  = "https://beta.pathofdiablo.com/api"
# Ladder API structure:
# - Main ladder: class_id=0, pages 1-5 (covers ~1000 characters)
# - Class-specific: class_id=1-7, page 1 only (covers top 200 per class)

SC_JSON_CANDIDATES = ["sc_ladder.json"]
HC_JSON_CANDIDATES = ["hc_ladder.json"]

RUNE_XP_WEIGHTS = {
    "Zod": 100,
    "Cham": 100,
    "Jah": 300,
    "Ber": 200,
    "Sur": 100,
    "Vex": 50,
    "Mal": 25,
    "Ist": 25,
}

# Rainbow facet scoring: both key rolls range from 3-5.
# We score each roll separately and then apply an element rarity multiplier,
# with physical and magic facets intentionally weighted highest.
FACET_ROLL_SCORE = {
    3: 60,
    4: 100,
    5: 160,
}

FACET_ELEMENT_MULTIPLIER = {
    "physical": 1.60,
    "magic": 1.50,
    "lightning": 1.25,
    "fire": 1.15,
    "cold": 1.15,
    "poison": 1.15,
}

# Class color mapping for class-count award pills.
CLASS_COLOR_MAP = {
    "ama": "rgb(255, 102, 105)",
    "asn": "rgb(255, 255, 255)",
    "bar": "rgb(150, 105, 32)",
    "dru": "rgb(255, 186, 74)",
    "nec": "rgb(179, 255, 253)",
    "pal": "rgb(255, 243, 112)",
    "sor": "rgb(188, 107, 255)",
}

CLASS_NAME_MAP = {
    "ama": "Amazon",
    "asn": "Assassin",
    "bar": "Barbarian",
    "dru": "Druid",
    "nec": "Necromancer",
    "pal": "Paladin",
    "sor": "Sorceress",
}

CLASS_ICON_MAP = {
    "ama": "d2images/cama.png",
    "asn": "d2images/casn.png",
    "bar": "d2images/cbar.png",
    "dru": "d2images/cdru.png",
    "nec": "d2images/cnec.png",
    "pal": "d2images/cpal.png",
    "sor": "d2images/csor.png",
}

CLASS_DISPLAY_ORDER = ["ama", "asn", "bar", "dru", "nec", "pal", "sor"]

# Optional hard-coded account merge groups so multiple seasonal accounts can
# be treated as one player identity for scoring and achievements.
#
# Example:
# ACCOUNT_MERGE_GROUPS = [
#     {
#         "label": "PlayerOne",
#         "accounts": ["playerone_s13", "playerone_s14", "playerone_s15"],
#     },
# ]
ACCOUNT_MERGE_GROUPS = [
     {
         "label": "Zardoz",
         "accounts": ["zardoz13", "zardoz12", "zardoz11", "zardoz10"],
     },    
     {
         "label": "Cripler",
         "accounts": ["cripler", "cripler2", "lord-cripler"],
     },    
]


def _build_account_merge_maps(groups):
    """Build lookup maps for merged-account handling and validate collisions."""
    account_to_canonical = {}
    canonical_to_label = {}
    canonical_to_primary = {}

    for group in groups:
        label = str(group.get("label") or "").strip()
        accounts = group.get("accounts") or []
        if not label or not isinstance(accounts, list) or not accounts:
            continue

        canonical_key = f"merged:{label}".lower()
        canonical_to_label[canonical_key] = label

        primary = None
        for account in accounts:
            acct = str(account or "").strip()
            if not acct:
                continue
            acct_lower = acct.lower()
            if acct_lower in account_to_canonical:
                raise ValueError(
                    f"Account '{acct}' is listed in multiple ACCOUNT_MERGE_GROUPS entries."
                )
            account_to_canonical[acct_lower] = canonical_key
            if primary is None:
                primary = acct

        if primary:
            canonical_to_primary[canonical_key] = primary

    return account_to_canonical, canonical_to_label, canonical_to_primary


ACCOUNT_TO_CANONICAL, CANONICAL_TO_LABEL, CANONICAL_TO_PRIMARY = _build_account_merge_maps(ACCOUNT_MERGE_GROUPS)


def canonicalize_account(account_name):
    """Return canonical account key for scoring and merge behavior."""
    raw = (account_name or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    return ACCOUNT_TO_CANONICAL.get(lower, lower)


def canonical_display_name(canonical_key, fallback_account):
    """Human-friendly display name for leaderboard rows."""
    return CANONICAL_TO_LABEL.get(canonical_key, fallback_account)


def canonical_primary_account(canonical_key, fallback_account):
    """Primary real account used for outbound profile links."""
    return CANONICAL_TO_PRIMARY.get(canonical_key, fallback_account)


# ── Ladder API ─────────────────────────────────────────────────────────────────

def fetch_current_season():
    try:
        r = requests.get(f"{BASE_API}/ladder-summaries", timeout=10)
        if r.ok:
            rows = r.json()
            cur = next((x for x in rows if x and x.get("current")), None)
            if cur and cur.get("season"):
                return int(cur["season"])
    except Exception:
        pass
    return 13


def fetch_ladder_rows(season, mode):
    """Fetch ladder rows for a season and mode (0=SC, 1=HC).
    
    Fetches:
    - Main ladder (class_id=0): pages 1-5
    - Class-specific ladders (class_id=1-7): page 1 only
    """
    rows = []
    
    # Main ladder (class_id=0) - pages 1-5
    for page in range(1, 6):
        url = f"{BASE_API}/ladder/{season}/{mode}/0/{page}"
        try:
            r = requests.get(url, timeout=10)
            if not r.ok:
                continue
            data = r.json()
            ladder = data.get("ladder") if isinstance(data, dict) else None
            if isinstance(ladder, list):
                rows.extend(ladder)
        except Exception as e:
            print(f"  Warning: {url} -> {e}")
    
    # Class-specific ladders (class_id=1-7) can be indexed inconsistently by
    # the API across classes/seasons (page 0 vs page 1), so fetch both.
    for class_id in range(1, 8):
        for page in (0, 1):
            url = f"{BASE_API}/ladder/{season}/{mode}/{class_id}/{page}"
            try:
                r = requests.get(url, timeout=10)
                if not r.ok:
                    continue
                data = r.json()
                ladder = data.get("ladder") if isinstance(data, dict) else None
                if isinstance(ladder, list):
                    rows.extend(ladder)
            except Exception as e:
                print(f"  Warning: {url} -> {e}")
    
    return rows


def build_all_season_stats(mode, seasons):
    """
    Returns:
      by_account    : account_lower -> stat dict (all-season totals)
      char_to_acct  : charname_lower -> account_lower  (current-season preferred)
      season_presence: account_lower -> set of seasons they appeared in
      class_counts  : account_lower -> {class_name: count}
      season_class_presence: account_lower -> {season: set(class_code)}
    """
    by_account   = defaultdict(lambda: {
        "account": "", "accountHref": "", "charCount": 0, "totalLevels": 0, "totalExp": 0,
        "bestRank": 0, "top5Count": 0, "top10Count": 0, "top100Count": 0, "charClasses": set(),
        "highLevelBonus": 0,
    })
    char_to_acct = {}  # built from all seasons; last-write wins (current season fetched last)
    season_presence = defaultdict(set)  # account_lower -> {seasons}
    class_counts = defaultdict(lambda: defaultdict(int))  # account_lower -> {class: count}
    season_class_presence = defaultdict(lambda: defaultdict(set))  # account_lower -> {season: {class codes}}

    for season in seasons:
        print(f"  Season {season} mode {mode} …", end=" ", flush=True)
        rows = fetch_ladder_rows(season, mode)

        # Dedupe within season: keep best rank per char
        season_best = {}
        for row in rows:
            char_name = (row.get("charName") or "").strip()
            if not char_name:
                continue
            key  = char_name.lower()
            rank = int(row.get("rank") or 0)
            prev = season_best.get(key)
            if prev is None or (rank > 0 and (prev["rank"] == 0 or rank < prev["rank"])):
                season_best[key] = {
                    "charName":  char_name,
                    "account":   (row.get("account") or "").strip(),
                    "rank":      rank,
                    "level":     int(row.get("level") or 0),
                    "exp":       int(row.get("exp")   or 0),
                    "charClass": (row.get("charClass") or ""),
                }

        print(f"{len(season_best)} unique chars")

        for key, char in season_best.items():
            account = char["account"]
            if not account:
                continue
            acct_lower = canonicalize_account(account)
            char_to_acct[key] = acct_lower

            acc = by_account[acct_lower]
            if not acc["account"]:
                acc["account"] = canonical_display_name(acct_lower, account)
            if not acc["accountHref"]:
                acc["accountHref"] = canonical_primary_account(acct_lower, account)
            acc["charCount"]   += 1
            acc["totalLevels"] += char["level"]
            acc["totalExp"]    += char["exp"]
            acc["charClasses"].add(char["charClass"])
            level_for_bonus = max(0, min(99, char["level"]) - 90)
            acc["highLevelBonus"] += level_for_bonus * 100

            # Track season presence and class counts
            season_presence[acct_lower].add(season)
            class_counts[acct_lower][char["charClass"]] += 1
            season_class_presence[acct_lower][season].add(char["charClass"])

            rank = char["rank"]
            if rank > 0:
                if acc["bestRank"] == 0 or rank < acc["bestRank"]:
                    acc["bestRank"] = rank
                if rank <= 5:
                    acc["top5Count"] += 1
                if rank <= 10:
                    acc["top10Count"] += 1
                if rank <= 100:
                    acc["top100Count"] += 1

    season_class_presence_dict = {
        acct: {s: set(classes) for s, classes in by_season.items()}
        for acct, by_season in season_class_presence.items()
    }
    return dict(by_account), char_to_acct, dict(season_presence), dict(class_counts), season_class_presence_dict


# ── Local JSON (current-season item data) ──────────────────────────────────────

def load_first_existing(candidates):
    for name in candidates:
        path = BASE_DIR / name
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                print(f"  Loaded local JSON: {name} ({len(data)} chars)")
                return data, name
    return [], None


def parse_demons_bonus(prop):
    text = str(prop)
    if "damage to demons" not in text.lower():
        return 0
    m = re.search(r'([+-]?\d+)%', text)
    return int(m.group(1)) if m else 0


def count_jah_runes(item):
    count = 0
    if (item.get("Title") or "").strip() == "Jah Rune":
        count += 1
    rune_tag = item.get("RuneTag") or ""
    # RuneTag like "JahBerLemEld" — count occurrences of "Jah"
    count += rune_tag.count("Jah")
    for sock in item.get("Sockets") or []:
        if isinstance(sock, dict) and (sock.get("Title") or "").strip() == "Jah Rune":
            count += 1
    return count


def rune_xp_value(item):
    xp = 0
    title = (item.get("Title") or "").strip()
    rune_tag = item.get("RuneTag") or ""

    for rune, weight in RUNE_XP_WEIGHTS.items():
        if title == f"{rune} Rune":
            xp += weight
        # RuneTag examples: "JahBerLemEld" or "ElSolDolLo"
        xp += rune_tag.count(rune) * weight

    return xp


def rainbow_facet_xp_value(item):
    title = (item.get("Title") or "").strip().lower()
    if title != "rainbow facet":
        return 0

    enemy_roll = 0
    enemy_elem = ""
    dmg_roll = 0
    dmg_elem = ""

    for prop in item.get("PropertyList") or []:
        prop_s = str(prop)

        # Examples:
        #   "-5% to Enemy Fire Resistance"
        #   "-4% to Enemy Magic Resistance"
        m_enemy = re.search(r'-(\d+)%\s+to\s+Enemy\s+([A-Za-z]+)\s+Resistance', prop_s, re.IGNORECASE)
        if m_enemy:
            enemy_roll = int(m_enemy.group(1))
            enemy_elem = m_enemy.group(2).lower()
            continue

        # Examples:
        #   "+5% Increased Fire Damage"
        #   "+5% Increased Magic Skill Damage"
        #   "+5% Increased Physical Damage"
        m_dmg = re.search(r'\+(\d+)%\s+Increased\s+([A-Za-z]+)(?:\s+Skill)?\s+Damage', prop_s, re.IGNORECASE)
        if m_dmg:
            dmg_roll = int(m_dmg.group(1))
            dmg_elem = m_dmg.group(2).lower()

    if not enemy_roll or not dmg_roll:
        return 0

    # Expected facet rolls are 3-5; clamp to keep scoring stable on weird data.
    enemy_roll = max(3, min(5, enemy_roll))
    dmg_roll = max(3, min(5, dmg_roll))

    facet_elem = enemy_elem or dmg_elem
    if enemy_elem and dmg_elem and enemy_elem != dmg_elem:
        facet_elem = dmg_elem

    base = FACET_ROLL_SCORE[enemy_roll] + FACET_ROLL_SCORE[dmg_roll]
    multiplier = FACET_ELEMENT_MULTIPLIER.get(facet_elem, 1.0)
    return round(base * multiplier)


def _extract_num(pattern, text):
    """Return first captured int from regex match, or 0."""
    m = re.search(pattern, text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def torch_anni_xp_value(character):
    bonus_xp = 0
    inventory = character.get("Inventory") or []
    if not isinstance(inventory, list):
        return 0

    for item in inventory:
        if not isinstance(item, dict):
            continue

        position = item.get("Position") or {}
        y_pos = int(position.get("y") or 0)
        if not (5 <= y_pos <= 8):
            continue

        if (item.get("QualityCode") or "") != "q_unique":
            continue

        props = [str(prop) for prop in (item.get("PropertyList") or [])]
        if not props:
            continue

        has_torch = any("+3 to" in prop and "Skill Levels" in prop for prop in props)
        has_anni = any("+1 to All Skills" in prop for prop in props) and any("Experience Gained" in prop for prop in props)

        if has_torch:
            attributes = 0
            all_res = 0
            for prop in props:
                if "to all Attributes" in prop:
                    attributes = _extract_num(r'([+-]?\d+)', prop)
                elif "All Resistances" in prop:
                    all_res = _extract_num(r'([+-]?\d+)', prop)
            bonus_xp += attributes + all_res
        elif has_anni:
            attributes = 0
            all_res = 0
            exp_gain = 0
            for prop in props:
                if "to all Attributes" in prop:
                    attributes = _extract_num(r'([+-]?\d+)', prop)
                elif "All Resistances" in prop:
                    all_res = _extract_num(r'([+-]?\d+)', prop)
                elif "Experience Gained" in prop:
                    exp_gain = _extract_num(r'([+-]?\d+)', prop)
            bonus_xp += attributes + all_res + exp_gain

    return bonus_xp


def collect_item_tags(character):
    total_sockets  = 0
    demons_bonus   = 0
    half_freeze    = 0
    jah_runes      = 0
    rune_xp        = 0
    rainbow_facet_xp = 0
    runewords      = 0
    ethereals      = 0
    corrupted      = 0
    life_leech     = 0
    mana_leech     = 0
    replenish_life = 0
    poison_res     = 0
    cold_res       = 0
    light_radius   = 0
    stamina        = 0
    crushing_blow  = 0
    deadly_strike  = 0
    dmg_reduced    = 0
    thorns_value   = 0
    thorns_count   = 0
    fire_absorb    = 0
    req_reduced    = 0
    dangoon_items  = 0
    delerium_helms = 0
    torch_anni_xp  = 0
    magic_items    = 0
    rare_items     = 0
    unique_items   = 0
    crafted_items  = 0
    rare_armor     = 0

    def consume(item):
        nonlocal total_sockets, demons_bonus, half_freeze, jah_runes, rune_xp, rainbow_facet_xp, runewords
        nonlocal ethereals, corrupted, life_leech, mana_leech, replenish_life
        nonlocal poison_res, cold_res, light_radius, stamina, crushing_blow
        nonlocal deadly_strike, dmg_reduced, thorns_value, thorns_count
        nonlocal fire_absorb, req_reduced
        nonlocal dangoon_items, delerium_helms
        if not isinstance(item, dict):
            return
        total_sockets += int(item.get("SocketCount") or 0)
        title_l = str(item.get("Title") or "").lower()
        runetag = str(item.get("RuneTag") or "")
        if "dangoon" in title_l:
            dangoon_items += 1
        if "delirium" in title_l or "delerium" in title_l  or "2693" in title_l or runetag == "LemIstIo":
            delerium_helms += 1
        if item.get("QualityCode") == "q_runeword":
            runewords += 1
        if str(item.get("Ethereal", "")).lower() == "true":
            ethereals += 1
        jah_runes += count_jah_runes(item)
        rune_xp += rune_xp_value(item)
        rainbow_facet_xp += rainbow_facet_xp_value(item)
        for prop in item.get("PropertyList") or []:
            prop_s = str(prop)
            prop_l = prop_s.lower()
            demons_bonus   += parse_demons_bonus(prop_s)
            if "half freeze duration" in prop_l:
                half_freeze += 1
            if "ÿc1corrupted" in prop_l or prop_s.strip() == "ÿc1Corrupted":
                corrupted += 1
            if "life stolen per hit" in prop_l:
                life_leech     += _extract_num(r'(\d+)%', prop_s)
            if "mana stolen per hit" in prop_l:
                mana_leech     += _extract_num(r'(\d+)%', prop_s)
            if "replenish life" in prop_l:
                replenish_life += _extract_num(r'replenish life[^\d]*(\d+)', prop_s)
            if "poison resist" in prop_l:
                poison_res     += _extract_num(r'poison resist[^\d]*(\d+)', prop_s)
            if "cold resist" in prop_l:
                cold_res       += _extract_num(r'cold resist[^\d]*(\d+)', prop_s)
            if "light radius" in prop_l:
                light_radius   += _extract_num(r'([+-]?\d+)[^\d]*light radius', prop_s)
            if "maximum stamina" in prop_l:
                stamina        += _extract_num(r'([+-]?\d+)[^\d]*maximum stamina', prop_s)
            if "heal stamina" in prop_l:
                stamina        += _extract_num(r'(\d+)', prop_s)
            if "crushing blow" in prop_l:
                crushing_blow  += _extract_num(r'(\d+)%', prop_s)
            if "deadly strike" in prop_l:
                deadly_strike  += _extract_num(r'(\d+)%', prop_s)
            if "physical damage taken reduced" in prop_l:
                dmg_reduced    += _extract_num(r'(\d+)%', prop_s)
            elif "damage reduced by" in prop_l:
                dmg_reduced    += _extract_num(r'damage reduced by (\d+)', prop_s)
            if "attacker takes damage of" in prop_l:
                thorns_value   += _extract_num(r'attacker takes damage of (\d+)', prop_s)
                thorns_count   += 1
            if "fire absorb" in prop_l:
                fire_absorb    += _extract_num(r'([+-]?\d+)', prop_s)
            if "requirements -" in prop_l:
                req_reduced    += _extract_num(r'requirements -(\d+)', prop_s)
        for sock in item.get("Sockets") or []:
            consume(sock)

    torch_anni_xp += torch_anni_xp_value(character)

    for item in character.get("Equipped") or []:
        quality_code = str(item.get("QualityCode") or "").lower()
        worn_slot = str(item.get("Worn") or "").lower()
        if quality_code == "q_magic":
            magic_items += 1
        elif quality_code == "q_rare":
            rare_items += 1
            if worn_slot == "body":
                rare_armor += 1
        elif quality_code == "q_unique":
            unique_items += 1
        elif quality_code == "q_crafted":
            crafted_items += 1
        consume(item)

    bonus      = character.get("Bonus") or {}
    total_mf   = int(bonus.get("MagicFind") or 0)
    total_gf   = int(bonus.get("GoldFind")  or 0)

    return {
        "totalSockets":  total_sockets,
        "demonsBonus":   demons_bonus,
        "halfFreeze":    half_freeze,
        "jahRunes":      jah_runes,
        "runeXP":        rune_xp,
        "rainbowFacetXP": rainbow_facet_xp,
        "runewords":     runewords,
        "ethereals":     ethereals,
        "corrupted":     corrupted,
        "mf":            total_mf,
        "goldFind":      total_gf,
        "lifeLeech":     life_leech,
        "manaLeech":     mana_leech,
        "replenishLife": replenish_life,
        "poisonRes":     poison_res,
        "coldRes":       cold_res,
        "lightRadius":   light_radius,
        "stamina":       stamina,
        "crushingBlow":  crushing_blow,
        "deadlyStrike":  deadly_strike,
        "dmgReduced":    dmg_reduced,
        "thornsValue":   thorns_value,
        "thornsCount":   thorns_count,
        "fireAbsorb":    fire_absorb,
        "reqReduced":    req_reduced,
        "dangoonItems":  dangoon_items,
        "deleriumHelms": delerium_helms,
        "torchAnniXP":   torch_anni_xp,
        "magicItems":    magic_items,
        "rareItems":     rare_items,
        "uniqueItems":   unique_items,
        "craftedItems":  crafted_items,
        "rareArmor":     rare_armor,
    }


def build_item_tags_by_account(local_chars, char_to_acct):
    zero_tags = {
        "totalSockets": 0, "demonsBonus": 0, "halfFreeze": 0,
        "jahRunes": 0, "runeXP": 0, "rainbowFacetXP": 0, "runewords": 0, "ethereals": 0, "corrupted": 0,
        "mf": 0, "goldFind": 0, "lifeLeech": 0, "manaLeech": 0,
        "replenishLife": 0, "poisonRes": 0, "coldRes": 0, "lightRadius": 0,
        "stamina": 0, "crushingBlow": 0, "deadlyStrike": 0, "dmgReduced": 0,
        "thornsValue": 0, "thornsCount": 0, "fireAbsorb": 0, "reqReduced": 0,
        "dangoonItems": 0, "deleriumHelms": 0, "torchAnniXP": 0,
        "magicItems": 0, "rareItems": 0, "uniqueItems": 0, "craftedItems": 0, "rareArmor": 0,
        "maxMagicItems": 0, "maxRareItems": 0, "maxUniqueItems": 0, "maxCraftedItems": 0, "maxRareArmor": 0,
        "totalStrength": 0,
    }
    by_account = defaultdict(lambda: dict(zero_tags))
    matched = unmatched = 0
    for char in local_chars:
        name = (char.get("Name") or "").strip()
        if not name:
            continue
        acct_lower = char_to_acct.get(name.lower())
        if not acct_lower:
            acct_lower = canonicalize_account(char.get("Account") or "")
        if not acct_lower:
            unmatched += 1
            continue
        matched += 1
        tags = collect_item_tags(char)
        acc  = by_account[acct_lower]
        for k, v in tags.items():
            acc[k] += v
        # Per-character award thresholds should trigger from any single character,
        # so track the maximum seen on one character for quality counters.
        acc["maxMagicItems"] = max(acc["maxMagicItems"], tags.get("magicItems", 0))
        acc["maxRareItems"] = max(acc["maxRareItems"], tags.get("rareItems", 0))
        acc["maxUniqueItems"] = max(acc["maxUniqueItems"], tags.get("uniqueItems", 0))
        acc["maxCraftedItems"] = max(acc["maxCraftedItems"], tags.get("craftedItems", 0))
        acc["maxRareArmor"] = max(acc["maxRareArmor"], tags.get("rareArmor", 0))
        # Strength comes from Stats, not items
        acc["totalStrength"] += int((char.get("Stats") or {}).get("Strength") or 0)
    print(f"  Item tags: {matched} chars matched, {unmatched} unmatched")
    return dict(by_account)


# ── Scoring ────────────────────────────────────────────────────────────────────

def hash32(s):
    h = 2166136261
    for c in s.encode("utf-8", errors="replace"):
        h ^= c
        h = (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) & 0xFFFFFFFF
    return h


BASE_ACHIEVEMENT_RULES = [
    (lambda r: 0 < r["bestRank"] <= 3, "Ladder Aristocracy"),
    (lambda r: r["charCount"] >= 15, "Alt Army Commander"),
    (lambda r: r["top10Count"] >= 3, "Front Page Camper"),
    (lambda r: (r["totalLevels"] / r["charCount"] if r["charCount"] else 0) >= 98, "Council of Sweats"),

    # Casual-friendly participation and light-gear milestones.
    (lambda r: 0 < r["bestRank"] <= 1000, "Made the Ladder"),
    (lambda r: r["charCount"] >= 3, "Weekend Warrior"),
    (lambda r: r["runewords"] >= 1, "Runeword Rookie"),
    (lambda r: r["maxUniqueItems"] >= 2, "Unique Dabbler"),
    (lambda r: r["mf"] >= 150, "Treasure Curious"),
    (lambda r: r["corrupted"] >= 1, "Corruption Tourist"),
]

# Tiered stat achievements: base for meeting threshold, apex for account with most/least.
# Thresholds are deliberately high — most accounts should only get 0-3 base achievements.
ACHIEVEMENT_TIERS = [
    {"key": "jahRunes",      "mode": "max", "threshold": 15,   "base": "Jah Hoarder",             "apex": "Jahs Rule"},
    {"key": "lightRadius",   "mode": "max", "threshold": 25,   "base": "Beacon of Light",          "apex": "Beacon of the Ancients"},
    {"key": "demonsBonus",   "mode": "max", "threshold": 600,  "base": "Slayer of Demons",         "apex": "Demon Hunter"},
    {"key": "lifeLeech",     "mode": "max", "threshold": 50,   "base": "Count of Leeches",         "apex": "Leech Lord"},
    {"key": "manaLeech",     "mode": "max", "threshold": 50,   "base": "The Thirsting",            "apex": "Bottomless"},
    {"key": "goldFind",      "mode": "max", "threshold": 700,  "base": "Treasure Hoarder",         "apex": "King Midas"},
    {"key": "mf",            "mode": "max", "threshold": 600,  "base": "Treasure Hunter",             "apex": "Golden Tyrant"},
    {"key": "replenishLife", "mode": "max", "threshold": 60,   "base": "The Regenerating",         "apex": "The Everliving"},
    {"key": "poisonRes",     "mode": "max", "threshold": 600,  "base": "Venom Ward",               "apex": "Serpentproof"},
    {"key": "coldRes",       "mode": "max", "threshold": 600,  "base": "Frostforged",              "apex": "Winterproof"},
    {"key": "stamina",       "mode": "max", "threshold": 600,  "base": "The Tireless",             "apex": "All Night Long"},
    {"key": "totalSockets",  "mode": "max", "threshold": 45,   "base": "Socket Goblin",            "apex": "Perforation Master"},
    {"key": "ethereals",     "mode": "max", "threshold": 8,    "base": "Ghost-Touched",            "apex": "The Glassiest"},
    {"key": "crushingBlow",  "mode": "max", "threshold": 150,  "base": "Bonebreaker",              "apex": "Skullsplitter"},
    {"key": "deadlyStrike",  "mode": "max", "threshold": 300,  "base": "The Executioner",          "apex": "Headsman"},
    {"key": "dmgReduced",    "mode": "max", "threshold": 120,   "base": "The Unyielding",           "apex": "Adamantine"},
    {"key": "thornsValue",   "mode": "max", "threshold": 1000,  "base": "The Spiteful",             "apex": "Porcupine"},
    {"key": "halfFreeze",    "mode": "max", "threshold": 7,    "base": "Mildly Chilled",           "apex": "Permafrost"},
    {"key": "thornsCount",   "mode": "max", "threshold": 7,    "base": "Touch Me Not",             "apex": "Needle Wall"},
    {"key": "fireAbsorb",    "mode": "max", "threshold": 30,   "base": "Fire Eater",           "apex": "Inferno Drinker"},
    {"key": "reqReduced",    "mode": "max", "threshold": 200,   "base": "Bare Minimum",             "apex": "Requirement Annihilator"},
    {"key": "totalStrength", "mode": "min", "threshold": 100,  "base": "Frail",                   "apex": "Paper Bones", "min_chars": 2},
]

# Winner-only legendary achievements (former award tile titles).
LEGENDARY_ACHIEVEMENTS = [
    {"key": "charCount", "mode": "max", "title": "An Army for the Ages"},
    {"key": "arbitraryXP", "mode": "max", "title": "The Most Experienced"},
    {"key": "jahRunes", "mode": "max", "title": "JAH-Makin' Me Crazy"},
    {"key": "runewords", "mode": "max", "title": "Known Creationist"},
    {"key": "demonsBonus", "mode": "max", "title": "+Damage to Demons Champion"},
    {"key": "lifeLeech", "mode": "max", "title": "Life Leech Champion"},
    {"key": "manaLeech", "mode": "max", "title": "Mana Leech Champion"},
    {"key": "crushingBlow", "mode": "max", "title": "Crushing Blow Champion"},
    {"key": "deadlyStrike", "mode": "max", "title": "Deadly Strike Champion"},
    {"key": "thornsValue", "mode": "max", "title": "The Thorny"},
    {"key": "dmgReduced", "mode": "max", "title": "It's Merely a Flesh Wound"},
    {"key": "ethereals", "mode": "max", "title": "The Glassiest"},
    {"key": "poisonRes", "mode": "max", "title": "Unpoisonable"},
    {"key": "coldRes", "mode": "max", "title": "Wears Shorts in Winter"},
    {"key": "fireAbsorb", "mode": "max", "title": "A Fire Inside"},
    {"key": "mf", "mode": "max", "title": "Magic Find Champion"},
    {"key": "goldFind", "mode": "max", "title": "Scrooge McDuck"},
    {"key": "totalSockets", "mode": "max", "title": "Most Holyest"},
    {"key": "replenishLife", "mode": "max", "title": "Replenish Life Champion"},
    {"key": "lightRadius", "mode": "max", "title": "A Beacon of Light"},
    {"key": "stamina", "mode": "max", "title": "Goes the Distance"},
    {"key": "halfFreeze", "mode": "max", "title": "Half-Frozen"},
    {"key": "thornsCount", "mode": "max", "title": "Stop Hitting Yourself"},
    {"key": "reqReduced", "mode": "max", "title": "Requirements Minimizer"},
    {"key": "totalStrength", "mode": "min", "title": "Frailest Account", "min_chars": 2},
]


CP_TITLES = {
    1: "Drifter",
    2: "Beggar",
    3: "Wanderer",
    4: "Outcast",
    5: "Pilgrim",
    6: "Wayfarer",
    7: "Watchman",
    8: "Scout",
    9: "Hunter",
    10: "Tracker",
    11: "Guard",
    12: "Sentinel",
    13: "Defender",
    14: "Caravaner",
    15: "Mercenary",
    16: "Sellsword",
    17: "Footman",
    18: "Warrior",
    19: "Slayer",
    20: "Demonhunter",
    21: "Initiate",
    22: "Novice",
    23: "Acolyte",
    24: "Disciple",
    25: "Zealot",
    26: "Confessor",
    27: "Cleric",
    28: "Templar",
    29: "Crusader",
    30: "Justicar",
    31: "Warden",
    32: "Castellan",
    33: "Knight",
    34: "Knight Errant",
    35: "Bloodguard",
    36: "Hellguard",
    37: "Bannerman",
    38: "Commander",
    39: "Marshal",
    40: "Warmaster",
    41: "Baron",
    42: "Count",
    43: "Earl",
    44: "Viscount",
    45: "Highborn",
    46: "Noble",
    47: "Lord",
    48: "High Lord",
    49: "Grand Lord",
    50: "Dread Lord",
    51: "Inquisitor",
    52: "High Inquisitor",
    53: "Prelate",
    54: "Canon",
    55: "Archcanon",
    56: "Hierophant",
    57: "Lightbearer",
    58: "Hand of Zakarum",
    59: "High Templar",
    60: "Grand Justicar",
    61: "Sage",
    62: "Lorekeeper",
    63: "Archivist",
    64: "Seeker",
    65: "Horadric Scholar",
    66: "Horadric Adept",
    67: "Summoner",
    68: "Magus",
    69: "Vizjerei",
    70: "Horadrim",
    71: "Soulkeeper",
    72: "Doomcaller",
    73: "Abysswalker",
    74: "Hellbinder",
    75: "Soulreaper",
    76: "Deathspeaker",
    77: "Harbinger",
    78: "Doombringer",
    79: "Hellforged",
    80: "Infernal",
    81: "Ascendant",
    82: "Exalted",
    83: "Eternal",
    84: "Immortal",
    85: "Worldwalker",
    86: "Fatebringer",
    87: "Riftwarden",
    88: "Archon",
    89: "Paragon",
    90: "Nephalem",
    91: "Ancient One",
    92: "Hellslayer",
    93: "Primebane",
    94: "Angelbane",
    95: "Demonbane",
    96: "Worldbreaker",
    97: "Harbinger of Fate",
    98: "Lord of Sanctuary",
    99: "Eternal Nephalem",
}


def assign_cp_titles(rows):
    """Assign CP title by arbitrary XP placement (top=99, bottom=1)."""
    total = len(rows)
    if total <= 1:
        for row in rows:
            row["cpLevel"] = 99
            row["cpTitle"] = CP_TITLES[99]
        return

    for idx, row in enumerate(rows):
        # idx=0 is top row and should receive level 99.
        cp_level = int(round((total - 1 - idx) * 98 / (total - 1))) + 1
        cp_level = max(1, min(99, cp_level))
        row["cpLevel"] = cp_level
        row["cpTitle"] = CP_TITLES.get(cp_level, "Drifter")


def assign_achievements(rows, season_presence=None, class_counts=None, season_class_presence=None, current_season=None):
    """Assigns zero-to-many achievements per account, tracking apex and legendary tiers."""
    season_presence = season_presence or {}
    class_counts = class_counts or {}
    season_class_presence = season_class_presence or {}
    row_by_account = {r["account"].lower(): r for r in rows}

    def prestige_label_for_season_count(season_count):
        # Requested mapping: n seasons -> Prestige (n-1), with named labels for 1 and 2.
        if season_count < 2:
            return None
        prestige_level = season_count - 1
        if prestige_level == 1:
            return "Prestige I"
        if prestige_level == 2:
            return "Prestige II"
        if prestige_level == 3:
            return "Prestige III"
        if prestige_level == 4:
            return "Prestige IV"
        if prestige_level == 5:
            return "Prestige V"
        if prestige_level == 6:
            return "Prestige VI"
        if prestige_level == 7:
            return "Prestige VII"
        if prestige_level == 8:
            return "Prestige VIII"
        if prestige_level == 9:
            return "Prestige IX"
        if prestige_level == 10:
            return "Prestige X"
        if prestige_level == 11:
            return "Prestige XI"
        if prestige_level == 12:
            return "Prestige XII"
        if prestige_level == 13:
            return "Prestige XIII"
        if prestige_level == 14:
            return "Prestige XIV"
        if prestige_level == 15:
            return "Prestige XV"
        return f"Prestige {prestige_level}"
    
    winners = {}
    for tier in ACHIEVEMENT_TIERS:
        key = tier["key"]
        mode = tier["mode"]
        min_chars = tier.get("min_chars", 1)
        candidates = [r for r in rows if r.get(key, 0) > 0 and r["charCount"] >= min_chars]
        if not candidates:
            continue
        winners[key] = min(candidates, key=lambda r: r[key]) if mode == "min" else max(candidates, key=lambda r: r[key])

    legendary_winners = {}
    for tier in LEGENDARY_ACHIEVEMENTS:
        key = tier["key"]
        mode = tier["mode"]
        min_chars = tier.get("min_chars", 1)
        candidates = [r for r in rows if r.get(key, 0) > 0 and r["charCount"] >= min_chars]
        if not candidates:
            continue
        legendary_winners[key] = min(candidates, key=lambda r: r[key]) if mode == "min" else max(candidates, key=lambda r: r[key])

    # Special achievements: season-based and class-based
    taking_a_break = set()  # accounts in season-1 but not current
    breaktime_over = set()  # accounts in current and season-2, but not season-1
    one_trick_pony = set()  # exactly one ladder character in exactly one season
    many_faces = set()  # has all 7 classes represented in at least one season
    stayed_a_while = set()  # appears in any 3 consecutive seasons
    baby_come_back = set()  # absent for the last two seasons
    afk_since = {}  # account_lower -> most recent season seen when absent in current season
    class_winners = {}  # class -> account_lower with most of that class
    required_class_codes = {"ama", "asn", "bar", "dru", "nec", "pal", "sor"}
    
    # Class achievement mapping: full name -> achievement title
    class_achievements = {
        "Assassin": "Killer",
        "Druid": "Tree Hugger",
        "Paladin": "Dindin",
        "Necromancer": "Undead",
        "Amazon": "Pew Pew",
        "Sorceress": "The Magician",
        "Barbarian": "GD Hates Barbs",
    }
    
    # API class codes by full class name.
    class_code_by_name = {
        "Assassin": "asn",
        "Druid": "dru",
        "Paladin": "pal",
        "Necromancer": "nec",
        "Amazon": "ama",
        "Sorceress": "sor",
        "Barbarian": "bar",
    }
    
    if current_season and season_presence and class_counts:
        for acct_lower, seasons in season_presence.items():
            sorted_seasons = sorted(seasons)

            # Taking a Break: on season N-1, not on season N
            if (current_season - 1) in seasons and current_season not in seasons:
                taking_a_break.add(acct_lower)

            # Breaktime's Over: on season N, not on N-1, but was on N-2
            if current_season in seasons and (current_season - 1) not in seasons and (current_season - 2) in seasons:
                breaktime_over.add(acct_lower)

            # One Trick Pony: exactly one character total in exactly one season.
            row = row_by_account.get(acct_lower)
            if row and row.get("charCount", 0) == 1 and len(seasons) == 1:
                one_trick_pony.add(acct_lower)

            # Many Faces: all 7 classes in at least one single season.
            by_season_classes = season_class_presence.get(acct_lower, {})
            if any(required_class_codes.issubset(class_set) for class_set in by_season_classes.values()):
                many_faces.add(acct_lower)

            # Stayed a While to Listen: any 3 consecutive seasons present.
            if any((s + 1 in seasons) and (s + 2 in seasons) for s in sorted_seasons):
                stayed_a_while.add(acct_lower)

            # Baby Come Back: missing current and previous season, but seen before that.
            if (
                current_season not in seasons
                and (current_season - 1) not in seasons
                and any(s <= (current_season - 2) for s in seasons)
            ):
                baby_come_back.add(acct_lower)

            # AFK Since Sx: not on current ladder, show last season they were seen.
            if current_season not in seasons and sorted_seasons:
                afk_since[acct_lower] = sorted_seasons[-1]
        
        # Class winners: most of each class across all seasons
        for full_class_name in class_achievements.keys():
            max_count = -1
            winner_acct = None
            class_code = class_code_by_name.get(full_class_name)
            if not class_code:
                continue

            # Find account with most of this class
            for row in rows:
                acct_lower = row["accountKey"]
                class_count = class_counts.get(acct_lower, {}).get(class_code, 0)
                if class_count > max_count:
                    max_count = class_count
                    winner_acct = acct_lower

            # Only assign if someone actually has at least one character of that class.
            if winner_acct and max_count > 0:
                class_winners[full_class_name] = winner_acct

    for row in rows:
        achievements = []
        apex_set = set()
        legend_set = set()
        acct_lower = row["accountKey"]
        season_count = len(season_presence.get(acct_lower, set()))

        prestige_label = prestige_label_for_season_count(season_count)
        if prestige_label:
            achievements.append(prestige_label)

        for cond, label in BASE_ACHIEVEMENT_RULES:
            if cond(row):
                achievements.append(label)

        for tier in ACHIEVEMENT_TIERS:
            key = tier["key"]
            val = row.get(key, 0)
            mode = tier["mode"]
            threshold = tier["threshold"]
            min_chars = tier.get("min_chars", 1)

            if row["charCount"] >= min_chars:
                if mode == "min":
                    if 0 < val <= threshold:
                        achievements.append(tier["base"])
                else:
                    if val >= threshold:
                        achievements.append(tier["base"])

            winner = winners.get(key)
            if winner and winner["accountKey"] == row["accountKey"]:
                achievements.append(tier["apex"])
                apex_set.add(tier["apex"])

        for tier in LEGENDARY_ACHIEVEMENTS:
            key = tier["key"]
            winner = legendary_winners.get(key)
            if winner and winner["accountKey"] == row["accountKey"]:
                achievements.append(tier["title"])
                legend_set.add(tier["title"])
        
        # Special achievements (treat as legendary for display)
        if acct_lower in taking_a_break:
            achievements.append("Taking a Break")
        if acct_lower in breaktime_over:
            achievements.append("Breaktime's Over")
            legend_set.add("Breaktime's Over")
        if acct_lower in one_trick_pony:
            achievements.append("One Trick Pony")
            legend_set.add("One Trick Pony")
        if acct_lower in many_faces:
            achievements.append("Seasonal Sampler")
            legend_set.add("Seasonal Sampler")
        if acct_lower in stayed_a_while:
            achievements.append("Stayed a While to Listen")
            legend_set.add("Stayed a While to Listen")
        if acct_lower in baby_come_back:
            achievements.append("Baby Come Back")
        if acct_lower in afk_since:
            afk_label = f"AFK Since S{afk_since[acct_lower]}"
            achievements.append(afk_label)
        if row.get("dangoonItems", 0) > 0 or row.get("deleriumHelms", 0) > 0:
            achievements.append("Simply the Best")
            apex_set.add("Simply the Best")
        if row.get("maxMagicItems", 0) >= 3:
            achievements.append("The Blues")
        if row.get("maxRareArmor", 0) >= 1:
            achievements.append("Yellow Bellied")
        if row.get("maxRareItems", 0) >= 4:
            achievements.append("A Rare Sight")
        if row.get("maxUniqueItems", 0) >= 5:
            achievements.append("Uniquely Suited")
        if row.get("maxCraftedItems", 0) >= 4:
            achievements.append("Crafty")
        
        # Class-based achievements
        for char_class, achievement_title in class_achievements.items():
            if class_winners.get(char_class) == row["accountKey"]:
                achievements.append(achievement_title)
                legend_set.add(achievement_title)

        # Preserve order while deduplicating.
        seen = set()
        row["achievements"] = [a for a in achievements if not (a in seen or seen.add(a))]
        row["apex_achievements"] = apex_set
        row["legendary_achievements"] = legend_set


def compute_xp_breakdown(row, no_items=False):
    def scale_torch_anni_points(raw_points):
        # Keep low rolls near-linear, then ramp aggressively for high rolls.
        # Targets: 20 -> 20, 40 -> 100.
        raw = max(0, int(raw_points or 0))
        if raw <= 20:
            return raw
        return round(20 + 0.20 * ((raw - 20) ** 2))

    rank_boost = max(0, 1001 - row["bestRank"]) * 35 if row["bestRank"] > 0 else 0
    chaos      = hash32(row.get("accountKey") or row["account"]) % 500
    item_xp = 0 if no_items else (
        row["totalSockets"]  * 45
        + row["demonsBonus"]   * 8
        + row["halfFreeze"]    * 10 # was 250
        + row["runeXP"]
        + row["rainbowFacetXP"]
        + row["runewords"]     * 60
        + row["mf"]            * 1
        + row["goldFind"]      * 1
        + row["lifeLeech"]     * 5 #was 15
        + row["manaLeech"]     * 5
        + row["replenishLife"] * 10
        + row["crushingBlow"]  * 10 #was 20
        + row["deadlyStrike"]  * 10 #was 20
        + row["dmgReduced"]    * 10 #was 25
        + row["thornsValue"]   * 3
        + row["fireAbsorb"]    * 10 #was 30
        + scale_torch_anni_points(row["torchAnniXP"])
    )
    history_xp = round(
        row["totalExp"]      / 1_000_000
        + row["totalLevels"] * 90 # was 120, too high
        + row["charCount"]   ** 2 * 40
        + row["seasonCount"] ** 3 * 400 # was 1000
        + row["highLevelBonus"]
        + rank_boost
        + row["top5Count"]   * 500 # was 800
        + row["top10Count"]  * 600 #was 1500
        + row["top100Count"] * 300 # was 300
        + chaos
    )
    total_xp = round(history_xp + item_xp)
    return {
        "historyXP": history_xp,
        "currentItemXP": item_xp,
        "arbitraryXP": total_xp,
    }


ALL_TAG_KEYS = [
    "totalSockets", "demonsBonus", "halfFreeze", "jahRunes", "runeXP", "rainbowFacetXP", "runewords",
    "ethereals", "corrupted", "mf", "goldFind", "lifeLeech", "manaLeech",
    "replenishLife", "poisonRes", "coldRes", "lightRadius", "stamina",
    "crushingBlow", "deadlyStrike", "dmgReduced", "thornsValue", "thornsCount",
    "fireAbsorb", "reqReduced", "dangoonItems", "deleriumHelms",
    "torchAnniXP", "magicItems", "rareItems", "uniqueItems", "craftedItems", "rareArmor", "totalStrength",
    "maxMagicItems", "maxRareItems", "maxUniqueItems", "maxCraftedItems", "maxRareArmor",
]


def build_rows(by_account, item_tags, season_presence=None, class_counts=None, season_class_presence=None, current_season=None, no_items=False):
    class_counts = class_counts or {}
    rows = []
    for acct_lower, acc in by_account.items():
        tags = item_tags.get(acct_lower, {})
        class_count_map = {
            class_code: int(class_counts.get(acct_lower, {}).get(class_code, 0) or 0)
            for class_code in CLASS_DISPLAY_ORDER
        }
        row = {
            "account":     acc["account"],
            "accountHref": acc.get("accountHref") or acc["account"],
            "accountKey":  acct_lower,
            "isMerged":    acct_lower.startswith("merged:"),
            "charCount":   acc["charCount"],
            "totalLevels": acc["totalLevels"],
            "totalExp":    acc["totalExp"],
            "bestRank":    acc["bestRank"],
            "top5Count":   acc["top5Count"],
            "top10Count":  acc["top10Count"],
            "top100Count": acc["top100Count"],
            "charClasses": sorted(acc["charClasses"]),
            "classCounts": class_count_map,
            "seasonCount": len(season_presence.get(acct_lower, set())),
            "highLevelBonus": acc["highLevelBonus"],
        }
        for k in ALL_TAG_KEYS:
            row[k] = tags.get(k, 0)
        xp_breakdown = compute_xp_breakdown(row, no_items=no_items)
        row.update(xp_breakdown)
        rows.append(row)
    rows.sort(key=lambda r: r["arbitraryXP"], reverse=True)
    assign_cp_titles(rows)
    assign_achievements(
        rows,
        season_presence=season_presence,
        class_counts=class_counts,
        season_class_presence=season_class_presence,
        current_season=current_season,
    )
    return rows


# ── HTML generation ────────────────────────────────────────────────────────────

def fmt(n):
    return f"{int(n):,}"


def leaderboard_rows_html(rows, show_xp_breakdown=False):
    parts = []
    for i, row in enumerate(rows, 1):
        acct   = escape(row["account"])
        acct_href = escape(row.get("accountHref") or row["account"])
        merged_marker = '<span class="merged-marker" title="Merged player identity, they\'ve played multiple different accounts">*</span>' if row.get("isMerged") else ''
        cp_title = escape(row.get("cpTitle") or "Drifter")
        cp_level = int(row.get("cpLevel") or 1)
        apex = row.get("apex_achievements", set())
        legendary = row.get("legendary_achievements", set())
        class_counts = row.get("classCounts", {})
        class_pills = []
        for class_code in CLASS_DISPLAY_ORDER:
            count = int(class_counts.get(class_code, 0) or 0)
            if count <= 0:
                continue
            class_name = escape(CLASS_NAME_MAP.get(class_code, class_code.upper()))
            class_color = escape(CLASS_COLOR_MAP.get(class_code, "#d3d3d3"))
            class_icon = escape(CLASS_ICON_MAP.get(class_code, ""))
            class_pills.append(
                f'<span class="title-pill class-count-pill" title="{class_name}: {count}" style="border-color: {class_color};">'
                f'<img class="class-icon" src="{class_icon}" alt="{class_name}">'
                f'<span class="class-count" style="color: {class_color};">{count}</span>'
                f'</span>'
            )

        ach_html = " ".join(
            f'<span class="title-pill legendary">{escape(a)}</span>' if a in legendary
            else f'<span class="title-pill apex">{escape(a)}</span>' if a.startswith("Prestige")
            else f'<span class="title-pill apex">{escape(a)}</span>' if a in apex
            else f'<span class="title-pill">{escape(a)}</span>'
            for a in row.get("achievements", [])
        ) or '<span class="title-pill">Account Enjoyer</span>'
        award_html = " ".join([ach_html] + class_pills).strip()
        parts.append(f"""
            <tr>
                <td class="rank-num">{i}</td>
                <td><a href="https://beta.pathofdiablo.com/account/{acct_href}" target="_blank"><span class="cp-title" title="CP {cp_level}">{cp_title}</span> {acct}{merged_marker}</a></td>
                {'<td class="xp-cell">' + fmt(row['historyXP']) + '</td>' if show_xp_breakdown else ''}
                {'<td class="xp-cell">' + fmt(row['currentItemXP']) + '</td>' if show_xp_breakdown else ''}
                <td class="xp-cell">{fmt(row['arbitraryXP'])}</td>
                <td>{award_html}</td>
            </tr>""")
    return "\n".join(parts)


def mini_stats_html(rows, local_source, current_season):
    account_count = len(rows)
    total_chars   = sum(r["charCount"] for r in rows)
    total_xp      = sum(r["arbitraryXP"] for r in rows)
    return f"""
        <div class="mini-stat"><div class="value">{fmt(account_count)}</div><div class="label">Accounts Ranked</div></div>
        <div class="mini-stat"><div class="value">{fmt(total_chars)}</div><div class="label">Total Characters</div></div>
        <div class="mini-stat"><div class="value">{fmt(total_xp)}</div><div class="label">Total Arbitrary XP</div></div>
        <div class="mini-stat"><div class="value">All seasons</div><div class="label">XP &amp; Rank Source</div></div>
        <div class="mini-stat"><div class="value">Season {current_season}</div><div class="label">Item Tags Source</div></div>
    """


def generate_html(rows, is_hardcore, local_source, current_season, seasons, show_xp_breakdown=False):
    hc_label      = "Hardcore " if is_hardcore else ""
    hc_suffix     = " (HC)" if is_hardcore else ""
    sc_page       = "ranking.html"
    hc_page       = "hcranking.html"
    sc_hc_link    = sc_page if is_hardcore else hc_page
    sc_hc_label   = "Switch to SC" if is_hardcore else "Switch to HC"
    generated_at  = datetime.now().strftime("%Y-%m-%d %H:%M")
    season_range = f"{min(seasons)}-{max(seasons)}" if seasons else str(current_season)

    lb_rows  = leaderboard_rows_html(rows, show_xp_breakdown=show_xp_breakdown)
    mini     = mini_stats_html(rows, local_source, current_season)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Sqord's Arbitrary Path of Diablo Ranking: nonsense account XP across seasons {season_range}, tiered ranking, and weird titles presented by Sethy and Qord.">
    <title>The Order of Sanctuary {hc_suffix}</title>
    <link rel="shortcut icon" type="image/x-icon" href="icons/pod.ico">
    <style>
        @font-face {{
            font-family: 'd2';
            src: url('icons/Exocet.TTF');
        }}
        @font-face {{
            font-family: 'armory';
            src: url('armory/font/avqest.ttf');
        }}
        body {{
            margin: 20px;
            margin-top: 20px;
            line-height: 1.6;
            background-color: #0d0d0d;
            color: #a9a9a9;
            font-family: armory, sans-serif;
            font-size: large;
        }}
        .special-background {{
            background-image: url('icons/pod-logo.png');
            background-position: top 24px left 2px;
            background-repeat: no-repeat;
            background-size: 170px auto;
            background-color: black;
            padding-top: 0;
        }}
        .main {{
            max-width: 1200px;
            margin-left: 150px;
            margin-top: 0;
            position: relative;
            --main-pad-x: 30px;
            padding: 36px 30px 34px;
            background: black;
            box-shadow: inset 0 1px 4px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.7);
        }}
        .main::before {{
            content: '';
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 2;
            background:
                url('d2images/border-top-left.gif') left top no-repeat,
                url('d2images/border-top-right.gif') right top no-repeat,
                url('d2images/border-bottom-left.gif') left bottom no-repeat,
                url('d2images/border-bottom-right.gif') right bottom no-repeat,
                url('d2images/border-top-mid.gif') left top repeat-x,
                url('d2images/border-bottom.gif') left bottom repeat-x,
                url('d2images/border-left.gif') left top repeat-y,
                url('d2images/border-right.gif') right top repeat-y;
        }}
        .main > * {{
            position: relative;
            z-index: 1;
        }}
        h1 {{ color: #d3d3d3; font-family: d2, sans-serif; text-shadow: 0 0 6px rgba(0,0,0,0.9); }}
        h2, h3 {{ color: #a0a0a0; font-family: armory, sans-serif; text-shadow: 0 0 4px rgba(0,0,0,0.8); }}
        p {{ color: #a9a9a9; font-family: armory, sans-serif; }}
        a {{ color: #a0a0c0; }}
        .title-panel {{
            position: relative;
            max-width: 1200px;
            margin-left: 150px;
            margin-bottom: 0;
            padding: 18px 24px 16px;
            text-align: center;
            background: url('d2images/small-border-back.gif') center center repeat;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
        }}
        .title-panel::before {{
            content: '';
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                url('d2images/small-border-top-left.gif') left top no-repeat,
                url('d2images/small-border-top-right.gif') right top no-repeat,
                url('d2images/small-border-top.gif') left top repeat-x,
                url('d2images/small-border-bottom.gif') left bottom repeat-x,
                url('d2images/small-border-left.gif') left top repeat-y,
                url('d2images/small-border-right.gif') right top repeat-y;
        }}
        .title-panel h1 {{
            margin: 0;
            color: #f2e8d6;
            text-shadow: 0 1px 0 rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.9);
        }}
        .between-section {{
            height: 4px;
            max-width: 1200px;
            margin-left: 150px;
            background: url('d2images/in-between-back.gif') center center repeat-x;
        }}
        .qords-hero {{
            background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 50%, #2a2a2a 100%);
            border: 3px solid #555555;
            border-radius: 1px;
            padding: 20px;
            margin-bottom: 20px;
            animation: heroFade 0.7s ease-out;
            box-shadow: inset 0 0 8px rgba(0,0,0,0.9), 0 0 12px rgba(85,85,85,0.4);
        }}
        @keyframes heroFade {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .qords-subtitle {{ color: #c0c0c0; margin-top: 6px; margin-bottom: 8px; font-style: italic; }}
        .mode-toggle {{
            display:inline-flex; gap:2px; margin: 8px 0 14px;
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 2px solid #404040;
            border-radius: 0;
            padding: 2px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.9);
        }}
        .mode-toggle .mode-link {{
            display:inline-block; text-decoration:none; color:#808080;
            border: 1px solid #303030;
            border-radius: 0;
            padding: 6px 14px; font-size: 12px; letter-spacing: 0.3px;
            background: linear-gradient(to bottom, #1a1a1a, #0d0d0d);
        }}
        .mode-toggle .mode-link:hover {{ background: linear-gradient(to bottom, #2a2a2a, #1a1a1a); color: #d3d3d3; }}
        .mode-toggle .mode-link.active {{
            background: linear-gradient(to bottom, #4a4a4a, #303030);
            border-color: #555555;
            color: #e8e8e8;
            font-weight: bold;
            box-shadow: inset 0 1px 2px rgba(232,232,232,0.2);
        }}
        .controls {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin-top:10px; }}
        .controls input, .controls select, .controls button {{
            background: linear-gradient(to bottom, #1a1a1a, #0d0d0d);
            color: #a0a0a0;
            border: 2px solid #404040;
            border-radius: 0;
            padding: 8px 10px;
            font-family: armory, sans-serif;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.8);
        }}
        .controls button {{
            cursor: pointer;
            background: linear-gradient(to bottom, #303030, #1a1a1a);
            border-color: #404040;
        }}
        .controls button:hover {{
            background: linear-gradient(to bottom, #4a4a4a, #303030);
            color: #d3d3d3;
        }}
        .info-box {{
            background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
            border: 2px solid #404040;
            border-left: 4px solid #555555;
            border-radius: 0;
            padding: 12px 14px;
            color: #a0a0a0;
            margin-bottom: 16px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.8);
        }}
        .info-box strong {{ color: #d3d3d3; }}
        .mini-stats {{
            display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
            gap:10px; margin:14px 0;
        }}
        .mini-stat {{
            border: 2px solid #404040;
            border-radius: 0;
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            padding: 12px;
            text-align: center;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.9), 0 2px 4px rgba(0,0,0,0.6);
        }}
        .mini-stat .value {{ color: #c0c0c0; font-family: d2, sans-serif; font-size: 22px; text-shadow: 0 0 4px rgba(0,0,0,0.8); }}
        .mini-stat .label {{ color: #808080; font-size: 12px; }}
        .table-wrap {{
            overflow-x: auto;
            border: 2px solid #404040;
            border-radius: 0;
            background: #0d0d0d;
            margin-bottom: 75px;
            box-shadow: inset 0 1px 4px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.7);
        }}
        table.rank-table {{ width:100%; border-collapse:collapse; min-width:1080px; }}
        .rank-table th, .rank-table td {{ padding: 9px; border-bottom: 1px solid #303030; text-align: left; color: #a0a0a0; font-size: 14px; }}
        .rank-table th {{
            position: sticky;
            top: 0;
            background: linear-gradient(to bottom, #303030, #1a1a1a);
            color: #d3d3d3;
            z-index: 1;
            font-weight: bold;
            border-bottom: 2px solid #404040;
        }}
        .rank-table tr:hover {{ background: linear-gradient(to right, rgba(85,85,85,0.15), transparent); }}
        .rank-num {{ font-weight: bold; color: #a0a0a0; }}
        .cp-title {{ color: #909090; font-weight: bold; margin-right: 4px; text-shadow: 0 0 3px rgba(0,0,0,0.8); }}
        .xp-cell {{ color: #d3d3d3; font-family: d2, sans-serif; letter-spacing: 0.4px; }}
        .title-pill {{
            display: inline-block;
            border: 1px solid #555555;
            border-radius: 1px;
            padding: 3px 8px;
            background: linear-gradient(to bottom, #3a3a2a, #202010);
            font-size: 14px;
            color: #d3d3d3;
            margin: 2px 4px 2px 0;
            white-space: nowrap;
            font-weight: bold;
            box-shadow: inset 0 1px 3px rgba(85,85,85,0.5);
        }}
        .title-pill.class-count-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 2px 6px 2px 4px;
            background: linear-gradient(to bottom, #1f1f1f, #121212);
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.85);
        }}
        .title-pill.class-count-pill .class-icon {{
            width: 14px;
            height: 14px;
            object-fit: cover;
            border: 1px solid rgba(0,0,0,0.55);
        }}
        .title-pill.class-count-pill .class-count {{
            font-family: d2, sans-serif;
            font-size: 13px;
            letter-spacing: 0.3px;
            text-shadow: none;
        }}
        .title-pill.apex {{
            border-color: #8d63d6;
            background: #25173b;
            color: #d7c2ff;
            font-weight: bold;
            box-shadow: 0 0 6px rgba(141,99,214,0.35);
        }}
        .title-pill.legendary {{
            border-color: #c8922a;
            background: #2e2010;
            color: #ffcc66;
            font-weight: bold;
            box-shadow: 0 0 7px rgba(200,146,42,0.38);
        }}
        .status {{ color: #a9a9a9; margin:6px 0 14px; }}
        .section-break {{
            height: 50px;
            margin: 22px 0 24px;
            margin-left: calc(-1 * var(--main-pad-x) + 20px);
            margin-right: calc(-1 * var(--main-pad-x) + 20px);
            display: flex;
            align-items: center;
            justify-content: center;
            background:
                url('d2images/break-left.gif') left center no-repeat,
                url('d2images/break-right.gif') right center no-repeat,
                url('d2images/break-mid.gif') center center repeat-x;
        }}
        .section-break span {{
            padding: 0 10px;
            color: #f2e8d6;
            font-family: armory, sans-serif;
            font-size: 1.17em;
            letter-spacing: 0.4px;
            text-shadow: 0 1px 0 rgba(0,0,0,0.95), 0 0 6px rgba(0,0,0,0.9);
        }}
        h3 {{
            height: 50px;
            margin: 0;
            margin-top: 10px;
            margin-bottom: 20px;
            margin-left: calc(-1 * var(--main-pad-x) + 20px);
            margin-right: calc(-1 * var(--main-pad-x) + 20px);
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #f2e8d6;
            text-shadow: 0 1px 0 rgba(0,0,0,0.95), 0 0 6px rgba(0,0,0,0.9);
            background:
                url('d2images/break-left.gif') left top no-repeat,
                url('d2images/break-right.gif') right top no-repeat,
                url('d2images/break-mid.gif') center top repeat-x;
        }}
        .generated-note {{ color: #666; font-size:12px; margin-top:4px; }}
        .merged-marker {{
            color: #ffcc66;
            margin-left: 3px;
            font-weight: bold;
            text-shadow: 0 0 4px rgba(200,146,42,0.55);
            cursor: help;
        }}
        .back-to-top {{
            position: fixed;
            right: 16px;
            bottom: 16px;
            width: 42px;
            height: 42px;
            display: none;
            border: 2px solid #404040;
            border-radius: 1px;
            background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
            color: #a0a0a0;
            cursor: pointer;
            z-index: 10;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.8);
        }}
        .back-to-top::before {{ content: '\u2191'; font-size: 18px; line-height: 1; }}
        .back-to-top:hover {{ background: linear-gradient(135deg, #303030, #2a2a2a); color: #d3d3d3; }}
        .about-wrap {{
            display: flex;
            justify-content: center;
            margin: 0 0 28px;
            position: relative;
            z-index: 3;
        }}
        .about-btn {{
            border: 2px solid #404040;
            border-radius: 1px;
            background: linear-gradient(to bottom, #2a2a2a, #1a1a1a);
            color: #d3d3d3;
            font-family: armory, sans-serif;
            font-size: 14px;
            letter-spacing: 0.5px;
            padding: 8px 18px;
            cursor: pointer;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.85), 0 0 6px rgba(0,0,0,0.5);
        }}
        .about-btn:hover {{
            background: linear-gradient(to bottom, #3a3a3a, #242424);
            color: #f2e8d6;
        }}
        .about-modal {{
            display: none;
            position: fixed;
            inset: 0;
            z-index: 1000;
            background: rgba(0, 0, 0, 0.72);
            align-items: center;
            justify-content: center;
            padding: 18px;
        }}
        .about-modal.open {{
            display: flex;
        }}
        .about-dialog {{
            width: min(760px, 100%);
            max-height: 80vh;
            overflow-y: auto;
            border: 2px solid #404040;
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.9), 0 0 18px rgba(0,0,0,0.8);
            padding: 18px 20px 16px;
        }}
        .about-dialog h4 {{
            margin: 0 0 12px;
            color: #f2e8d6;
            font-family: d2, sans-serif;
            font-size: 18px;
        }}
        .about-dialog p {{
            margin: 0 0 12px;
            color: #c0c0c0;
        }}
        .about-dialog .about-close {{
            margin-top: 6px;
            border: 2px solid #404040;
            background: linear-gradient(to bottom, #2a2a2a, #1a1a1a);
            color: #d3d3d3;
            font-family: armory, sans-serif;
            padding: 7px 16px;
            cursor: pointer;
        }}
        .about-dialog .about-close:hover {{
            background: linear-gradient(to bottom, #3a3a3a, #242424);
            color: #f2e8d6;
        }}
        @media (max-width: 768px) {{
            body {{ margin: 10px; font-size: medium; }}
            .special-background {{
                background-size: 200px auto;
                background-position: top 8px right 8px;
            }}
            .main {{
                margin-left: 0 !important;
                margin-right: 0;
                --main-pad-x: 16px;
                padding: 24px 16px 22px;
            }}
            .title-panel {{
                margin-left: 0;
                margin-right: 0;
                padding: 16px 18px 14px;
            }}
            .between-section {{
                margin-left: 0;
                margin-right: 0;
                height: 28px;
            }}
            .about-wrap {{
                margin-bottom: 22px;
            }}
            .page-intro {{ padding-top: 8px; }}
        }}
    </style>
</head>
<body class="special-background">
<div class="is-clipped">
    <div class="title-panel">
        <h1>The Order of Sanctuary {hc_label}</h1>
    </div>

    <div class="between-section"></div>

    <div class="main page-intro">
        <div class="qords-hero">
            <p class="qords-subtitle">Infinite points. No goal. Dubious XP. Highly scientific nonsense.</p>
            <div class="mode-toggle" aria-label="Ladder mode toggle">
                <a class="mode-link {'active' if not is_hardcore else ''}" href="{sc_page}">Softcore</a>
                <a class="mode-link {'active' if is_hardcore else ''}" href="{hc_page}">Hardcore</a>
            </div>
            <div class="controls">
                <label for="rowLimit">Show top</label>
                <select id="rowLimit">
                    <option value="25">25</option>
                    <option value="50" selected>50</option>
                    <option value="100">100</option>
                    <option value="500">500</option>
                    <option value="1000">1000</option>
                    <option value="5000">5000</option>
                    <option value="99999">All</option>
                </select>
                <label for="accountFilter">Account contains</label>
                <input id="accountFilter" type="text" placeholder="type account name">
            </div>
        </div>

        <div class="section-break"><span>How this works</span></div>

        <div class="info-box">
            XP is a made-up score aggregated across <em>seasons {season_range}</em>
            (rank, level, character count), with a boost from equipment worn by current ladder characters. 
            XP will rise and fall across seasons as accounts come and go, and as characters equip and unequip items.
            Rankings are tied to both accounts across seasons and equipment
            current ladder characters are using. Some rankings will follow you through seasons, and others will
            change with the times. This page is intentionally unserious.
<!--            Accounts marked with <strong>*</strong> represent merged player identities spanning multiple configured accounts. -->
        </div>

        <p class="status">Generated {generated_at} &nbsp;·&nbsp; XP from <em>seasons {season_range}</em> &nbsp;·&nbsp; Item tags from current ladder characters</p>

        <div class="mini-stats">{mini}</div>

        <h3>Tome of Accomplishments</h3>
        <div class="table-wrap">
            <table class="rank-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Account</th>
                        {'<th>History XP</th>' if show_xp_breakdown else ''}
                        {'<th>Current Item XP</th>' if show_xp_breakdown else ''}
                        <th>Arbitrary XP</th>
                        <th>Ranking</th>
                    </tr>
                </thead>
                <tbody id="leaderboardBody">
{lb_rows}
                </tbody>
            </table>
        </div>

        <div class="about-wrap">
            <button class="about-btn" onclick="showAboutPopup()">About</button>
        </div>

        <div id="aboutModal" class="about-modal" onclick="hideAboutPopup(event)">
            <div class="about-dialog" onclick="event.stopPropagation()">
                <h4>About</h4>
                <p>Built on the back of the Trends reporting site and the data analysis it allows, the aim of this is to look at entire accounts, both in current form and over time, and credit players for their work beyond the right now. This takes into account ladder participation, ranking, character and level count, and experience from seasons {season_range}, then adds XP points based on what current ladder season characters have equipped.</p>
                <p>Rankings are primarily for entertainment value, and as such many of them will rotate with the seasons. Some will get removed, and others will get added. Some are character specific and others are based on data over time. There are rankings for appearing on the ladder ranks over time, as well as rankings based on item properties of currently worn equipment. The source of some rankings is obvious, and others will take some time to figure out. </p>
                <p>For players who return to the ladder ranks over and over, your participation is reflected in both your XP and prestige level.</p>
                <p>Please direct any feedback or suggestions to Sethy or Qord.</p>
                <button class="about-close" onclick="hideAboutPopup()">Close</button>
            </div>
        </div>

        <button onclick="topFunction()" id="backToTopBtn" class="back-to-top"></button>
    </div>
</div>

<script>
// All rows pre-computed; JS only handles client-side filtering/display
const ALL_ROWS = document.querySelectorAll("#leaderboardBody tr");

function applyFilter() {{
    const limit      = parseInt(document.getElementById("rowLimit").value) || 50;
    const filterText = document.getElementById("accountFilter").value.toLowerCase().trim();
    let shown = 0;
    ALL_ROWS.forEach(tr => {{
        const acct = tr.cells[1] ? tr.cells[1].textContent.toLowerCase() : "";
        const matches = !filterText || acct.includes(filterText);
        const underLimit = shown < limit;
        if (matches && underLimit) {{
            tr.style.display = "";
            shown++;
            tr.cells[0].textContent = shown;  // renumber
        }} else {{
            tr.style.display = "none";
        }}
    }});
}}

document.getElementById("rowLimit").addEventListener("change", applyFilter);
document.getElementById("accountFilter").addEventListener("input", applyFilter);
applyFilter();

var backToTopBtn = document.getElementById("backToTopBtn");
window.onscroll = function() {{
    backToTopBtn.style.display = (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) ? "block" : "none";
}};
function topFunction() {{ document.body.scrollTop = 0; document.documentElement.scrollTop = 0; }}
function showAboutPopup() {{ document.getElementById("aboutModal").classList.add("open"); }}
function hideAboutPopup(event) {{
    if (!event || event.target.id === "aboutModal") {{
        document.getElementById("aboutModal").classList.remove("open");
    }}
}}
document.addEventListener("keydown", function(event) {{
    if (event.key === "Escape") {{
        document.getElementById("aboutModal").classList.remove("open");
    }}
}});

function toggleMenu() {{ document.querySelector(".top-buttons").classList.toggle("show"); }}
function setActive(n) {{ console.log("active", n); }}
</script>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def generate(mode_label, mode_int, json_candidates, out_filename, seasons_override=None, no_items=False, show_xp_breakdown=False):
    print(f"\n{'='*60}")
    print(f"Generating {mode_label} ranking → {out_filename}")
    print(f"{'='*60}")

    current_season = fetch_current_season()
    if seasons_override is not None:
        seasons = seasons_override
    else:
        seasons = list(range(1, current_season + 1))
    print(f"Current season: {current_season}  |  Fetching seasons: {seasons}  |  no_items={no_items}  |  show_xp_breakdown={show_xp_breakdown}")

    print("\n[1/3] Fetching all-season ladder data …")
    by_account, char_to_acct, season_presence, class_counts, season_class_presence = build_all_season_stats(mode_int, seasons)
    print(f"  → {len(by_account)} accounts, {len(char_to_acct)} chars mapped")

    print("\n[2/3] Loading current-season item data …")
    local_chars, local_source = load_first_existing(json_candidates)
    item_tags = build_item_tags_by_account(local_chars, char_to_acct)

    print("\n[3/3] Computing scores and generating HTML …")
    rows = build_rows(
        by_account,
        item_tags,
        season_presence=season_presence,
        class_counts=class_counts,
        season_class_presence=season_class_presence,
        current_season=current_season,
        no_items=no_items,
    )
    print(f"  → {len(rows)} accounts ranked")

    html = generate_html(rows, is_hardcore=(mode_int == 1),
                         local_source=local_source, current_season=current_season, seasons=seasons,
                         show_xp_breakdown=show_xp_breakdown)

    out_path = BASE_DIR / out_filename
    out_path.write_text(html, encoding="utf-8")
    print(f"  → Wrote {out_path}")


if __name__ == "__main__":
    generate("SC", 0, SC_JSON_CANDIDATES, "ranking.html")
    generate("HC", 1, HC_JSON_CANDIDATES, "hcranking.html")
    generate("SC (with XP breakdown)", 0, SC_JSON_CANDIDATES, "ranking-xp-breakdown.html", show_xp_breakdown=True)
    generate("HC (with XP breakdown)", 1, HC_JSON_CANDIDATES, "hcranking-xp-breakdown.html", show_xp_breakdown=True)
    generate("SC (no items)",  0, SC_JSON_CANDIDATES, "ranking-noitems.html",    no_items=True)
    generate("HC (no items)",  1, HC_JSON_CANDIDATES, "hcranking-noitems.html",    no_items=True)
#    generate("SC (S13 only)",  0, SC_JSON_CANDIDATES, "ranking-s13.html",        seasons_override=[13])
#    generate("SC (S13 no items)", 0, SC_JSON_CANDIDATES, "ranking-s13-noitems.html", seasons_override=[13], no_items=True)
    print("\nDone.")
