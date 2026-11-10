"""The Minecraft blocks the converter may use, with their colours, measured from the game's own textures.

    uv run python scripts/minecraft_blocks.py [version]      # default: $MC_VERSION, else 26.3

Downloads the client jar of that version once (data/raw/minecraft/, not committed), averages each block's side and
top textures (alpha-weighted; grass and leaves tinted with the plains biome colours) and writes
scripts/minecraft_blocks.json: {version, data_version, blocks: {id: {side, top, groups}}}. Run it again when the
server moves to a new Minecraft version; the converter reads the JSON, so building a world needs no download.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "minecraft"
OUT = ROOT / "scripts" / "minecraft_blocks.json"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

GRASS_TINT = (0x91, 0xBD, 0x59)    # plains
FOLIAGE_TINT = (0x77, 0xAB, 0x2F)  # plains
FIXED_TINT = {"birch_leaves": (0x80, 0xA7, 0x55), "spruce_leaves": (0x61, 0x99, 0x61)}
TINTED = {"oak_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "mangrove_leaves", "birch_leaves",
          "spruce_leaves", "grass_block"}

COLOURS = ["white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow", "lime", "green", "cyan",
           "light_blue", "blue"]  # no pink, magenta or purple: nothing in the city should come out that way
STONES = ["stone", "smooth_stone", "andesite", "polished_andesite", "diorite", "polished_diorite", "granite",
          "polished_granite", "calcite", "tuff", "polished_tuff", "tuff_bricks", "deepslate", "polished_deepslate",
          "deepslate_bricks", "deepslate_tiles", "cobbled_deepslate", "stone_bricks", "sandstone", "smooth_sandstone",
          "cut_sandstone", "red_sandstone", "smooth_red_sandstone", "quartz_block", "smooth_quartz", "bricks",
          "mud_bricks", "packed_mud", "end_stone", "end_stone_bricks", "dark_prismarine", "blackstone",
          "polished_blackstone", "polished_blackstone_bricks", "smooth_basalt", "nether_bricks", "red_nether_bricks",
          "dripstone_block", "resin_bricks", "clay", "mushroom_stem", "bone_block", "prismarine_bricks"]
PLANKS = ["oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks", "dark_oak_planks",
          "mangrove_planks", "bamboo_planks", "pale_oak_planks"]
METALS = ["iron_block", "gold_block", "copper_block", "exposed_copper", "weathered_copper", "oxidized_copper",
          "cut_copper", "exposed_cut_copper", "weathered_cut_copper", "oxidized_cut_copper", "netherite_block",
          "polished_deepslate", "polished_blackstone", "smooth_stone", "polished_andesite", "light_gray_concrete",
          "gray_concrete", "black_concrete", "white_concrete", "waxed_copper_block"]
GROUPS = {
    "generic": [f"{c}_concrete" for c in COLOURS] + ["terracotta"] + [f"{c}_terracotta" for c in COLOURS]
               + [f"{c}_wool" for c in COLOURS] + STONES + PLANKS,
    "roof": ["terracotta"] + [f"{c}_terracotta" for c in COLOURS] + ["bricks", "deepslate_tiles", "deepslate_bricks",
             "polished_deepslate", "cobbled_deepslate", "blackstone", "polished_blackstone", "mud_bricks",
             "nether_bricks", "red_nether_bricks", "oxidized_copper", "weathered_copper", "exposed_copper",
             "copper_block", "dark_prismarine", "stone_bricks", "stone", "andesite", "granite", "spruce_planks",
             "dark_oak_planks", "gray_concrete", "light_gray_concrete", "black_concrete", "brown_concrete",
             "smooth_stone", "tuff", "polished_tuff", "packed_mud", "resin_bricks", "red_sandstone"],
    "glass": ["glass", "tinted_glass"] + [f"{c}_stained_glass" for c in COLOURS],
    "window": [f"{c}_stained_glass" for c in ("gray", "black", "light_gray", "cyan", "light_blue", "blue", "brown")],
    "leaf": ["oak_leaves", "birch_leaves", "spruce_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves",
             "mangrove_leaves", "azalea_leaves", "flowering_azalea_leaves", "pale_oak_leaves"],
    "lamp": ["sea_lantern", "glowstone", "shroomlight", "ochre_froglight", "pearlescent_froglight", "verdant_froglight"],
    "soil": ["dirt", "coarse_dirt", "rooted_dirt", "podzol", "mud", "packed_mud", "moss_block", "grass_block"],
    "grass": ["grass_block", "moss_block", "green_wool", "lime_wool", "green_concrete", "lime_concrete", "white_wool",
              "yellow_wool", "orange_wool", "red_wool", "light_blue_wool", "blue_wool", "azalea_leaves"],
    "metal": METALS,
    "interior": ["black_concrete", "gray_concrete", "shroomlight", "ochre_froglight", "pearlescent_froglight"],
    "ground": ["stone", "deepslate", "bedrock", "water", "dirt"],
}
# thin things (poles, spires, cable stays): walls, standing as posts, joined to their neighbours
WALLS = {"andesite_wall": "andesite", "stone_brick_wall": "stone_bricks", "polished_blackstone_wall": "polished_blackstone",
         "polished_deepslate_wall": "polished_deepslate", "cobbled_deepslate_wall": "cobbled_deepslate",
         "diorite_wall": "diorite", "sandstone_wall": "sandstone", "brick_wall": "bricks", "mud_brick_wall": "mud_bricks",
         "end_stone_brick_wall": "end_stone_bricks", "polished_tuff_wall": "polished_tuff",
         "red_sandstone_wall": "red_sandstone", "deepslate_tile_wall": "deepslate_tiles", "blackstone_wall": "blackstone",
         "resin_brick_wall": "resin_bricks", "granite_wall": "granite"}
EXTRA = {"iron_bars": "iron_bars", "lantern": "lantern"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "voxelpest"}), timeout=120) as r:
        return r.read()


def client_jar(version):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"client-{version}.jar"
    if not p.exists():
        man = json.loads(fetch(MANIFEST))
        v = next(x for x in man["versions"] if x["id"] == version)
        meta = json.loads(fetch(v["url"]))
        print("downloading the client jar", version, meta["downloads"]["client"]["size"] // 2 ** 20, "MB")
        p.write_bytes(fetch(meta["downloads"]["client"]["url"]))
    return zipfile.ZipFile(p)


class Models:
    def __init__(self, jar):
        self.jar = jar

    def json(self, path):
        try:
            return json.loads(self.jar.read(path))
        except KeyError:
            return None

    def model_textures(self, name):
        """the texture variables of a model, parents first, then its own"""
        name = name.replace("minecraft:", "")
        m = self.json(f"assets/minecraft/models/{name}.json")
        if m is None:
            return {}
        tex = self.model_textures(m["parent"]) if "parent" in m else {}
        tex.update(m.get("textures", {}))
        return tex

    def textures(self, block):
        bs = self.json(f"assets/minecraft/blockstates/{block}.json")
        if bs is None:
            return None
        if "variants" in bs:
            v = next(iter(bs["variants"].values()))
        else:  # multipart: the first part (a wall's post)
            v = bs["multipart"][0]["apply"]
        if isinstance(v, list):
            v = v[0]
        tex = self.model_textures(v["model"])

        def res(k, depth=0):
            t = tex.get(k)
            while depth < 8:
                ref = t.get("sprite") if isinstance(t, dict) else t
                if not (isinstance(ref, str) and ref.startswith("#")):
                    break
                t, depth = tex.get(ref[1:]), depth + 1
            return t
        side = next((res(k) for k in ("north", "side", "all", "wall", "texture", "particle") if res(k)), None)
        top = next((res(k) for k in ("up", "top", "end", "all", "wall", "texture", "particle") if res(k)), None)
        return side, top

    def colour(self, tex, tint=None):
        if isinstance(tex, dict):  # newer models can give a texture as {"sprite": ..., ...}
            tex = tex.get("sprite") or tex.get("texture") or ""
        p = tex.replace("minecraft:", "")
        try:
            im = Image.open(io.BytesIO(self.jar.read(f"assets/minecraft/textures/{p}.png"))).convert("RGBA")
        except KeyError:
            return None
        a = np.asarray(im, np.float64)
        a = a[:a.shape[1]]  # an animated strip: its first frame
        w = a[..., 3:4] / 255
        if w.sum() < 1:
            return None
        rgb = (a[..., :3] * w).sum((0, 1)) / w.sum()
        if tint is not None:
            rgb = rgb * np.array(tint) / 255
        return [int(round(c)) for c in rgb], float(w.mean())


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MC_VERSION", "26.3")
    jar = client_jar(version)
    info = json.loads(jar.read("version.json"))
    M = Models(jar)
    blocks = {}
    want = {}
    for g, names in GROUPS.items():
        for n in names:
            want.setdefault(n, []).append(g)
    for n in WALLS:
        want.setdefault(n, []).append("wall")
    for n in EXTRA:
        want.setdefault(n, []).append("thin")
    missing = []
    for n, groups in sorted(want.items()):
        if n in ("water", "bedrock"):
            blocks[n] = dict(side=[63, 118, 228] if n == "water" else [85, 85, 85], top=None, groups=groups)
            continue
        t = M.textures(n)
        if t is None:
            missing.append(n)
            continue
        side_t, top_t = t
        tint_side = tint_top = None
        if n in TINTED:
            tint = FIXED_TINT.get(n, FOLIAGE_TINT if n.endswith("leaves") else GRASS_TINT)
            tint_top = tint
            tint_side = tint if n.endswith("leaves") else None
        if n == "grass_block":
            side_t = "block/grass_block_side"
        s = M.colour(side_t, tint_side) if side_t else None
        tp = M.colour(top_t, tint_top) if top_t else None
        if s is None:
            missing.append(n)
            continue
        blocks[n] = dict(side=s[0], top=(tp or s)[0], cover=round(s[1], 2), groups=groups)
    OUT.write_text(json.dumps(dict(version=version, data_version=info["world_version"], walls=WALLS, blocks=blocks),
                              indent=1, ensure_ascii=False))
    print(f"{len(blocks)} blocks for Minecraft {version} (data version {info['world_version']}) -> {OUT.name}")
    if missing:
        print("not in this version:", ", ".join(missing))


if __name__ == "__main__":
    main()
