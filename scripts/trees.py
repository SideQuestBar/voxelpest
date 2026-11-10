"""Trees: each tree's species and foliage class, its shape, and the foliage grid the viewer's seasons read.

Species. OSM names one for 5 % of the map's mapped trees (species, genus, taxon, taxon:genus, the Hungarian and
English names, species:wikipedia / :wikidata) and a leaf type for 69 % (leaf_type, leaf_cycle). Every other tree
gets one drawn from a mix for where it stands, by a hash of its position (a tree row's trees share one, by the row's id):
streets (FŐKERT's typical street genera and the species its register names most), narrow streets (small crowns: globe
robinias, Callery pears, manna ash), parks and squares, courtyard gardens, the Buda hills' woods, Margaret Island, and the
banks of the Danube and the ponds (willows, poplars, alder). README "Trees" has the sources.

Classes (foliage.bin; warsaw-vibe-voxel's phenology ids, plus the plane): 1 maple, 2 lime, 3 ash, 4 robinia (Sophora,
Gleditsia), 5 oak, 6 horse chestnut, 7 beech and hornbeam, 8 birch, 9 rowan, 10 larch, 11 willow, 12 alder, 13 other
deciduous, 14 evergreen conifers, 15 plane.

Shapes. A crown is a union of ellipsoids (a body and a few lobes, placed by the species' form and then scaled to the
tree's radius and crown height), roughened by value noise and opened by clumped gaps where the foliage is thin; cones,
pines and weeping willows have their own. The trunk runs to the crown's base and on as a leader, with main limbs and a
fork each inside the crown, in bark colours (not LEAF): a bare winter tree still reads as a tree. Crowns are cached by
(species, radius, crown height, variant) in voxels, and turned and mirrored per tree.
"""
import math
import re
from collections import Counter, namedtuple

import numpy as np
from scipy import ndimage

from style import BARK_IDS, FOLIAGE_IDS

MAPLE, LIME, ASH, ROBINIA, OAK, CHESTNUT, BEECH, BIRCH, ROWAN, LARCH, WILLOW, ALDER, OTHER, CONIFER, PLANE = range(1, 16)
CLASS_NAMES = ["none", "maple", "lime", "ash", "robinia", "oak", "chestnut", "beech/hornbeam", "birch", "rowan", "larch",
               "willow", "alder", "other deciduous", "conifer", "plane"]

Sp = namedtuple("Sp", "cls form h r base dens leaf bark")
# class, form, height (m), crown radius (m), crown base (share of the height), foliage density, leaves, bark
SPECIES = {
    "plane": Sp(PLANE, "broad", (18, 30), (6.5, 9.5), (0.15, 0.25), 0.86, "plane", "plane"),
    "lime": Sp(LIME, "oval", (14, 22), (4.0, 6.0), (0.18, 0.28), 0.95, "lime", "dark"),
    "silverlime": Sp(LIME, "round", (14, 20), (4.5, 6.5), (0.2, 0.28), 0.95, "silverlime", "grey"),
    "maple": Sp(MAPLE, "round", (10, 17), (3.8, 6.0), (0.2, 0.3), 0.93, "maple", "grey"),
    "fieldmaple": Sp(MAPLE, "round", (6, 11), (2.6, 4.0), (0.25, 0.35), 0.9, "maple", "grey"),
    "ash": Sp(ASH, "open", (14, 22), (4.0, 6.0), (0.3, 0.42), 0.72, "ash", "grey"),
    "manna": Sp(ASH, "round", (6, 10), (2.6, 4.0), (0.28, 0.38), 0.85, "ash", "smooth"),
    "robinia": Sp(ROBINIA, "open", (12, 20), (3.5, 5.5), (0.35, 0.5), 0.62, "robinia", "furrow"),
    "globe": Sp(ROBINIA, "globe", (4.5, 6.5), (1.8, 2.6), (0.42, 0.52), 0.97, "robinia", "furrow"),
    "sophora": Sp(ROBINIA, "round", (10, 16), (4.5, 7.0), (0.25, 0.35), 0.82, "sophora", "furrow"),
    "gleditsia": Sp(ROBINIA, "open", (10, 16), (3.5, 5.5), (0.3, 0.42), 0.55, "gleditsia", "dark"),
    "oak": Sp(OAK, "broad", (16, 25), (5.5, 8.0), (0.22, 0.32), 0.88, "oak", "furrow"),
    "oakcol": Sp(OAK, "column", (12, 18), (1.6, 2.4), (0.08, 0.14), 0.95, "oak", "furrow"),
    "chestnut": Sp(CHESTNUT, "broad", (14, 20), (5.5, 7.5), (0.16, 0.24), 0.97, "chestnut", "dark"),
    "hornbeam": Sp(BEECH, "oval", (12, 18), (3.5, 5.5), (0.15, 0.25), 0.94, "beech", "smooth"),
    "hornbeamcol": Sp(BEECH, "column", (9, 14), (2.0, 3.0), (0.06, 0.12), 0.97, "beech", "smooth"),
    "beech": Sp(BEECH, "broad", (18, 28), (6.0, 8.5), (0.12, 0.22), 0.95, "beech", "smooth"),
    "birch": Sp(BIRCH, "oval", (12, 18), (2.2, 3.6), (0.28, 0.4), 0.55, "birch", "birch"),
    "rowan": Sp(ROWAN, "round", (6, 10), (2.0, 3.2), (0.3, 0.4), 0.8, "rowan", "grey"),
    "larch": Sp(LARCH, "cone", (15, 25), (2.5, 4.0), (0.12, 0.25), 0.6, "larch", "pine"),
    "willow": Sp(WILLOW, "weep", (11, 17), (5.0, 7.5), (0.2, 0.28), 0.85, "willow", "willow"),
    "whitewillow": Sp(WILLOW, "open", (14, 22), (5.0, 7.5), (0.18, 0.28), 0.8, "willow", "willow"),
    "alder": Sp(ALDER, "oval", (12, 18), (2.5, 4.0), (0.2, 0.3), 0.85, "alder", "dark"),
    "celtis": Sp(OTHER, "round", (12, 18), (4.0, 6.0), (0.28, 0.38), 0.88, "celtis", "grey"),
    "poplar": Sp(OTHER, "oval", (22, 30), (5.0, 7.5), (0.3, 0.42), 0.75, "poplar", "dark"),
    "poplarcol": Sp(OTHER, "column", (20, 28), (1.8, 2.8), (0.04, 0.1), 0.92, "poplar", "dark"),
    "whitepoplar": Sp(OTHER, "round", (18, 26), (5.5, 8.0), (0.25, 0.35), 0.8, "whitepoplar", "pale"),
    "ailanthus": Sp(OTHER, "open", (10, 17), (3.5, 5.0), (0.4, 0.55), 0.6, "ailanthus", "smooth"),
    "pear": Sp(OTHER, "oval", (8, 12), (2.0, 3.0), (0.22, 0.3), 0.95, "fruit", "grey"),
    "fruit": Sp(OTHER, "round", (5, 8), (2.2, 3.5), (0.3, 0.4), 0.88, "fruit", "dark"),
    "koel": Sp(OTHER, "round", (7, 10), (3.0, 4.5), (0.3, 0.4), 0.82, "ailanthus", "grey"),
    "hazel": Sp(OTHER, "oval", (10, 15), (2.6, 3.6), (0.15, 0.22), 0.95, "celtis", "grey"),
    "elm": Sp(OTHER, "broad", (14, 22), (5.0, 7.0), (0.3, 0.4), 0.85, "celtis", "dark"),
    "walnut": Sp(OTHER, "broad", (10, 16), (5.0, 7.0), (0.25, 0.35), 0.85, "fruit", "pale"),
    "mulberry": Sp(OTHER, "round", (6, 10), (3.0, 4.5), (0.25, 0.35), 0.9, "fruit", "dark"),
    "catalpa": Sp(OTHER, "broad", (8, 13), (4.5, 6.5), (0.3, 0.4), 0.85, "catalpa", "grey"),
    "ginkgo": Sp(OTHER, "oval", (10, 18), (2.5, 4.0), (0.2, 0.3), 0.75, "ginkgo", "grey"),
    "metaseq": Sp(OTHER, "cone", (15, 25), (2.5, 3.8), (0.05, 0.12), 0.8, "ginkgo", "pine"),
    "pine": Sp(CONIFER, "pine", (12, 22), (3.5, 5.5), (0.58, 0.72), 0.9, "pine", "pine"),
    "spruce": Sp(CONIFER, "cone", (14, 24), (2.5, 3.8), (0.02, 0.08), 0.95, "spruce", "dark"),
    "thuja": Sp(CONIFER, "cone", (5, 10), (1.2, 2.2), (0.02, 0.06), 0.97, "thuja", "dark"),
    "cedar": Sp(CONIFER, "cone", (15, 24), (5.0, 7.0), (0.1, 0.18), 0.85, "cedar", "dark"),
    "scrub": Sp(OTHER, "shrub", (2.0, 3.5), (1.2, 2.0), (0.0, 0.0), 0.8, "scrub", "dark"),
}
NAMES = list(SPECIES)
FORMS = ("round", "oval", "broad", "open", "column", "globe", "weep", "shrub", "pine", "cone")
LEAF_CLASS = {}  # leaf palette id -> class
for _k, _s in SPECIES.items():
    for _i in FOLIAGE_IDS[_s.leaf]:
        assert LEAF_CLASS.get(_i, _s.cls) == _s.cls, f"leaf colour of {_k} shared with another class"
        LEAF_CLASS[_i] = _s.cls

