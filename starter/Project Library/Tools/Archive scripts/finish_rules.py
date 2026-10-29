"""Finish inference for projects without a suggested finish, and metal/roughness-only Substance 3D Painter recipes per finish.

Revised 2026-10-29: the user can only use the Metallic and Roughness channels (no clear-coat or coat channel), so every recipe fakes the
clear coat with roughness and fakes candy, pearl and colour-shift with base colour, metallic and gradient maps.
"""

NAME_RULES = [
    ("Chrome", "Chrome"), ("Foil", "Colour-shift"), ("Hologram", "Colour-shift"), ("Oil Slick", "Colour-shift"), ("Pearl", "Pearl"),
    ("Opal", "Pearl"), ("Abalone", "Pearl"), ("Candy", "Candy"), ("Patina", "Patina"), ("Rust", "Patina"), ("Verdigris", "Patina"),
    ("Burn", "Heat tint"), ("Titanium", "Heat tint"), ("Anodised", "Anodised"), ("Concrete", "Textured"), ("Sand", "Textured"),
    ("Dune", "Textured"), ("Mesa", "Textured"), ("Gravel", "Textured"), ("Matte", "Matte"), ("Ash", "Matte"), ("Smoke", "Matte"),
    ("Cassette", "Matte"), ("Mono", "Matte"), ("Neon", "Fluorescent"), ("Voltage", "Fluorescent"), ("Acid", "Fluorescent"),
    ("Toxic", "Fluorescent"), ("Sodium", "Fluorescent"), ("Glacier", "Pearl"), ("Frost", "Pearl"), ("Kintsugi", "Metallic flake"),
    ("Copper", "Metallic flake"), ("Gold", "Metallic flake"), ("Sorbet", "Satin"), ("Milk", "Satin"),
]
MOOD_RULES = {"neon": "Fluorescent", "metal": "Metallic flake", "ice": "Pearl", "fire": "Candy", "gold": "Metallic flake", "night": "Gloss",
              "earth": "Matte", "desert": "Textured", "forest": "Satin", "water": "Gloss", "storm": "Satin", "sakura": "Pearl",
              "toxic": "Candy", "dragon": "Candy", "light": "Satin", "retro": "Satin", "pop": "Gloss", "bio": "Satin",
              "cosmos": "Metallic flake", "mineral": "Pearl"}


def infer_finish(name, moods):
    for key, fin in NAME_RULES:
        if key.lower() in name.lower():
            return fin
    for m in moods:
        if m in MOOD_RULES:
            return MOOD_RULES[m]
    return "Satin"


