# Qord's Arbitrary XP: Complete Calculation Breakdown

This document describes exactly how Arbitrary XP is calculated in the current generator.

Source of truth:
- generate_qords_ranking.py

## 1) Data Scope

Arbitrary XP uses:
- All ladder seasons from 1 through current season (unless a manual override is passed).
- Current-season local ladder JSON for item-based bonuses.

## 2) Account Aggregation

If account merge groups are configured, listed account names are merged into one canonical identity before scoring.

That means all of the following are summed on the merged identity:
- Experience
- Level totals
- Character counts
- Rank achievements
- Season presence
- Item-derived tags

## 3) Full XP Formula

Total Arbitrary XP is:

Arbitrary XP =
  round(
    totalExp / 1,000,000
    + totalLevels * 90
    + (charCount^2) * 40
    + (seasonCount^3) * 400
    + highLevelBonus
    + rankBoost
    + top5Count * 500
    + top10Count * 600
    + top100Count * 300
    + itemXP
    + chaos
  )

Where:
- totalExp: sum of character experience across all included seasons.
- totalLevels: sum of character levels across all included seasons.
- charCount: total unique characters after per-season de-duplication.
- seasonCount: number of distinct seasons where account appears.
- highLevelBonus: for each character, max(0, min(level, 99) - 90) * 100, then summed.
- rankBoost: if bestRank > 0, (1001 - bestRank) * 35, else 0.
- top5Count: number of character entries with rank <= 5.
- top10Count: number of character entries with rank <= 10.
- top100Count: number of character entries with rank <= 100.
- itemXP: current-season equipment score (detailed below).
- chaos: deterministic account hash % 500 (integer 0..499).

Important overlap note:
- A rank 3 character increments top5Count, top10Count, and top100Count.

## 4) Item XP (Current-Season Twist)

Item XP is only from current-season character equipment data loaded from local JSON.

itemXP =
  totalSockets * 45
  + demonsBonus * 8
  + halfFreeze * 10
  + runeXP
  + rainbowFacetXP
  + runewords * 60
  + mf * 1
  + goldFind * 1
  + lifeLeech * 5
  + manaLeech * 5
  + replenishLife * 10
  + crushingBlow * 10
  + deadlyStrike * 10
  + dmgReduced * 10
  + thornsValue * 3
  + fireAbsorb * 10
  + scaledTorchAnniXP

If no-items mode is enabled, itemXP is forced to 0.

### Item Term Definitions

- totalSockets: summed socket counts across equipped items (including nested sockets).
- demonsBonus: summed % Damage to Demons values.
- halfFreeze: count of Half Freeze Duration property occurrences.
- runeXP: rune-weight score from base item rune titles and RuneTag content.
- rainbowFacetXP: custom facet score using rolls and element multipliers.
- runewords: count of equipped items with q_runeword quality.
- mf: total Magic Find from character Bonus block.
- goldFind: total Gold Find from character Bonus block.
- lifeLeech: summed % life stolen per hit.
- manaLeech: summed % mana stolen per hit.
- replenishLife: summed Replenish Life values.
- crushingBlow: summed % crushing blow.
- deadlyStrike: summed % deadly strike.
- dmgReduced: summed physical reduction terms (% and flat parsed forms).
- thornsValue: summed Attacker Takes Damage Of values.
- fireAbsorb: summed Fire Absorb values.
- scaledTorchAnniXP: scaled value from Torch/Anni parsing (below).

## 5) Rune XP Weights

runeXP uses these weights:
- Jah: 300
- Ber: 200
- Zod: 100
- Cham: 100
- Sur: 100
- Vex: 50
- Mal: 25
- Ist: 25

Weights apply to:
- Standalone rune items (title match).
- RuneTag string occurrences (for runewords/socket content encoding).

## 6) Rainbow Facet XP

Facet base roll score:
- 3 roll: 60
- 4 roll: 100
- 5 roll: 160

Facet score uses both:
- Enemy resistance roll
- Increased damage roll

Rolls are clamped to 3..5, then:
- base = score(enemyRoll) + score(damageRoll)
- final = round(base * elementMultiplier)

Element multipliers:
- physical: 1.60
- magic: 1.50
- lightning: 1.25
- fire: 1.15
- cold: 1.15
- poison: 1.15
- unknown/default: 1.00

## 7) Torch + Anni Parsing and Scaling

Raw torch/anni points are built from charm-area unique charms in inventory rows y=5..8:

- Hellfire Torch (detected by +3 class skills):
  raw += allAttributes + allResistances

- Annihilus (detected by +1 all skills and Experience Gained):
  raw += allAttributes + allResistances + experienceGained

Then scaled:
- If raw <= 20: scaled = raw
- If raw > 20: scaled = round(20 + 0.20 * (raw - 20)^2)

Examples:
- raw 20 -> 20
- raw 30 -> 40
- raw 40 -> 100

## 8) What Does Not Affect XP

Achievements and title labels do not directly add XP.
They are display/recognition systems separate from the numeric Arbitrary XP formula.

## 9) Practical Reading Guide for Community

You can think of total score as:
- Lifetime backbone:
  experience, level totals, char count growth, season longevity, rank history
- Current-season momentum:
  itemXP (including torch/anni and facets)
- Tiny deterministic jitter:
  chaos (0..499)

This is why active gearing right now still matters, even when all historical seasons are included.