# where a tree's species isn't tagged: the share of each species by setting (weights). Street: FŐKERT's typical genera
# (Tilia, Acer, Fraxinus, Celtis, Robinia, Styphnolobium, Gleditsia), the plane (~4000 of the city's ~27 000 street
# trees), chestnut, ornamental pear and Koelreuteria (the register's most common, index.hu 2016)
MIX = {
    "street": dict(silverlime=9, lime=7, plane=12, ash=8, manna=3, sophora=10, celtis=10, maple=8, fieldmaple=2,
                   robinia=6, globe=5, chestnut=6, pear=4, koel=3, gleditsia=2, hazel=2, ailanthus=2, poplarcol=1),
    "narrow": dict(globe=26, pear=12, koel=8, celtis=12, sophora=8, fieldmaple=8, manna=10, lime=8, hazel=6, ailanthus=2),
    "park": dict(plane=13, chestnut=9, lime=6, silverlime=4, maple=9, ash=7, oak=8, celtis=6, sophora=4, robinia=4,
                 hornbeam=5, beech=2, birch=4, poplar=3, whitepoplar=1, poplarcol=1, elm=2, ailanthus=1, fruit=2,
                 walnut=1, catalpa=1, rowan=1, ginkgo=1, pine=4, spruce=2, thuja=3, cedar=1),
    "yard": dict(ailanthus=14, celtis=12, robinia=10, fieldmaple=8, maple=5, fruit=10, walnut=6, mulberry=6, birch=6,
                 lime=5, catalpa=5, thuja=7, pine=2, spruce=2, poplar=2),
    # Gellért Hill: remnants of lime-ash and hornbeam-oak woods, karst scrub woods, planted robinia and pine
    "hills": dict(oak=24, hornbeam=14, robinia=16, ash=8, manna=6, fieldmaple=8, lime=6, celtis=5, pine=7, ailanthus=3,
                  rowan=3),
    "island": dict(plane=22, poplar=10, whitepoplar=4, poplarcol=2, willow=4, whitewillow=4, oak=12, chestnut=8, maple=6,
                   ash=6, lime=6, sophora=3, birch=2, hornbeam=2, pine=5, cedar=2, spruce=2),
    "bank": dict(willow=22, whitewillow=14, poplar=14, whitepoplar=12, alder=10, plane=10, ash=8, maple=5, poplarcol=5),
}
CONIFERS = dict(pine=45, spruce=22, thuja=25, cedar=8)
SCALE = dict(street=0.75, narrow=0.65, park=1.0, yard=0.85, hills=0.85, island=1.05, bank=1.0, scrub=1.0)
# a street tree's crown: no wider than its spacing allows (rows every 8-9 m), nor than the pavement to the facade
CAP = dict(street=5.0, narrow=3.6, yard=4.5)
YOUNG = dict(street=0.12, narrow=0.15, park=0.04, yard=0.06)  # replanted street trees, a few years old

