"""Palette, materials and colour parsing. Material ids match web/src/meta.ts MAT (the ids are warsaw-vibe-voxel's, MIT,
© 2026 Piotr Migdał; parse_colour and the ground palette are taken from its scripts/voxelize.py)."""
import colorsys
import hashlib
import re

import webcolors

SOLID, WALL, GLASS, LEAF, WATER, LAMP, METAL, PKIN, GRASS, MARK, SOIL, CAR, ROOF, CONCRETE = range(14)
CLASSIC, TENEMENT = 20, 22


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Palette:
    def __init__(self):
        self.entries = [(0, 0, 0, 0)]
        self.index = {}

    def __call__(self, rgb, mat=SOLID, q=4):
        if isinstance(rgb, str):
            rgb = hex_rgb(rgb)
        r, g, b = (min(255, int(round(v / q)) * q) for v in rgb)
        key = (r, g, b, mat)
        if key not in self.index:
            self.index[key] = len(self.entries)
            self.entries.append(key)
        return self.index[key]

    def ids(self, mats):
        return {i for i, e in enumerate(self.entries) if e[3] in mats}


ALIASES = {"grey": "gray", "lightgrey": "lightgray", "darkgrey": "darkgray", "cream": "#f1e9d2",
           "sand": "#d8c79f", "beige": "#ddd2b8", "brick": "#a5553f", "terracotta": "#c0623f",
           "glass": "#9fb5c2", "concrete": "#b8b5ae", "gold": "#cfae5c", "bronze": "#8c6c47",
           "copper": "#5f9c87", "ochre": "#cc9a4a", "salmon": "#e19a85", "pink": "#dcb7ac",
           "white": "#efede6", "black": "#3a3a3d", "red": "#b5513f", "brown": "#7e5a43",
           "yellow": "#e3c86a", "green": "#6e9a5e", "blue": "#6c8cad", "orange": "#d98b4e",
           "silver": "#c3c6c9", "gray": "#9a9a9a", "darkgray": "#6e6f72", "lightgray": "#cfcfcc",
           "lightyellow": "#f2e6b0", "tan": "#cfb48c", "maroon": "#7a3b33", "moccasin": "#ecd7ad"}


def parse_colour(s):
    if not s:
        return None
    s = s.split(";")[0].strip().lower().replace(" ", "")
    s = ALIASES.get(s, s)
    s = ALIASES.get(s, s)
    try:
        rgb = hex_rgb(s) if re.fullmatch(r"#?[0-9a-f]{6}|#?[0-9a-f]{3}", s) else hex_rgb(webcolors.name_to_hex(s))
    except ValueError:
        return None
    # building paint is never neon: cap the saturation at 0.62, keep hue and lightness
    h_, l_, s_ = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    if s_ > 0.62 and 0.12 < l_ < 0.9:
        rgb = tuple(round(v * 255) for v in colorsys.hls_to_rgb(h_, l_, 0.62))
    return tame(rgb)


def tame(rgb, roof=False):
    """keep a facade or a roof in the colours buildings come in: magenta and violet (OSM's "pink", "fuchsia", a
    satellite colour drifting) become a dusty rose; a pale pink roof becomes the faded terracotta it is."""
    h_, l_, s_ = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    if 0.70 < h_ < 0.97 and s_ > 0.22:                 # violet to pink
        h_, s_ = 0.98, 0.2
    if roof and (h_ >= 0.94 or h_ < 0.035) and s_ > 0.12:  # pink and rose roofs: terracotta, darker, less saturated
        h_, s_, l_ = 0.035, min(s_, 0.42), min(l_, 0.58)
    if roof and 0.5 < h_ < 0.97 and s_ > 0.16:           # bluish to violet roofs: slate
        s_ = 0.12
    return tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h_, l_, s_))


def parse_len(s):
    if s is None:
        return None
    m = re.match(r"\s*(-?[0-9]+(?:[.,][0-9]+)?)", str(s))
    return float(m.group(1).replace(",", ".")) if m else None


def stable_hash(*a):
    return int(hashlib.md5("/".join(map(str, a)).encode()).hexdigest()[:8], 16)


