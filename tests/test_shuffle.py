"""Shuffle: where the items of a view go, with a seeded random generator so the results can be checked."""
import random
import unittest

from stukez_studio import board as bd


class Midpoint:
    """Stands in for random: every range gives its middle, and nothing is shuffled, so the spots come out in order."""
    def shuffle(self, seq):
        pass

    def uniform(self, a, b):
        return (a + b) / 2

    def choice(self, seq):
        return seq[0]


def items():
    sponsor = bd.default_item("sponsor", "side", "Logos/a.png", "A")
    other = bd.default_item("sponsor", "side", "Logos/b.png", "B")
    other["colour"]["mode"] = "sponsor_b"
    tribal = bd.default_item("tribal", "side", "Logos/t.png", "T")
    return [sponsor, other, tribal]


class ShuffleTests(unittest.TestCase):
    def test_keeps_every_item_and_its_view(self):
        its = items()
        bd.shuffle_items(its, side=True, rng=random.Random(1))
        self.assertEqual(len(its), 3)
        self.assertTrue(all(it["view"] == "side" for it in its))

    def test_tribals_stay_across_the_body(self):
        its = items()
        bd.shuffle_items(its, side=True, rng=random.Random(2))
        tribal = its[2]
        self.assertTrue(.38 <= tribal["x"] <= .62)
        self.assertTrue(.5 <= tribal["y"] <= .62)
        self.assertTrue(.32 <= tribal["w"] <= .55)

    def test_sponsor_sizes_and_positions_are_in_range(self):
        for seed in range(20):
            its = items()
            bd.shuffle_items(its, side=True, rng=random.Random(seed))
            for it in its[:2]:
                self.assertTrue(0 <= it["x"] <= 1)
                self.assertTrue(.09 <= it["w"] <= .2)

    def test_original_colours_are_kept_and_others_take_sponsor_a_or_b(self):
        for seed in range(20):
            its = items()
            bd.shuffle_items(its, side=True, rng=random.Random(seed))
            self.assertEqual(its[0]["colour"]["mode"], "original")
            self.assertIn(its[1]["colour"]["mode"], ("sponsor_a", "sponsor_b"))

    def test_same_seed_gives_the_same_result(self):
        a, b = items(), items()
        bd.shuffle_items(a, side=True, rng=random.Random(7))
        bd.shuffle_items(b, side=True, rng=random.Random(7))
        self.assertEqual([(i["x"], i["y"], i["rot"]) for i in a], [(i["x"], i["y"], i["rot"]) for i in b])

    def test_front_on_the_right_mirrors_the_side_spots(self):
        left, right = items(), items()
        bd.shuffle_items(left, side=True, front_right=False, rng=Midpoint())
        bd.shuffle_items(right, side=True, front_right=True, rng=Midpoint())
        self.assertEqual(left[0]["x"], .52)     # the first spot of SHUFFLE_SPOTS, with no noise
        self.assertEqual(right[0]["x"], .48)

    def test_other_views_are_placed_anywhere_on_the_view(self):
        its = items()
        bd.shuffle_items(its, side=False, rng=random.Random(4))
        for it in its[:2]:
            self.assertTrue(.3 - .02 <= it["x"] <= .7 + .02)
            self.assertTrue(.2 - .02 <= it["y"] <= .8 + .02)


if __name__ == "__main__":
    unittest.main()