TAG_KEYS = ("species", "genus", "taxon", "taxon:genus", "taxon:species", "species:hu", "taxon:hu", "genus:hu",
            "species:en", "taxon:en", "genus:en", "species:wikipedia", "taxon:wikipedia", "genus:wikipedia", "name")
RULES = [(re.compile(p), k) for p, k in (
    (r"acer (campestre|negundo|tataricum|ginnala)|mezei juhar|zöld juhar|kőrislevelű juhar|tatár ?juhar|box ?elder",
     "fieldmaple"),
    (r"\bacer\b|\bjuhar\b|maple", "maple"),
    (r"platan|platán|\bplane\b", "plane"),
    (r"quercus.*(pyramid|fastig)|oszlopos.*tölgy|piramistölgy", "oakcol"),
    (r"quercus|tölgy|\boak\b", "oak"),
    (r"(carpinus|gyertyán).*(fastig|columnar)|oszlopos.*gyertyán", "hornbeamcol"),
    (r"carpinus|gyertyán|hornbeam", "hornbeam"),
    (r"fagus|bükk|beech", "beech"),
    (r"tilia tomentosa|ezüst ?hárs|silver (lime|linden)", "silverlime"),
    (r"tilia|hárs|\blime\b|linden|malvaceae|malvales", "lime"),
    (r"aesculus|(?<!szelíd)gesztenye|horse.?chestnut", "chestnut"),
    (r"fraxinus ornus|virágos kőris|manna ash|gömbkőris", "manna"),
    (r"fraxinus|kőris|\bash\b", "ash"),
    (r"umbraculifera|gömbakác", "globe"),
    (r"styphnolobium|sophora|japánakác|pagoda", "sophora"),
    (r"gleditsia|lepényfa|honey ?locust", "gleditsia"),
    (r"robinia|robinieae|akác|black locust|fabaceae", "robinia"),
    (r"\bbetula\b|nyír\b|nyírfa|birch", "birch"),
    (r"sorbus|berkenye|rowan|whitebeam", "rowan"),
    (r"larix|vörösfenyő|larch", "larch"),
    (r"metasequoia|taxodium|mocsárciprus|kínai mamutfenyő|dawn redwood", "metaseq"),
    (r"salix.*(babylon|tristis|sepulcral|pendul)|szomorúfűz|weeping willow", "willow"),
    (r"salix|fűz|willow", "whitewillow"),
    (r"alnus|éger|alder", "alder"),
    (r"populus nigra.*italica|jegenyenyár|lombardy", "poplarcol"),
    (r"populus alba|fehér nyár|white poplar|ezüstnyár", "whitepoplar"),
    (r"populus|nyár\b|nyárfa|poplar", "poplar"),
    (r"celtis|ostorfa|hackberry", "celtis"),
    (r"ulmus|\bszil\b|szilfa|\belm\b", "elm"),
    (r"ailanthus|bálványfa|tree of heaven", "ailanthus"),
    (r"koelreuteria|csörgőfa", "koel"),
    (r"pyrus calleryana|díszkörte|callery", "pear"),
    (r"corylus colurna|török mogyoró|turkish hazel", "hazel"),
    (r"juglans|carya|pterocarya|\bdió|szárnyasdió|hikori|walnut|hickory|castanea|szelídgesztenye|sweet chestnut", "walnut"),
    (r"morus|eper|mulberry", "mulberry"),
    (r"catalpa|szivarfa|paulownia|császárfa", "catalpa"),
    (r"ginkgo|gingko|páfrányfenyő", "ginkgo"),
    (r"cedrus|cédrus|cedar", "cedar"),
    (r"abies|picea|pseudotsuga|sequoiadendron|jegenyefenyő|\bluc|duglász|mamutfenyő|spruce|\bfir\b", "spruce"),
    (r"taxus|tiszafa|thuja|tuja|életfa|cupress|ciprus|chamaecyparis|juniperus|boróka|calocedrus|\byew\b|cypress|juniper",
     "thuja"),
    (r"pinus|pinux|pinaceae|fenyő|\bpine\b", "pine"),
    (r"prunus|malus|pyrus|cydonia|mespilus|ficus|cercis|magnolia|liriodendron|parrotia|albizia|ceratonia|maclura|"
     r"cseresznye|meggy|szilva|barack|mandula|\balma|körte|birs|naspolya|füge|júdásfa|liliomfa|tulipánfa|varázsfa|"
     r"selyemvirág|szentjánoskenyér|cherry|plum|apple|\bpear\b|almond|apricot|peach|\bfig\b|quince|medlar|carob|"
     r"crataegus|galagonya|rhus|ecetfa|elaeagnus|ezüstfa|tetradium|mézesfa",
     "fruit"),
)]
# species:wikidata on trees with no name tag (the Q ids paired with Hungarian Wikipedia titles on other trees)
WIKIDATA = {"Q165145": "oak", "Q161374": "plane", "Q161382": "silverlime", "Q26745": "maple", "Q157417": "robinia",
            "Q156895": "birch", "Q3079266": "pear", "Q156944": "maple", "Q158776": "hornbeam", "Q161421": "manna",
            "Q156831": "lime", "Q163831": "catalpa", "Q146951": "fruit", "Q179729": "thuja", "Q145954": "pine",
            "Q623489": "cedar", "Q146149": "beech", "Q158746": "lime", "Q146269": "whitepoplar", "Q248582": "celtis",
            "Q157307": "mulberry", "Q852572": "walnut", "Q26899": "chestnut", "Q147064": "poplar"}