pal = Palette()
C = {  # ground & misc (MagicaVoxel-like pastel, as in Warsaw)
    "paving": pal("#c6c2b8"), "paving2": pal("#b9b4a9"), "asphalt": pal("#5f636b"), "sett": pal("#8f8981"),
    "road_paving": pal("#a49f97"),
    "concrete": pal("#bdbab2"), "cycle": pal("#8a5a52"), "gravel": pal("#d8ccb5"), "parking": pal("#6a6d73"),
    "grass": pal("#86b45a", GRASS), "grass2": pal("#79a852", GRASS), "garden": pal("#73a34e", GRASS),
    "forest": pal("#5f8442", GRASS), "flower": pal("#4f7a3a", GRASS), "pitch": pal("#5f9150", GRASS),
    "foliage": pal("#4f7a3a", GRASS), "bloom_red": pal("#b8433b", GRASS), "bloom_yellow": pal("#d9b84a", GRASS),
    "bloom_white": pal("#e4e0d2", GRASS), "bloom_violet": pal("#7d5a9a", GRASS), "bloom_orange": pal("#d17a3a", GRASS),
    "dirt": pal("#a58a66"), "sand": pal("#d9c79a"), "rock": pal("#9c968b"), "court": pal("#b0614c"),
    "track": pal("#b8705a"), "ballast": pal("#8a8178"), "rail": pal("#55575d", METAL), "trambed": pal("#a9a59c"),
    "platform": pal("#b7b1a6"), "steps": pal("#a8a296"), "water": pal("#68654f", WATER), "pool": pal("#62b8cc"),
    "mark": pal("#f1efe8", MARK), "soil": pal("#7a5c45", SOIL), "stone": pal("#a59f92"), "riverbed": pal("#6f6551", SOIL),
    "trunk": pal("#6b4f3a"), "lamp": pal("#ffe2a8", LAMP), "pole": pal("#5b6164", METAL), "fence": pal("#3f4447", METAL),
    "deck": pal("#a7a49d", CONCRETE), "deck_side": pal("#8e8b85", CONCRETE), "pier": pal("#b8ae9a"),
    "woodfloor": pal("#6b5847"), "statue": pal("#5a7f6a", METAL),
    "parking_lane": pal("#686b70"), "kerb": pal("#b4afa6"),
    "signal": pal("#24272b", METAL), "signal_red": pal("#c8362c", METAL), "bench": pal("#7a5a3c"), "bin": pal("#3d4a44"),
    "hydrant": pal("#b8382f"), "sign_red": pal("#c23b30"), "sign_blue": pal("#2e5fa6"), "sign_warn": pal("#e9e3d6"),
}
# tree crowns (scripts/trees.py): five shades per kind of leaf, from the shaded inside and underside to the sunlit top.
# Darker than lawns; limes, oaks and chestnuts darkest, robinia, birch and larch light and yellowish, willows and white
# poplars grey-green, conifers blue-green. A colour belongs to one foliage class only (trees.py reads a leaf voxel's
# class back from it, and checks this) and is no landmark's leaf colour.
FOLIAGE = {
    "plane": ["#406834", "#4c743c", "#588444", "#68904c", "#7ca058"],
    "lime": ["#345830", "#406438", "#487040", "#588048", "#689050"],
    "silverlime": ["#3c5c38", "#486844", "#58784c", "#648858", "#789464"],
    "maple": ["#386030", "#487038", "#547c40", "#608848", "#749854"],
    "ash": ["#447038", "#508040", "#608c48", "#709854", "#80a860"],
    "robinia": ["#507838", "#5c8840", "#6c944c", "#7ca450", "#90b05c"],
    "sophora": ["#3c6434", "#48703c", "#588040", "#648c4c", "#789c58"],
    "gleditsia": ["#588038", "#689040", "#789c4c", "#88a854", "#9cb860"],
    "oak": ["#345834", "#406434", "#4c703c", "#588044", "#6c8c50"],
    "chestnut": ["#30542c", "#3c6034", "#487034", "#5c8044", "#689048"],
    "beech": ["#446838", "#507840", "#5c8448", "#6c9454", "#80a060"],
    "birch": ["#50803c", "#608c44", "#709c4c", "#80a858", "#94b864"],
    "rowan": ["#486c38", "#547c44", "#60884c", "#709850", "#84a85c"],
    "larch": ["#588848", "#689850", "#78a45c", "#88b068", "#98bc70"],
    "willow": ["#587048", "#607c50", "#708858", "#809864", "#90a870"],
    "alder": ["#305030", "#3c6038", "#486c3c", "#547844", "#648850"],
    "celtis": ["#3c6030", "#486c34", "#547840", "#608844", "#709858"],
    "poplar": ["#446c38", "#54783c", "#608844", "#6c9450", "#80a458"],
    "whitepoplar": ["#587454", "#68845c", "#789068", "#88a074", "#98ac80"],
    "ailanthus": ["#4c7838", "#588440", "#689044", "#78a050", "#8cb060"],
    "fruit": ["#406838", "#4c7440", "#58804c", "#689054", "#789c60"],
    "catalpa": ["#54783c", "#5c8844", "#6c984c", "#7ca458", "#90b060"],
    "ginkgo": ["#5c8440", "#689448", "#78a050", "#88b05c", "#9cbc68"],
    "scrub": ["#44683c", "#507440", "#5c8048", "#6c9050", "#7ca05c"],
    "pine": ["#2c4834", "#345438", "#3c6040", "#486848", "#507450"],
    "spruce": ["#284438", "#30503c", "#385844", "#406448", "#487050"],
    "thuja": ["#345030", "#3c5834", "#446438", "#507040", "#587c48"],
    "cedar": ["#3c5848", "#446450", "#50705c", "#587c64", "#688870"],
}
# bark, per voxel by hash: the plane's mottle of cream, olive and grey, the birch's white with dark marks, grey smooth
# (maple, ash, hornbeam, Celtis), dark furrowed (lime, oak, robinia, chestnut, poplar), the pine's red-brown
BARK = {
    "plane": ["#c9c2a2", "#b3ae8d", "#9a9679", "#d6d0b8", "#8b876e"],
    "birch": ["#e6e3da", "#dcd9cf", "#ece9e1", "#e1ded5", "#3d3a36"],
    "grey": ["#77736b", "#837f77", "#6c6861"],
    "smooth": ["#8f8b84", "#9a968e", "#85817a"],
    "dark": ["#4f4740", "#5a5149", "#463f39"],
    "furrow": ["#5b4f44", "#4c4239", "#665a4e"],
    "pale": ["#a8a397", "#97928a", "#b5b0a4"],
    "pine": ["#7a4e36", "#8c5c3f", "#6a4632"],
    "willow": ["#6b6357", "#5e574d", "#776f62"],
}
FOLIAGE_IDS = {k: [pal(c, LEAF) for c in v] for k, v in FOLIAGE.items()}
BARK_IDS = {k: [pal(c) for c in v] for k, v in BARK.items()}
NEEDLES = sorted({i for k in ("pine", "spruce", "thuja", "cedar") for i in FOLIAGE_IDS[k]})
SCRUB = FOLIAGE_IDS["scrub"]
LEAVES = sorted({i for v in FOLIAGE_IDS.values() for i in v} - set(NEEDLES) - set(SCRUB))
# Pest's eclectic and Secession facades: creams, ochres, sand, yellows, the odd pink, sage and grey (no colour in OSM).
# Street photos (Mapillary, 2024-26) beside renders from the same spots read lighter than this once was: more off-white
# and pale grey stone, fewer dull tans, and the odd terracotta front
WALLS = ["#e6d8b5", "#dcc8a0", "#d4bf96", "#e9dcc0", "#cfc1a3", "#ebe5d8", "#e3cf9b", "#d9cdb8", "#dedbd3",
         "#d8c08a", "#e8d9b0", "#cbbfae", "#b9b4ab", "#ead48f", "#e2b8a4", "#c9cfb0", "#d6c9b5", "#efe3c4",
         "#e7e3da", "#cf8e72", "#e0cf7a"]