# (metallic of the base paint, roughness of the base paint, how the clear-coat look is faked, layer recipe)
PBR = {
    "Gloss": ("0.00", "0.06-0.12", "low roughness is the clear coat (a dielectric at 0.08 gives the sharp wet-look highlight)",
              ["Fill with the base hex, Metallic 0, Roughness 0.08.", "Do not go below 0.05: the highlight clips and shows aliasing. Add fine orange-peel noise to Normal (strength 0.02-0.05) and +/- 0.02 to Roughness so big flat panels do not look CG-perfect.", "Let curvature raise roughness a little on edges and panel gaps."]),
    "Satin": ("0.00", "0.30-0.40", "roughness 0.30-0.40 gives a soft sheen",
              ["Fill with the base hex, Metallic 0, Roughness 0.35.", "Add +/- 0.05 roughness noise so the sheen breaks up softly.", "Let curvature and wear raise roughness slightly on edges."]),
    "Matte": ("0.00", "0.65-0.80", "none (matte has no clear coat)",
              ["Fill with the base hex, Metallic 0, Roughness 0.72.", "Add +/- 0.08 roughness noise so the panel is not flat.", "Dark matte colours render darker than the hex: lift them 5-10 % and compare in the viewport."]),
    "Candy": ("0.90-1.00", "0.08-0.18", "a metal tinted by a saturated colour reads as candy over silver; the real translucent layer cannot be made in metal/roughness",
              ["Fill with the candy hex made darker and more saturated than the swatch: a metal reflects its base colour, so the brightness comes from the environment.", "Metallic 1.0 (0.9 keeps the colour a little stronger), Roughness 0.12.", "Optional: very fine flake noise in Roughness (-0.05) for the sparkle.", "Check under two HDRIs (bright sky and dark studio): candy that looks right in only one is too dark or too light."]),
    "Pearl": ("0.25-0.45", "0.12-0.22", "roughness 0.12-0.22 on a partly metallic base gives the soft glow of a pearl coat",
              ["Fill with the base hex, Metallic 0.35, Roughness 0.18.", "Add a pearl layer: a lighter, hue-shifted tint of the base hex (white-lilac or white-gold) as a gradient driven by curvature or world-space normals at 15-25 % opacity.", "The shift is baked into the texture and does not move with the viewing angle; keep it subtle."]),
    "Colour-shift": ("0.80-0.95", "0.12-0.20", "low roughness on a mostly metallic base",
                     ["Fill with the first palette hex, Metallic 0.9, Roughness 0.16.", "Apply a gradient map from the first to the last palette colour, driven by world-space normals or position, so the hue changes across the shape of the panel.", "This is a static fake of a colour flip (it does not change with the viewing angle); use it on large curved panels where the change looks natural."]),
    "Metallic flake": ("0.00 base, 1.00 on flakes", "0.10-0.15 base, 0.25-0.35 on flakes", "the paint stays glossy; only the flakes are metal",
                       ["Fill with the base hex, Metallic 0, Roughness 0.12.", "Add a flake layer: a high-frequency noise or 'metal flakes' mask (cell size about 0.5-1 mm on the car, 15-30 % coverage) that sets Metallic 1.0 and Roughness 0.30 on the flakes, with a slightly lighter tint of the hex.", "Add the same noise to Normal at low strength so the flakes sparkle when the light moves; keep the flakes small, big ones look like glitter."]),
    "Chrome": ("1.00", "0.02-0.05", "a polished metal: nothing to fake",
               ["Fill with a very light grey (#E6E6E6), tinted 5 % toward the base hex, Metallic 1.0, Roughness 0.03.", "Roughness exactly 0 can band or alias: use 0.02-0.03.", "Chrome shows only reflections: check it under a studio HDRI with clear horizon lines."]),
    "Fluorescent": ("0.00", "0.20-0.30", "roughness 0.20-0.30 keeps a bright but soft highlight",
                    ["Fill with the base hex brightened 10-15 % (the lit result is darker than the swatch), Metallic 0, Roughness 0.25.", "Use an Emissive channel at 5-15 % only if your exporter and the game support it; otherwise rely on the brighter base colour.", "Avoid tonemapping that desaturates neon hues; test in the game lighting."]),
    "Textured": ("0.00", "0.75-0.90", "none (high roughness)",
                 ["Fill with the base hex, Metallic 0, Roughness 0.82.", "Add a high-frequency grain to Normal and Height (sand, stone or structure), strength 0.3-0.5.", "Vary Roughness with the same grain (+/- 0.1)."]),
    "Patina": ("0.60-0.90 on exposed metal, 0.00 on paint", "0.45-0.70", "none (high roughness)",
               ["Fill with the base hex, Metallic 0.7, Roughness 0.50.", "Use a curvature or cavity generator to push verdigris or rust colour into the recesses (Metallic 0 and Roughness up to 0.8 there).", "Add edge wear that exposes brighter metal (Metallic 1.0, Roughness 0.3) on convex edges."]),
    "Heat tint": ("1.00", "0.25-0.40", "polished metal with coloured bands",
                  ["Fill with grey metal (#9A9AA3), Metallic 1.0, Roughness 0.30.", "Map a gradient (straw, gold, purple, blue) onto a heat-distance mask so colour bands follow edges and weld lines.", "Keep Roughness slightly higher in the coloured bands."]),
    "Anodised": ("1.00", "0.30-0.45", "metal with a satin finish",
                 ["Fill with the base hex (anodised colours stay saturated and metallic), Metallic 1.0, Roughness 0.38.", "Add fine brushed grain in Normal (stretched noise, strength 0.2).", "Keep edge wear bright silver for the exposed aluminium."]),
}
VINYL_R = {"Gloss": "0.12", "Candy": "0.12", "Chrome": "0.12", "Pearl": "0.14", "Colour-shift": "0.14", "Metallic flake": "0.12", "Fluorescent": "0.20", "Satin": "0.32",
           "Matte": "0.55", "Textured": "0.55", "Patina": "0.30", "Heat tint": "0.30", "Anodised": "0.30"}
