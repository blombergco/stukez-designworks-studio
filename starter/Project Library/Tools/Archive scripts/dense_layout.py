"""Dense (Animal Style reference) sponsor layout: 36 slots on the 12 zones. star = also in the clean 12-zone kit."""

# id, zone, label, size, star, preference zone (index into SLOTS zone numbers), view, x, y
D = [
    ("1a", 1, "Windshield banner (title)", "L", True, 1, "side", 388, 108),
    ("2a", 2, "Hood, large mark", "M", True, 2, "top", 700, 80),
    ("2b", 2, "Hood, small", "S", False, 2, "top", 745, 62),
    ("2c", 2, "Hood, small", "S", False, 2, "top", 678, 62),
    ("2d", 2, "Hood, small", "S", False, 2, "top", 690, 106),
    ("2e", 2, "Hood, filler", "XS", False, 2, "top", 752, 102),
    ("3a", 3, "Front bumper / lip", "M", True, 3, "side", 540, 186),
    ("3b", 3, "Front bumper, small", "S", False, 3, "side", 522, 198),
    ("3c", 3, "Front bumper, filler", "XS", False, 3, "top", 720, 40),
    ("4a", 4, "Front fender", "M", True, 4, "side", 445, 164),
    ("4b", 4, "Front fender, small", "S", False, 4, "side", 472, 176),
    ("4c", 4, "Front fender, small", "S", False, 4, "side", 415, 172),
    ("4d", 4, "Front fender, filler", "XS", False, 4, "side", 430, 148),
    ("5a", 5, "Door upper", "L", True, 5, "side", 300, 150),
    ("5b", 5, "Lower-door hero mark", "L", False, 5, "side", 300, 184),
    ("5c", 5, "Door, small", "S", False, 5, "side", 350, 168),
    ("6a", 6, "Side skirt strip", "S", True, 6, "side", 230, 200),
    ("6b", 6, "Side skirt strip", "XS", False, 6, "side", 262, 200),
    ("6c", 6, "Side skirt strip", "XS", False, 6, "side", 294, 200),
    ("6d", 6, "Side skirt strip", "XS", False, 6, "side", 326, 200),
    ("6e", 6, "Side skirt strip", "XS", False, 6, "side", 358, 200),
    ("7a", 7, "Rear quarter", "M", True, 7, "side", 190, 168),
    ("7b", 7, "Rear quarter, small", "S", False, 7, "side", 165, 152),
    ("7c", 7, "Rear quarter, small", "S", False, 7, "side", 214, 178),
    ("7d", 7, "Rear quarter, filler", "XS", False, 7, "side", 180, 188),
    ("8a", 8, "Roof", "M", True, 8, "top", 720, 224),
    ("9a", 9, "Trunk lid", "M", True, 9, "top", 720, 372),
    ("9b", 9, "Trunk, small", "S", False, 9, "top", 690, 392),
    ("9c", 9, "Wing end plate, left", "S", False, 9, "top", 672, 420),
    ("9d", 9, "Wing end plate, right", "S", False, 9, "top", 768, 420),
    ("10a", 10, "Rear bumper", "S", True, 10, "side", 80, 190),
    ("10b", 10, "Rear bumper, filler", "XS", False, 10, "side", 96, 198),
    ("11a", 11, "Mirror, left", "XS", True, 11, "top", 642, 152),
    ("11b", 11, "Mirror, right", "XS", False, 11, "top", 798, 152),
    ("12a", 12, "Rear / side glass", "S", True, 12, "side", 215, 124),
    ("12b", 12, "Rear / side glass", "S", False, 12, "side", 245, 120),
]
SIZE_WORD = {"L": "large (40-60 % of panel width)", "M": "medium (25-40 %)", "S": "small (10-20 %)", "XS": "filler (5-10 %)"}
RADIUS = {"L": 14, "M": 11, "S": 8, "XS": 5}
assert len(D) == 36 and sum(1 for x in D if x[4]) == 12