# tenement roofs from above: weathered terracotta tile, and grey sheet metal, slate and eternit, a bit more grey than
# red (lighter and less mauve than they were: aerial photos of Pest read about a fifth brighter, tiles more orange)
ROOFS_PITCHED = ["#a8664f", "#9a5c49", "#b27660", "#9a6a55", "#877b72", "#76736f", "#86827d", "#6b6864", "#958b83",
                 "#a08f80", "#615f5c", "#7f7b77"]
ROOFS_FLAT = ["#a8a49b", "#97948d", "#b3afa6", "#9f9b93", "#8c8984"]
MATERIAL_WALL = {"brick": "#a5553f", "stone": "#cdc3ae", "sandstone": "#d6c49a", "limestone": "#ddd3bd",
                 "concrete": "#b8b5ae", "glass": "#8fa7b5", "metal": "#9aa0a6", "steel": "#9aa0a6", "wood": "#8a6a4c",
                 "plaster": None, "masonry": "#c9bea8"}
MATERIAL_ROOF = {"roof_tiles": "#9a5a45", "tile": "#9a5a45", "tiles": "#9a5a45", "slate": "#55585c", "metal": "#7d8287",
                 "copper": "#6c9a86", "zinc": "#8d9296", "tar_paper": "#6f6c68", "concrete": "#a6a29a", "glass": "#a8c0cc",
                 "gravel": "#a39d92", "grass": "#7aa15a", "asphalt": "#5f6066", "eternit": "#7b7774"}
