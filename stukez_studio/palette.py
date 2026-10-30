"""Colour maths, palette generator and name generator.

Generated palettes follow the Project Library rules: base is a solid or a 2-colour gradient, tribals and
sponsors and outlines are solid or 2-colour gradients (the generator makes solid outlines), hex codes only.
"""
import colorsys
import random

# ---------------------------------------------------------------------- colour maths
def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(r, g, b):
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(x))) for x in (r, g, b)))


def hsl_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, max(0, min(1, l)), max(0, min(1, s)))
    return rgb_to_hex(r * 255, g * 255, b * 255)


def hex_hsl(h):
    r, g, b = (c / 255 for c in hex_to_rgb(h))
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, s, l


def luminance(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def text_on(h):
    return "#101018" if luminance(h) > 0.35 else "#F4F2FA"


def valid_hex(s):
    s = s.strip().upper()
    if len(s) == 6 and not s.startswith("#"):
        s = "#" + s
    return s if len(s) == 7 and s[0] == "#" and all(c in "0123456789ABCDEF" for c in s[1:]) else None


# ---------------------------------------------------------------------- moods
# hue anchors (degrees), saturation range, base lightness range; matches the moods used in the vault
MOODS = {
    "night":   dict(hues=(250, 270, 225, 290), sat=(.35, .70), base=(.07, .20)),
    "light":   dict(hues=(200, 40, 330, 150), sat=(.30, .65), base=(.72, .88)),
    "fire":    dict(hues=(0, 12, 25, 40), sat=(.70, .95), base=(.18, .40)),
    "earth":   dict(hues=(20, 30, 42, 65), sat=(.25, .50), base=(.18, .42)),
    "neon":    dict(hues=(300, 165, 185, 70, 330), sat=(.88, 1.0), base=(.07, .20)),
    "water":   dict(hues=(190, 200, 212, 175), sat=(.50, .80), base=(.14, .40)),
    "metal":   dict(hues=(210, 30, 200, 260), sat=(.05, .22), base=(.20, .55)),
    "gold":    dict(hues=(38, 45, 50, 30), sat=(.65, .90), base=(.15, .45)),
    "forest":  dict(hues=(100, 130, 150, 85), sat=(.30, .60), base=(.10, .32)),
    "storm":   dict(hues=(215, 240, 260, 200), sat=(.18, .45), base=(.12, .35)),
    "ice":     dict(hues=(185, 200, 210, 225), sat=(.20, .50), base=(.65, .88)),
    "pop":     dict(hues=(330, 55, 190, 280, 15), sat=(.75, .95), base=(.40, .62)),
    "toxic":   dict(hues=(75, 92, 280, 58), sat=(.70, .90), base=(.10, .30)),
    "sakura":  dict(hues=(335, 345, 320, 355), sat=(.30, .62), base=(.65, .88)),
    "bio":     dict(hues=(160, 140, 180, 300), sat=(.60, .90), base=(.08, .26)),
    "retro":   dict(hues=(30, 15, 180, 50), sat=(.45, .70), base=(.30, .62)),
    "desert":  dict(hues=(30, 40, 15, 50), sat=(.35, .62), base=(.48, .72)),
    "dragon":  dict(hues=(5, 140, 45, 200), sat=(.55, .85), base=(.10, .32)),
    "cosmos":  dict(hues=(260, 290, 320, 220), sat=(.50, .85), base=(.06, .22)),
    "mineral": dict(hues=(190, 160, 280, 20), sat=(.28, .60), base=(.20, .50)),
}
SCHEMES = ("Analogous", "Complementary", "Split complementary", "Triadic", "Mood mix")


def _shift(scheme, h, rng):
    return {"Analogous": [h + 30, h - 30],
            "Complementary": [h + 180, h + 165],
            "Split complementary": [h + 150, h + 210],
            "Triadic": [h + 120, h + 240]}.get(scheme) or [rng.choice([h + 60, h + 180, h + 120, h - 40]),
                                                            rng.choice([h + 200, h + 90, h - 120, h + 25])]


def _tint_dark(h, rng):
    return hsl_hex(h, rng.uniform(.25, .55), rng.uniform(.035, .075))


def _fill(h, s, l, rng, gradient_chance=.35):
    a = hsl_hex(h, s, l)
    if rng.random() < gradient_chance:
        b = hsl_hex(h + rng.choice([-28, -18, 18, 28]), min(1, s + .05), min(.9, l + rng.uniform(.08, .2)))
        return [a, b] if a != b else a
    return a


def generate(moods=(), scheme="Mood mix", seed_hue=None, rng=None):
    """A rule-conforming palette dict (base, tribal, sponsor_a, sponsor_b and their outlines)."""
    rng = rng or random.Random()
    pool = [MOODS[m] for m in moods if m in MOODS] or [rng.choice(list(MOODS.values()))]
    hues = [h for m in pool for h in m["hues"]]
    sat = (sum(m["sat"][0] for m in pool) / len(pool), sum(m["sat"][1] for m in pool) / len(pool))
    bl = (sum(m["base"][0] for m in pool) / len(pool), sum(m["base"][1] for m in pool) / len(pool))
    dark_base = bl[1] < .6
    best = None
    for _ in range(40):
        h0 = (seed_hue if seed_hue is not None else rng.choice(hues)) + rng.uniform(-12, 12)
        h1, h2 = _shift(scheme, h0, rng)
        s = rng.uniform(*sat)
        l0 = rng.uniform(*bl)
        base = [hsl_hex(h0, s * .9, l0), hsl_hex(h0 + rng.choice([-25, 25, 40]), min(1, s * 1.1),
                                                 min(.85, l0 + rng.uniform(.14, .26)))]
        if rng.random() < .25:
            base = base[0]
        # fills must read against the base: light on a dark base, deep on a light one
        fl = (.62, .80) if dark_base else (.18, .34)
        tribal = _fill(h1, min(1, s + .1), rng.uniform(*fl), rng)
        a = _fill(h2, min(1, s + .15), rng.uniform(.52, .70) if dark_base else rng.uniform(.24, .42), rng, .15)
        b = _fill(h0 + rng.choice([60, 180, 300]), min(1, s + .1), rng.uniform(*fl), rng, .5)
        outline = _tint_dark(h0, rng)
        cand = dict(base=base, tribal=tribal, tribal_outline=outline, sponsor_a=a, sponsor_a_outline=outline,
                    sponsor_b=b, sponsor_b_outline=outline)
        score = quality(cand)
        if best is None or score > best[0]:
            best = (score, cand)
        if score >= 3.0:
            break
    return best[1]


def _first(v):
    return v[0] if isinstance(v, list) else v


def quality(d):
    """Lowest contrast among the pairs that must stay readable (fill vs outline, tribal vs base)."""
    base_mid = _first(d["base"]) if not isinstance(d["base"], list) else d["base"][-1]
    pairs = [(c, o) for fill, line in (("tribal", "tribal_outline"), ("sponsor_a", "sponsor_a_outline"), ("sponsor_b", "sponsor_b_outline"))
             for c in _cl(d[fill]) for o in _cl(d[line])]
    pairs += [(_first(d["tribal"]), base_mid)]
    return min(contrast(a, b) for a, b in pairs)


def _cl(v):
    return v if isinstance(v, list) else [v]


def check_rules(d):
    """Problems against the Project Library rules; an empty list means the palette can be saved."""
    problems = []
    for key in ("base", "tribal", "tribal_outline", "sponsor_a", "sponsor_a_outline", "sponsor_b", "sponsor_b_outline"):
        v = d[key]
        if isinstance(v, list) and len(v) != 2:
            problems.append(f"{key}: a gradient needs exactly 2 colours")
        if not all(valid_hex(c) for c in _cl(v)):
            problems.append(f"{key}: invalid hex")
    return problems


# ---------------------------------------------------------------------- names
COLOUR_WORDS = {
    "Wasabi": "#6E8B1F", "Salmon": "#FA8072", "Cobalt": "#2150C8", "Lilac": "#B79AE0", "Pistachio": "#93C572",
    "Nightshade": "#3B2060", "Grape": "#6B2FA0", "Tangerine": "#F28500", "Mustard": "#D4A017", "Teal": "#128C8C",
    "Indigo": "#3F3FA8", "Crimson": "#B01030", "Ivory": "#F2ECD8", "Slate": "#5A6674", "Copper": "#B4673A",
    "Jade": "#2FA06B", "Amber": "#E8A010", "Coral": "#F26B5B", "Plum": "#6E2A5A", "Rose": "#E0709A",
    "Sage": "#9CAF88", "Rust": "#A8481C", "Ink": "#1C1C34", "Bone": "#E4DAC4", "Ash": "#8C8C94", "Moss": "#6B7A2F",
    "Lemon": "#EEE240", "Sky": "#7EC8F0", "Denim": "#3A5F8F", "Mint": "#8EE8B8", "Peach": "#FFB88A", "Wine": "#6D1A36",
    "Smoke": "#6E6A78", "Sand": "#D8BC8A", "Olive": "#7A7A2A", "Orchid": "#C65BC0", "Cherry": "#B81F3C", "Lime": "#B5E31B",
    "Violet": "#7A3FE0", "Fern": "#3F8F4A", "Marigold": "#F4B120", "Steel": "#6C8AA6", "Mauve": "#A57A9A", "Cocoa": "#5A3A28",
    "Cyan": "#10C8E0", "Magenta": "#D81B84", "Charcoal": "#2A2C34", "Pearl": "#ECE8F2", "Ember": "#E04A12", "Aqua": "#30D4C0",
}
NOUNS = {
    "night": ["Eclipse", "Midnight", "Static", "Dusk", "Void"], "light": ["Daybreak", "Haze", "Linen", "Glow", "Milk"],
    "fire": ["Burn", "Flare", "Ember", "Blaze", "Smelt"], "earth": ["Clay", "Ridge", "Dust", "Terrain", "Kiln"],
    "neon": ["Circuit", "Pulse", "Signal", "Arcade", "Strobe"], "water": ["Tide", "Lagoon", "Drift", "Current", "Dive"],
    "metal": ["Alloy", "Chrome", "Forge", "Rivet", "Plate"], "gold": ["Gild", "Crown", "Bullion", "Foil", "Ore"],
    "forest": ["Canopy", "Thicket", "Grove", "Moss", "Hollow"], "storm": ["Squall", "Thunder", "Gale", "Overcast", "Front"],
    "ice": ["Frost", "Glacier", "Rime", "Shard", "Floe"], "pop": ["Soda", "Bubble", "Sticker", "Riot", "Candy"],
    "toxic": ["Slick", "Spill", "Acid", "Fallout", "Vial"], "sakura": ["Petal", "Blush", "Bloom", "Silk", "Drift"],
    "bio": ["Spore", "Glow", "Culture", "Larva", "Algae"], "retro": ["Cassette", "Diner", "Tape", "Vinyl", "Arcade"],
    "desert": ["Mirage", "Dune", "Mesa", "Scorch", "Caravan"], "dragon": ["Scale", "Ember", "Fang", "Hoard", "Wyrm"],
    "cosmos": ["Nebula", "Orbit", "Quasar", "Drift", "Comet"], "mineral": ["Quartz", "Slate", "Geode", "Flint", "Shale"],
}
GENERIC = ["Tar", "Burn", "Circuit", "Soda", "Slick", "Haze", "Static", "Fade", "Rush", "Grain", "Pulse", "Spark"]


def nearest_colour_word(hexes):
    """The colour word closest to the most saturated, mid-light colour in the palette."""
    pick = max(hexes, key=lambda c: hex_hsl(c)[1] * (1 - abs(hex_hsl(c)[2] - .5)))
    r, g, b = hex_to_rgb(pick)
    return min(COLOUR_WORDS, key=lambda w: sum((x - y) ** 2 for x, y in zip((r, g, b), hex_to_rgb(COLOUR_WORDS[w]))))


def suggest_name(d, moods=(), taken=(), rng=None):
    rng = rng or random.Random()
    cols = [c for k in ("base", "tribal", "sponsor_a", "sponsor_b") for c in _cl(d[k])]
    first = nearest_colour_word(cols)
    others = sorted(COLOUR_WORDS, key=lambda w: sum((x - y) ** 2 for x, y in zip(hex_to_rgb(cols[0]), hex_to_rgb(COLOUR_WORDS[w]))))
    firsts = [first] + others[:3]
    nouns = [n for m in moods for n in NOUNS.get(m, [])] + GENERIC
    taken = {t.lower() for t in taken}
    for _ in range(80):
        name = f"{rng.choice(firsts)} {rng.choice(nouns)}"
        if name.lower() not in taken:
            return name
    return f"{first} {rng.choice(GENERIC)} {rng.randint(2, 99)}"
