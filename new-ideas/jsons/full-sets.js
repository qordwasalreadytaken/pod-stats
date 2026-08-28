
        // Set items data - organized by level/tier 
        const highLevelSets = [
            // Immortal King's (Barbarian)
            { name: "Immortal King's Will", code: "ba5", set: "IK", base: "Avenger Guard", req_level:47, req_strength:65 },
            { name: "Immortal King's Soul Cage", code: "uar", set: "IK", base: "Sacred Armor" },
            { name: "Immortal King's Detail", code: "zhb", set: "IK", base: "War Belt" },
            { name: "Immortal King's Forge", code: "xhg", set: "IK", base: "War Gauntlets" },
            { name: "Immortal King's Pillar", code: "xhb", set: "IK", base: "War Boots" },
            { name: "Immortal King's Stone Crusher", code: "7m7", set: "IK", base:"Ogre Maul" },
            // Tal Rasha's (Sorceress)
            { name: "Tal Rasha's Horadric Crest", code: "xsk", set: "TR", base: "Death Mask" },
            { name: "Tal Rasha's Guardianship", code: "uth", set: "TR", base: "Lacquered Plate" },
            { name: "Tal Rasha's Fine-Spun Cloth", code: "zmb", set: "TR", base: "Mesh Belt" },
            { name: "Tal Rasha's Lidless Eye", code: "oba", set: "TR", base: "Swirling Crystal" },
            { name: "Tal Rasha's Adjudication", code: "amu", set: "TR" },
            // Griswold's (Paladin)
            { name: "Griswold's Valor", code: "urn", set: "Gris", base: "Corona" },
            { name: "Griswold's Heart", code: "xar", set: "Gris", base: "Ornate Plate" },
            { name: "Griswold's Redemption", code: "7ws", set: "Gris", base: "Caduceus" },
            { name: "Griswold's Honor", code: "paf", set: "Gris", base: "Vortex Shield" },
            // Trang-Oul's (Necromancer)
            { name: "Trang-Oul's Guise", code: "uh9", set: "TO", base: "Bone Visage" },
            { name: "Trang-Oul's Scales", code: "xul", set: "TO", base: "Chaos Armor" },
            { name: "Trang-Oul's Wing", code: "ne9", set: "TO", base: "Cantor Trophy" },
            { name: "Trang-Oul's Claws", code: "xmg", set: "TO", base: "Heavy Bracers" },
            { name: "Trang-Oul's Girth", code: "utc", set: "TO", base: "Troll Belt" },
            // M'avina's (Amazon)
            { name: "M'avina's True Sight", code: "ci3", set: "Mav", base: "Diadem" },
            { name: "M'avina's Embrace", code: "uld", set: "Mav", base: "Kraken Shell" },
            { name: "M'avina's Icy Clutch", code: "xtg", set: "Mav", base: "Battle Gauntlets" },
            { name: "M'avina's Tenet", code: "zvb", set: "Mav", base: "Sharkskin Belt" },
            { name: "M'avina's Caster", code: "amc", set: "Mav", base: "Grand Matron Bow" },
            // Natalya's (Assassin)
            { name: "Natalya's Totem", code: "xh9", set: "Nat", base: "Grim Helm" },
            { name: "Natalya's Shadow", code: "ucl", set: "Nat", base: "Loricated Mail" },
            { name: "Natalya's Mark", code: "7qr", set: "Nat", base: "Scissors Suwayyah" },
            { name: "Natalya's Soul", code: "xmb", set: "Nat", base: "Mesh Boots" },
            // Aldur's (Druid)
            { name: "Aldur's Stony Gaze", code: "dr8", set: "Ald", base: "Hunter's Guise" },
            { name: "Aldur's Deception", code: "uul", set: "Ald", base: "Shadow Plate" },
            { name: "Aldur's Rhythm", code: "9mt", set: "Ald", base: "Jagged Star" },
            { name: "Aldur's Advance", code: "xtb", set: "Ald", base: "Battle Boots" },
            // The Disciple
            { name: "Laying of Hands", code: "ulg", set: "Disciple", base: "Bramble Mitts" },
            { name: "Rite of Passage", code: "xlb", set: "Disciple", base: "Demonhide Boots" },
            { name: "Dark Adherent", code: "uui", set: "Disciple", base: "Dusk Shroud" },
            { name: "Credendum", code: "umc", set: "Disciple", base: "Mithril Coil" },
            { name: "Telling of Beads", code: "amu", set: "Disciple" },
            // Sazabi's
            { name: "Sazabi's Mental Sheath", code: "xhl", set: "Sazabi", base: "Basinet" },
            { name: "Sazabi's Ghost Liberator", code: "upl", set: "Sazabi", base: "Balrog Skin" },
            { name: "Sazabi's Cobalt Redeemer", code: "7ls", set: "Sazabi", base: "Cryptic Sword" },
            // Bul-Kathos'
            { name: "Bul-Kathos' Sacred Charge", code: "7gd", set: "BK", base: "Colossus Blade" },
            { name: "Bul-Kathos' Tribal Guardian", code: "7wd", set: "BK", base: "Mythical Sword" },
       ];

        const midLevelSets = [
            // Hwanin's Majesty
            { name: "Hwanin's Splendor", code: "xrn", set: "Hwanin", base: "Grand Crown" },
            { name: "Hwanin's Refuge", code: "xcl", set: "Hwanin", base: "Tigulated Mail" },
            { name: "Hwanin's Blessing", code: "mbl", set: "Hwanin", base: "Belt" },
            { name: "Hwanin's Justice", code: "9vo", set: "Hwanin", base: "Bill" },
            // Naj's Ancient Vestige
            { name: "Naj's Circlet", code: "ci0", set: "Naj", base: "Circlet" },
            { name: "Naj's Light Plate", code: "ult", set: "Naj", base: "Hellforge Plate" },
            { name: "Naj's Puzzler", code: "6cs", set: "Naj", base: "Elder Staff" },
            // Orphan's Call
            { name: "Guillaume's Face", code: "xhm", set: "Orphan", base: "Winged Helm" },
            { name: "Whitstan's Guard", code: "xml", set: "Orphan", base: "Round Shield" },
            { name: "Magnus' Skin", code: "xvg", set: "Orphan", base: "Sharkskin Gloves" },
            { name: "Wilhelm's Pride", code: "ztb", set: "Orphan", base: "Battle Belt" },
            // Sander's Folly
            { name: "Sander's Paragon", code: "cap", set: "Sander", base: "Cap" },
            { name: "Sander's Riprap", code: "vbt", set: "Sander", base: "Heavy Boots" },
            { name: "Sander's Taboo", code: "vgl", set: "Sander", base: "Heavy Gloves" },
            { name: "Sander's Superstition", code: "bwn", set: "Sander", base: "Bone Wand" },
            // Cow King's Leathers
            { name: "Cow King's Horns", code: "xap", set: "Cow", base: "War Hat" },
            { name: "Cow King's Hide", code: "stu", set: "Cow", base: "Studded Leather" },
            { name: "Cow King's Hooves", code: "vbt", set: "Cow", base: "Heavy Boots" },
            // Heaven's Brethren
            { name: "Dangoon's Teaching", code: "7ma", set: "Brethren", base: "Reinforced Mace" },
            { name: "Taebaek's Glory", code: "uts", set: "Brethren", base: "Ward" },
            { name: "Haemosu's Adamant", code: "xrs", set: "Brethren", base: "Cuirass" },
            { name: "Ondal's Almighty", code: "xrn", set: "Brethren", base: "Spired Helm" },
        ];

        const lowLevelSets = [
            // Angelic Raiment
            { name: "Angelic Halo", code: "rin", set: "Angelic" },
            { name: "Angelic Wings", code: "amu", set: "Angelic" },
            { name: "Angelic Sickle", code: "sbr", set: "Angelic", base: "Saber" },
            { name: "Angelic Mantle", code: "rng", set: "Angelic", base: "Ring Mail" },
            // Arcanna's Tricks
            { name: "Arcanna's Head", code: "skp", set: "Arcanna", base: "Skull Cap" },
            { name: "Arcanna's Flesh", code: "ltp", set: "Arcanna", base: "Light Plate" },
            { name: "Arcanna's Deathwand", code: "wnd", set: "Arcanna", base: "Wand" },
            { name: "Arcanna's Sign", code: "amu", set: "Arcanna" },
            // Arctic Gear
            { name: "Arctic Horn", code: "swb", set: "Arctic", base: "Short War Bow" },
            { name: "Arctic Furs", code: "qui", set: "Arctic", base: "Quilted Armor" },
            { name: "Arctic Binding", code: "lbl", set: "Arctic", base: "Light Belt" },
            { name: "Arctic Mitts", code: "tgl", set: "Arctic", base: "Light Gauntlets" },
            // Berserker's Arsenal
            { name: "Berserker's Headgear", code: "hlm", set: "Berserker", base: "Helm" },
            { name: "Berserker's Hauberk", code: "spl", set: "Berserker", base: "Splint Mail" },
            { name: "Berserker's Hatchet", code: "2ax", set: "Berserker", base: "Double Axe" },
            // Cathan's Traps
            { name: "Cathan's Visage", code: "msk", set: "Cathan", base: "Mask" },
            { name: "Cathan's Mesh", code: "chn", set: "Cathan", base: "Chain Mail" },
            { name: "Cathan's Rule", code: "bst", set: "Cathan", base: "Battle Staff" },
            { name: "Cathan's Sigil", code: "amu", set: "Cathan" },
            { name: "Cathan's Seal", code: "rin", set: "Cathan" },
            // Civerb's Vestments
            { name: "Civerb's Cudgel", code: "gsc", set: "Civerb", base: "Grand Scepter" },
            { name: "Civerb's Icon", code: "amu", set: "Civerb" },
            { name: "Civerb's Ward", code: "lrg", set: "Civerb", base: "Large Shield" },
            // Cleglaw's Brace
            { name: "Cleglaw's Tooth", code: "lsd", set: "Cleglaw", base: "Long Sword" },
            { name: "Cleglaw's Claw", code: "sml", set: "Cleglaw", base: "Small Shield" },
            { name: "Cleglaw's Pincers", code: "mgl", set: "Cleglaw", base: "Chain Gloves" },
            // Death's Disguise
            { name: "Death's Touch", code: "lsd", set: "Death", base: "Long Sword" },
            { name: "Death's Guard", code: "lbl", set: "Death", base: "Sash" },
            { name: "Death's Hand", code: "lgl", set: "Death", base: "Leather Gloves" },
            // Hsarus' Defense
            { name: "Hsarus' Iron Heel", code: "mbt", set: "Hsarus", base: "Chain Boots" },
            { name: "Hsarus' Iron Fist", code: "buc", set: "Hsarus", base: "Buckler" },
            { name: "Hsarus' Iron Stay", code: "lbl", set: "Hsarus", base: "Belt" },
            // Infernal Tools
            { name: "Infernal Cranium", code: "cap", set: "Infernal", base: "Cap" },
            { name: "Infernal Torch", code: "gwn", set: "Infernal", base: "Grim Wand" },
            { name: "Infernal Sign", code: "tbl", set: "Infernal", base: "Heavy Belt" },
            // Iratha's Finery
            { name: "Iratha's Coil", code: "crn", set: "Iratha", base: "Crown" },
            { name: "Iratha's Cuff", code: "tgl", set: "Iratha", base: "Light Gauntlets" },
            { name: "Iratha's Cord", code: "tbl", set: "Iratha", base: "Heavy Belt" },
            { name: "Iratha's Collar", code: "amu", set: "Iratha" },
            // Isenhart's Armory
            { name: "Isenhart's Horns", code: "fhl", set: "Isenhart", base: "Full Helm" },
            { name: "Isenhart's Case", code: "brs", set: "Isenhart", base: "Breast Plate" },
            { name: "Isenhart's Parry", code: "gts", set: "Isenhart", base: "Gothic Shield" },
            { name: "Isenhart's Lightbrand", code: "bsd", set: "Isenhart", base: "Broad Sword" },
            // Milabrega's Regalia
            { name: "Milabrega's Diadem", code: "crn", set: "Milabrega", base: "Crown" },
            { name: "Milabrega's Robe", code: "aar", set: "Milabrega", base: "Ancient Armor" },
            { name: "Milabrega's Orb", code: "kit", set: "Milabrega", base: "Kite Shield" },
            { name: "Milabrega's Rod", code: "wsp", set: "Milabrega", base: "War Scepter" },
            // Sigon's Complete Steel
            { name: "Sigon's Visor", code: "ghm", set: "Sigon", base: "Great Helm" },
            { name: "Sigon's Shelter", code: "gth", set: "Sigon", base: "Gothic Plate" },
            { name: "Sigon's Guard", code: "tow", set: "Sigon", base: "Tower Shield" },
            { name: "Sigon's Gage", code: "hgl", set: "Sigon", base: "Gauntlets" },
            { name: "Sigon's Sabot", code: "hbt", set: "Sigon", base: "Greaves" },
            { name: "Sigon's Wrap", code: "hbl", set: "Sigon", base: "Plated Belt" },
            // Tancred's Battlegear
            { name: "Tancred's Skull", code: "bhm", set: "Tancred", base: "Bone Helm" },
            { name: "Tancred's Spine", code: "ful", set: "Tancred", base: "Full Plate Mail" },
            { name: "Tancred's Hobnails", code: "lbt", set: "Tancred", base: "Boots" },
            { name: "Tancred's Weird", code: "amu", set: "Tancred" },
            { name: "Tancred's Crowbill", code: "mpi", set: "Tancred", base: "Military Pick" },
            // Vidala's Rig
            { name: "Vidala's Snare", code: "amu", set: "Vidala" },
            { name: "Vidala's Fetlock", code: "tbt", set: "Vidala", base: "Light Plated Boots" },
            { name: "Vidala's Barb", code: "lbb", set: "Vidala", base: "Long Battle Bow" },
            { name: "Vidala's Ambush", code: "lea", set: "Vidala", base: "Leather Armor" },
        ];