def species_of(t):
    """a species key from a tree's name tags, or None; and its leaf type ('needle', 'broad' or None)"""
    txt = " ".join(str(t[k]) for k in TAG_KEYS if k in t).lower()
    sp = next((k for rx, k in RULES if rx.search(txt)), None) if txt else None
    if sp is None:
        sp = WIKIDATA.get(t.get("species:wikidata") or t.get("taxon:wikidata"))
    lt = t.get("leaf_type")
    return sp, ("needle" if lt == "needleleaved" else "broad" if lt == "broadleaved" else None)


def uhash(a, b, salt):
    """uniform [0, 1) from two integer arrays and a salt (deterministic, vectorised)"""
    h = (np.asarray(a, np.int64) & 0xFFFFFFFF) * 0x9E3779B1 + (np.asarray(b, np.int64) & 0xFFFFFFFF) * 0x85EBCA77
    h = (h + salt * 0xC2B2AE3D) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h ^= h >> 12
    h = (h * 0x297A2D39) & 0xFFFFFFFF
    h ^= h >> 15
    return h / 2.0 ** 32


def pick(mix, u):
    keys = list(mix)
    w = np.cumsum([mix[k] for k in keys], dtype=np.float64)
    return keys[min(int(np.searchsorted(w, u * w[-1], side="right")), len(keys) - 1)]


def vhash(x, y, z):
    h = (x.astype(np.int64) * 73856093) ^ (y.astype(np.int64) * 19349663) ^ (z.astype(np.int64) * 83492791)
    return ((h ^ (h >> 13)) & 0xFFFF) / 65535.0


def near_mask(mask, xs, ys, rad):
    """for points on the 1 m grid: distance to the nearest cell of mask within rad m (rad + 1 if none), and the unit
    vector pointing away from the mask cells around (weighted 1/d)"""
    D_, W_ = mask.shape
    o = np.arange(-rad, rad + 1)
    oy, ox = np.meshgrid(o, o, indexing="ij")
    oy, ox = oy.ravel(), ox.ravel()
    od = np.hypot(oy, ox)
    keep = od <= rad
    oy, ox, od = oy[keep], ox[keep], od[keep]
    dist = np.full(len(xs), rad + 1.0, np.float32)
    away = np.zeros((len(xs), 2), np.float32)
    for s in range(0, len(xs), 4000):
        cx, cy = xs[s:s + 4000].astype(int), ys[s:s + 4000].astype(int)
        yy, xx = cy[:, None] + oy[None], cx[:, None] + ox[None]
        ok = (yy >= 0) & (yy < D_) & (xx >= 0) & (xx < W_)
        hit = np.zeros(yy.shape, bool)
        hit[ok] = mask[yy[ok], xx[ok]]
        dist[s:s + 4000] = np.where(hit.any(1), np.where(hit, od[None], 1e9).min(1), rad + 1.0)
        wgt = np.where(hit, 1.0 / np.maximum(od[None], 0.5), 0.0)
        v = -np.stack([(wgt * ox[None]).sum(1), (wgt * oy[None]).sum(1)], 1)
        n = np.linalg.norm(v, axis=1, keepdims=True)
        away[s:s + 4000] = np.where(n > 1e-6, v / np.maximum(n, 1e-6), 0)
    return dist, away


def vnoise(shape, cell, rs):
    g = rs.uniform(-1, 1, tuple(s // cell + 2 for s in shape)).astype(np.float32)
    return ndimage.zoom(g, cell, order=1)[:shape[0], :shape[1], :shape[2]]


# body (horizontal and vertical semi-axis, centre height: shares of the crown), lobes (count, distance from the centre,
# size, sine of their elevation), noise, the leader (share of the crown height), limbs (count, start height, elevation°)
FORM = {
    "round": dict(a=0.72, c=0.78, zc=0.5, n=(5, 8), d=(0.5, 0.75), la=(0.36, 0.5), el=(-0.3, 0.75), amp=0.16,
                  lead=0.6, limbs=(4, 6), start=(0.05, 0.4), elev=(35, 55)),
    "oval": dict(a=0.75, c=0.82, zc=0.5, n=(5, 8), d=(0.45, 0.7), la=(0.38, 0.52), el=(-0.6, 0.8), amp=0.15,
                 lead=0.7, limbs=(4, 6), start=(0.05, 0.45), elev=(45, 65)),
    "broad": dict(a=0.7, c=0.72, zc=0.46, n=(6, 9), d=(0.55, 0.8), la=(0.36, 0.5), el=(-0.25, 0.6), amp=0.16,
                  lead=0.4, limbs=(5, 7), start=(0.0, 0.3), elev=(22, 45)),
    "open": dict(a=0.5, c=0.55, zc=0.5, n=(6, 10), d=(0.6, 0.85), la=(0.28, 0.42), el=(-0.3, 0.8), amp=0.22,
                 lead=0.5, limbs=(4, 6), start=(0.0, 0.35), elev=(30, 60)),
    "column": dict(a=0.85, c=0.9, zc=0.5, n=(3, 5), d=(0.3, 0.55), la=(0.5, 0.7), el=(-0.85, 0.85), amp=0.1,
                   lead=0.88, limbs=(4, 5), start=(0.05, 0.7), elev=(70, 80)),
    "globe": dict(a=0.92, c=0.92, zc=0.5, n=(3, 4), d=(0.25, 0.4), la=(0.5, 0.6), el=(-0.3, 0.8), amp=0.06,
                  lead=0.3, limbs=(3, 4), start=(0.0, 0.15), elev=(30, 50)),
    "weep": dict(a=0.8, c=0.75, zc=0.56, n=(4, 6), d=(0.45, 0.6), la=(0.4, 0.5), el=(-0.1, 0.7), amp=0.12,
                 lead=0.5, limbs=(5, 6), start=(0.0, 0.3), elev=(30, 45)),
    "shrub": dict(a=0.75, c=0.8, zc=0.5, n=(3, 5), d=(0.4, 0.6), la=(0.45, 0.6), el=(-0.2, 0.6), amp=0.2,
                  lead=0.0, limbs=(3, 3), start=(0.0, 0.0), elev=(55, 70)),
    "pine": dict(amp=0.2, lead=0.88, limbs=(3, 5), start=(0.1, 0.7), elev=(12, 30)),
    "cone": dict(amp=0.1, lead=0.92, limbs=(0, 0), start=(0, 0), elev=(0, 0)),
}
HANG = 5  # a weeping willow's curtain hangs this many voxels below its crown's base


class Crown:
    __slots__ = ("lz", "ly", "lx", "shade", "wz", "wy", "wx", "fy", "fx", "ftop")


def make_crown(spk, Rv, Hv, var):
    """one crown shape in voxels: leaves (offsets, shade 0-4) and wood (limbs), z from the crown's base, x and y from
    the trunk; and its footprint (top leaf per column)"""
    sp = SPECIES[spk]
    form = sp.form
    P = FORM[form]
    rs = np.random.default_rng([NAMES.index(spk), Rv, Hv, var])
    R, Hc = float(max(Rv, 1)), float(max(Hv, 2))
    n = Rv + 2
    z0 = -HANG if form == "weep" else 0
    zz, yy, xx = np.ogrid[z0:Hv + 2, -n:n + 1, -n:n + 1]
    zz, yy, xx = zz.astype(np.float32), yy.astype(np.float32), xx.astype(np.float32)
    shape = (Hv + 2 - z0, 2 * n + 1, 2 * n + 1)
    noise = 0.65 * vnoise(shape, 4, rs) + 0.35 * vnoise(shape, 2, rs)
    if form == "cone":
        zr = np.clip(zz / Hc, 0, 1)
        rad = R * (1 - zr) ** 0.9
        if spk in ("spruce", "cedar", "larch", "metaseq"):  # drooping tiers: each widens downwards
            tier = max(3.0, Hc / (5 if spk == "cedar" else 7))
            rad = rad * (0.78 + 0.22 * ((zz % tier) / tier))
        f = (xx ** 2 + yy ** 2) / np.maximum(rad, 0.35) ** 2
        f = np.where((zz < 0) | (zz > Hc), np.inf, f)
        zmid, half = Hc / 2, Hc / 2
    else:
        ells = []
        if form == "pine":  # flat clusters of needles high on the trunk, the top one smallest
            ells.append((0.0, 0.0, Hc * 0.6, 0.45 * R, 0.3 * Hc))
            for i in range(int(rs.integers(3, 6))):
                az, d = rs.uniform(0, 2 * math.pi), rs.uniform(0.25, 0.6) * R
                ells.append((d * math.cos(az), d * math.sin(az), Hc * rs.uniform(0.3, 0.9), R * rs.uniform(0.38, 0.55),
                             max(1.5, Hc * rs.uniform(0.12, 0.2))))
        else:
            ells.append((0.0, 0.0, P["zc"] * Hc, P["a"] * R, P["c"] * Hc / 2))
            for i in range(int(rs.integers(*P["n"]))):
                az = rs.uniform(0, 2 * math.pi)
                el = math.asin(rs.uniform(*P["el"]))
                d = rs.uniform(*P["d"])
                la = rs.uniform(*P["la"])
                ells.append((d * R * math.cos(el) * math.cos(az), d * R * math.cos(el) * math.sin(az),
                             P["zc"] * Hc + d * Hc / 2 * math.sin(el), la * R, la * Hc / 2 * rs.uniform(0.8, 1.0)))
        e = np.array(ells, np.float64)
        reach = np.max(np.hypot(e[:, 0], e[:, 1]) + e[:, 3])  # scaled to the tree's radius and crown height
        e[:, [0, 1, 3]] *= R / reach
        lo, hi = np.min(e[:, 2] - e[:, 4]), np.max(e[:, 2] + e[:, 4])
        k = Hc / (hi - lo)
        e[:, 2] = (e[:, 2] - lo) * k
        e[:, 4] *= k
        f = np.full(shape, np.inf, np.float32)
        for ex, ey, ez, a, c in e:
            f = np.minimum(f, ((xx - ex) ** 2 + (yy - ey) ** 2) / a ** 2 + ((zz - ez) / c) ** 2)
        zmid, half = float(e[0, 2]), Hc / 2
    env = np.sqrt(f) <= 1 + P["amp"] * noise
    if form != "weep":
        env &= zz >= 0
    else:
        env &= zz >= 1
    clump = vnoise(shape, 2, rs)
    leaves = env.copy()
    if env.any():
        thr = np.quantile(clump[env], (1 - sp.dens) * 0.9)
        leaves &= clump >= thr
    if form == "weep":  # strands hang from the dome's rim almost to the ground
        has = leaves.any(0)
        low = leaves.argmax(0)
        rr = np.hypot(yy[0], xx[0])
        sel = has & (rr >= 0.55 * R) & (rs.random(has.shape) < 0.4)
        bottom = rs.integers(0, HANG + 2, has.shape)
        zi = np.arange(shape[0])[:, None, None]
        leaves |= sel[None] & (zi >= bottom[None]) & (zi < low[None])
    inner = ndimage.binary_erosion(leaves)
    s = 2.0 + 1.4 * np.clip((zz - zmid) / max(half, 1.0), -1, 1) + 0.9 * clump - 1.0 * inner
    lz, ly, lx = np.nonzero(leaves)
    cr = Crown()
    cr.shade = np.clip(np.round(s[lz, ly, lx]), 0, 4).astype(np.uint8)
    cr.lz, cr.ly, cr.lx = (lz + z0).astype(np.int8), (ly - n).astype(np.int8), (lx - n).astype(np.int8)
    # wood: the leader and the limbs, each with a fork, ending inside the crown
    pts = []

    def seg(p0, p1):
        m = int(np.linalg.norm(p1 - p0) / 0.35) + 2
        pts.append(p0[None] + np.linspace(0, 1, m)[:, None] * (p1 - p0)[None])

    def reach_in(p, d):  # how far from p along d the crown goes on
        ts = np.arange(0.5, 2 * n + Hc + 1, 0.5)
        q = np.round(p[None] + d[None] * ts[:, None]).astype(int)
        ok = (q[:, 2] >= z0) & (q[:, 2] < Hv + 2) & (np.abs(q[:, 1]) <= n) & (np.abs(q[:, 0]) <= n)
        ok[ok] = env[q[ok, 2] - z0, q[ok, 1] + n, q[ok, 0] + n]
        return float(ts[np.argmin(ok)] - 0.5) if not ok.all() else float(ts[-1])

    if P["lead"] > 0:
        seg(np.zeros(3), np.array([0.0, 0.0, P["lead"] * Hc]))
    nl = int(rs.integers(P["limbs"][0], P["limbs"][1] + 1))
    a0 = rs.uniform(0, 2 * math.pi)
    for i in range(nl):
        az = a0 + 2 * math.pi * i / nl + rs.uniform(-0.4, 0.4)
        el = math.radians(rs.uniform(*P["elev"]))
        p = np.array([0.0, 0.0, Hc * rs.uniform(*P["start"])])
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        L = 0.78 * reach_in(p, d) if form != "shrub" else Hc * 0.7
        if L < 1:
            continue
        q = p + d * L
        seg(p, q)
        if form == "weep":  # arching over and down
            seg(q, q + np.array([math.cos(az), math.sin(az), -0.6]) * 0.3 * R)
        pf = p + d * L * rs.uniform(0.45, 0.7)
        az2 = az + rs.choice([-1, 1]) * rs.uniform(0.4, 0.8)
        el2 = min(el + 0.2, 1.4)
        d2 = np.array([math.cos(el2) * math.cos(az2), math.cos(el2) * math.sin(az2), math.sin(el2)])
        L2 = 0.7 * reach_in(pf, d2)
        if L2 >= 1:
            seg(pf, pf + d2 * L2)
    if pts:
        w = np.unique(np.round(np.concatenate(pts)).astype(int), axis=0)
        w = w[(w[:, 2] >= z0) & (np.abs(w[:, 0]) <= n) & (np.abs(w[:, 1]) <= n)]
    else:
        w = np.zeros((0, 3), int)
    cr.wx, cr.wy, cr.wz = (w[:, 0].astype(np.int8), w[:, 1].astype(np.int8), w[:, 2].astype(np.int8))
    key = (cr.ly.astype(np.int32) + 64) * 256 + cr.lx.astype(np.int32) + 64
    o = np.lexsort((-cr.lz.astype(np.int32), key))
    first = np.ones(len(o), bool)
    first[1:] = key[o][1:] != key[o][:-1]
    cr.fy, cr.fx, cr.ftop = cr.ly[o][first], cr.lx[o][first], cr.lz[o][first]
    return cr


def orient(dx, dy, rot):
    dx, dy = dx.astype(np.int32), dy.astype(np.int32)
    if rot & 4:
        dx = -dx
    r = rot & 3
    return (dx, dy) if r == 0 else (-dy, dx) if r == 1 else (-dx, -dy) if r == 2 else (dy, -dx)


class Forest:
    """every tree of the map: species, class, size, crown and drawing parameters, as arrays"""

    def __init__(self, x, y, h0, r0, src, tags, ids, ctx, F, note):
        """x, y: trunk positions (1 m grid); h0, r0: the heights and radii drawn so far (or tagged); src per tree:
        'osm', 'row', 'wood', 'park', 'yard', 'street', 'scrub'; tags: OSM tags (or None); ids: OSM id (or None).
        ctx: per-tree arrays island, park, wood, buda (bool), d_water, d_bld (m), away (unit vectors from buildings)."""
        N = len(x)
        self.N, self.F = N, F
        qa, qb = np.round(np.asarray(x) * 4).astype(np.int64), np.round(np.asarray(y) * 4).astype(np.int64)
        oid = np.array([i or 0 for i in ids], np.int64)
        has = oid > 0
        qa, qb = np.where(has, oid & 0xFFFFFFFF, qa), np.where(has, (oid >> 32) + 7919, qb)
        row_of = {}
        for k in range(N):  # a tree row: its trees share the row's id; give each its place along the row
            if src[k] == "row":
                row_of.setdefault(ids[k], []).append(k)
        for rid, ks in row_of.items():
            qb[ks] = np.arange(len(ks)) + 104729
        U = [uhash(qa, qb, s) for s in range(12)]
        setting = []
        for k in range(N):
            s = src[k]
            if s in ("scrub", "yard"):
                st = s
            elif ctx["island"][k] and s != "street":
                st = "island"
            elif s == "wood" or (s in ("osm", "row") and ctx["wood"][k]):
                st = "hills" if ctx["buda"][k] else "park"
            elif s == "park" or (s in ("osm", "row") and ctx["park"][k]):
                st = "park"
            elif s in ("osm", "row") and (tags[k] or {}).get("denotation") == "garden":
                st = "yard"
            else:
                st = "narrow" if ctx["d_bld"][k] < 4.5 else "street"
            if st in ("park", "hills", "island") and (ctx["d_water"][k] < 12 or (ctx["d_water"][k] < 25 and U[0][k] < 0.5)):
                st = "bank"
            setting.append(st)
        for rid, ks in row_of.items():  # one setting and one species per row: its middle tree's
            m = ks[len(ks) // 2]
            for k in ks:
                setting[k] = setting[m]
        sp = []
        tagged = 0
        row_sp = {}
        for k in range(N):
            st = setting[k]
            key, leaf = species_of(tags[k]) if tags[k] else (None, None)
            if src[k] == "row" and key is None:
                key, leaf = row_sp.get(ids[k], (None, leaf))
            tagged += key is not None and src[k] == "osm"
            if key is None:
                u = U[1][k] if src[k] != "row" else uhash(ids[k] & 0xFFFFFFFF, 3, 1)
                if st == "scrub":
                    key = "scrub"
                elif leaf == "needle":
                    key = "larch" if (tags[k] or {}).get("leaf_cycle") == "deciduous" else pick(CONIFERS, u)
                else:
                    mix = MIX[st]
                    if leaf == "broad":
                        mix = {s_: w_ for s_, w_ in mix.items() if SPECIES[s_].cls != CONIFER}
                    key = pick(mix, u)
                if src[k] == "row":
                    row_sp[ids[k]] = (key, leaf)
            sp.append(key)
        self.sp = np.array([NAMES.index(k) for k in sp], np.int16)
        self.cls = np.array([SPECIES[k].cls for k in sp], np.uint8)
        self.setting = setting
        # sizes: within the species' range, by setting; tags win; rows nearly even
        uh, ur = U[3].copy(), U[4].copy()
        for rid, ks in row_of.items():
            u_ = uhash(rid & 0xFFFFFFFF, 5, 2)
            uh[ks] = np.clip(u_ + (uh[ks] - 0.5) * 0.15, 0, 1)
            ur[ks] = np.clip(u_ + (ur[ks] - 0.5) * 0.15, 0, 1)
        h, r, base = np.zeros(N), np.zeros(N), np.zeros(N)
        young = np.zeros(N, bool)
        for k in range(N):
            s_ = SPECIES[sp[k]]
            t = tags[k] or {}
            sc = SCALE[setting[k]] if s_.h[1] > 12 else 1.0  # big species grow smaller in streets, yards and on the hills
            hk = s_.h[0] + uh[k] * (s_.h[1] - s_.h[0])
            rk = s_.r[0] + (0.6 * uh[k] + 0.4 * ur[k]) * (s_.r[1] - s_.r[0])
            hk, rk = hk * sc, rk * sc * (0.8 if src[k] == "wood" else 1.0)  # crowded in a wood
            sd = str(t.get("start_date", ""))[:4]
            yg = (U[5][k] < YOUNG.get(setting[k], 0) * (0.4 if src[k] == "street" else 1.0)) or (sd.isdigit() and int(sd) >= 2016)
            if yg and s_.cls != CONIFER and s_.form not in ("shrub", "globe"):
                young[k] = True
                hk, rk = 4.5 + 3.0 * uh[k], 1.3 + 0.7 * ur[k]
            if t.get("height") or t.get("diameter_crown"):  # mapped sizes, as drawn so far
                hk = h0[k] if t.get("height") else hk
                rk = r0[k] if t.get("diameter_crown") else rk
            hk, rk = min(hk, 35.0), min(rk, 9.5)
            if setting[k] in CAP and not t.get("diameter_crown"):
                rk = min(rk, CAP[setting[k]], max(ctx["d_bld"][k] + 2.0, 1.5))
            bs = s_.base[0] + U[6][k] * (s_.base[1] - s_.base[0])
            if s_.form == "shrub":
                b = 0.0
            elif s_.form == "globe":
                b = max(hk - 1.9 * rk, 2.2)
            elif s_.form == "cone":
                b = bs * hk
            elif young[k]:
                b = 2.0 + 0.4 * U[6][k]
            else:
                b = max(bs * hk, 2.0 if s_.form == "weep" else 3.0 if setting[k] in ("street", "narrow") else 2.2)
            h[k], r[k], base[k] = hk, rk, min(b, hk - 1.5)
        self.young = young
        self.h, self.r = h.astype(np.float32), r.astype(np.float32)
        self.Rv = np.maximum(np.round(r * F), 1).astype(np.int16)
        self.Hv = (2 * np.maximum(np.round((h - base) * F / 2), 1)).astype(np.int16)
        self.bv = np.round(base * F).astype(np.int16)
        self.var = (U[7] * 3).astype(np.int8)
        self.rot = (U[8] * 8).astype(np.int8)
        self.tint = np.where(U[9] < 0.15, -1, np.where(U[9] > 0.85, 1, 0)).astype(np.int8)
        self.uid = (1 + (U[10] * 255).astype(np.int64) % 255).astype(np.uint8)
        forms = np.array([FORMS.index(SPECIES[k].form) for k in sp])
        big = (h >= 20) | ((h >= 17) & np.isin(self.cls, (PLANE, OAK, CHESTNUT, WILLOW)))
        self.thick = big & ~young & ~np.isin(forms, (FORMS.index("cone"), FORMS.index("column")))
        # a crown leans away from a facade close by (street trees grow towards the open street)
        push = np.clip(r - ctx["d_bld"] + 1.0, 0, np.minimum(1.5, 0.35 * r)) * (forms != FORMS.index("cone"))
        self.sx = np.round(ctx["away"][:, 0] * push * F).astype(np.int16)
        self.sy = np.round(ctx["away"][:, 1] * push * F).astype(np.int16)
        self.cx = np.floor(np.asarray(x) * F).astype(np.int32)
        self.cy = np.floor(np.asarray(y) * F).astype(np.int32)
        self.reach = int((self.Rv + np.maximum(np.abs(self.sx), np.abs(self.sy))).max(initial=0)) + 3 if N else 0
        self.cache = {}
        cnt = Counter(self.cls.tolist())
        note(f"trees: species from OSM's tags for {tagged} mapped trees; {int(young.sum())} young; settings "
             + ", ".join(f"{k} {v}" for k, v in Counter(setting).most_common()))
        note("trees by class: " + ", ".join(f"{CLASS_NAMES[c]} {cnt[c]} ({100 * cnt[c] / max(N, 1):.0f}%)"
                                           for c in sorted(cnt, key=lambda c: -cnt[c])))
        note("trees by species: " + ", ".join(f"{k} {v}" for k, v in Counter(sp).most_common(24)))

    def take(self, keep):
        """keep only the trees where keep is True"""
        for k_, v in list(vars(self).items()):
            if isinstance(v, np.ndarray) and len(v) == self.N:
                setattr(self, k_, v[keep])
        self.setting = [s for s, k in zip(self.setting, keep) if k]
        self.N = int(keep.sum())

    def crown(self, k):
        key = (int(self.sp[k]), int(self.Rv[k]), int(self.Hv[k]), int(self.var[k]))
        c = self.cache.get(key)
        if c is None:
            c = self.cache[key] = make_crown(NAMES[key[0]], *key[1:])
        return c

    def place(self, gz):
        """the ground z (fine voxels) under each trunk; top: the highest voxel a tree reaches"""
        self.gz = np.asarray(gz, np.int32)
        self.top = self.gz + self.bv + self.Hv + 3

    def cache_mb(self):
        return sum(c.lz.nbytes * 3 + c.shade.nbytes + c.wz.nbytes * 3 + c.fy.nbytes * 3 for c in self.cache.values()) / 2 ** 20

    def draw(self, vol, ks, r0, c0, roadw):
        """the trees ks into vol (z, rows r0.., cols c0..): all the wood first, then the leaves, each into empty voxels.
        Over a road (roadw) nothing but the trunk comes lower than 4.5 m above the trunk's foot."""
        H, R_, C_ = vol.shape
        clear = int(4.5 * self.F)
        for k in ks:
            sp = SPECIES[NAMES[self.sp[k]]]
            cr = self.crown(k)
            cx, cy, gz, bv = int(self.cx[k]), int(self.cy[k]), int(self.gz[k]), int(self.bv[k])
            ztr = bv + (min(6, int(self.Hv[k]) // 4) if self.thick[k] else 0)
            tz = np.arange(gz, gz + ztr)
            trunk = [(cx, cy)] + ([(cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)] if self.thick[k] else [])
            dx, dy = orient(cr.wx, cr.wy, int(self.rot[k]))
            X = np.concatenate([np.full(len(tz), a) for a, _ in trunk] + [cx + dx])
            Y = np.concatenate([np.full(len(tz), b) for _, b in trunk] + [cy + dy])
            Z = np.concatenate([tz] * len(trunk) + [gz + bv + cr.wz.astype(np.int32)])
            limb = np.arange(len(X)) >= len(tz) * len(trunk)
            ok = (X >= c0) & (X < c0 + C_) & (Y >= r0) & (Y < r0 + R_) & (Z >= 0) & (Z < H)
            X, Y, Z, limb = X[ok], Y[ok], Z[ok], limb[ok]
            ok = ~(limb & roadw[Y - r0, X - c0] & (Z < gz + clear))
            X, Y, Z = X[ok], Y[ok], Z[ok]
            ids = BARK_IDS[sp.bark]
            col = np.array(ids, np.uint16)[(vhash(X, Y, Z) * len(ids) * 0.999).astype(int)]
            free = vol[Z, Y - r0, X - c0] == 0
            vol[Z[free], Y[free] - r0, X[free] - c0] = col[free]
        for k in ks:
            sp = SPECIES[NAMES[self.sp[k]]]
            cr = self.crown(k)
            cx, cy, gz, bv = int(self.cx[k] + self.sx[k]), int(self.cy[k] + self.sy[k]), int(self.gz[k]), int(self.bv[k])
            dx, dy = orient(cr.lx, cr.ly, int(self.rot[k]))
            X, Y, Z = cx + dx, cy + dy, gz + bv + cr.lz.astype(np.int32)
            ok = (X >= c0) & (X < c0 + C_) & (Y >= r0) & (Y < r0 + R_) & (Z > gz) & (Z < H)
            X, Y, Z, s = X[ok], Y[ok], Z[ok], cr.shade[ok]
            ok = (vhash(X, Y, Z) > (0.25 if sp.form == "shrub" else 0.16)) & ~(roadw[Y - r0, X - c0] & (Z < gz + clear))
            X, Y, Z, s = X[ok], Y[ok], Z[ok], s[ok]
            col = np.array(FOLIAGE_IDS[sp.leaf], np.uint16)[np.clip(s.astype(np.int16) + self.tint[k], 0, 4)]
            free = vol[Z, Y - r0, X - c0] == 0
            vol[Z[free], Y[free] - r0, X[free] - c0] = col[free]

    def plane(self, cols, rows, cell):
        """per cell of `cell` fine voxels: the class of the tree whose crown is highest there (0: none), and that tree's
        byte (1-255)"""
        zb = np.full((rows, cols), -1, np.int32)
        cl = np.zeros((rows, cols), np.uint8)
        ui = np.zeros((rows, cols), np.uint8)
        for k in range(self.N):
            cr = self.crown(k)
            dx, dy = orient(cr.fx, cr.fy, int(self.rot[k]))
            ci = (self.cx[k] + self.sx[k] + dx) // cell
            cj = (self.cy[k] + self.sy[k] + dy) // cell
            zt = self.gz[k] + self.bv[k] + cr.ftop.astype(np.int32)
            ok = (ci >= 0) & (ci < cols) & (cj >= 0) & (cj < rows)
            if not ok.any():
                continue
            ci, cj, zt = ci[ok], cj[ok], zt[ok]
            i0, j0 = ci.min(), cj.min()
            loc = np.full((cj.max() - j0 + 1, ci.max() - i0 + 1), -1, np.int32)
            np.maximum.at(loc, (cj - j0, ci - i0), zt)
            sub = zb[j0:j0 + loc.shape[0], i0:i0 + loc.shape[1]]
            up = loc > sub
            sub[up] = loc[up]
            cl[j0:j0 + loc.shape[0], i0:i0 + loc.shape[1]][up] = self.cls[k]
            ui[j0:j0 + loc.shape[0], i0:i0 + loc.shape[1]][up] = self.uid[k]
        return cl, ui


def leaf_lut(n):
    """palette id -> foliage class (0: not a tree's leaf)"""
    lut = np.zeros(max(n, 1), np.uint8)
    for i, c in LEAF_CLASS.items():
        if i < n:
            lut[i] = c
    return lut


def check(vol, r0, c0, cl, j0, i0, cell, lut):
    """the class grid against a built window: of the columns whose top leaf is a tree's, the share whose cell has a
    class, and has that leaf's class"""
    top = np.zeros(vol.shape[1:], np.uint8)
    for z in range(vol.shape[0]):  # bottom up: the highest tree leaf wins
        c = lut[np.minimum(vol[z], len(lut) - 1)]
        top = np.where(c > 0, c, top)
    yy, xx = np.nonzero(top)
    if not len(yy):
        return "no tree leaves"
    pc = cl[(yy + r0) // cell - j0, (xx + c0) // cell - i0]
    vc = top[yy, xx]
    return (f"{len(yy)} columns with tree leaves: {100 * (pc > 0).mean():.1f}% in a cell with a class, "
            f"{100 * (pc == vc).mean():.1f}% of the leaf's class")
