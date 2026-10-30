"""Undo and redo of a board's items, with a fake clock so the grouping of quick changes is exact."""
import unittest

from stukez_studio import board as bd


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def items_with(x):
    return [dict(id="a", x=x, colour=dict(mode="original", value="#FFFFFF"))]


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.h = bd.History(clock=self.clock)

    def test_nothing_to_undo_or_redo_at_the_start(self):
        self.assertIsNone(self.h.undo(items_with(1)))
        self.assertIsNone(self.h.redo(items_with(1)))

    def test_undo_returns_the_state_before_the_change(self):
        now = items_with(0.1)
        self.h.snapshot(now, "move")
        back = self.h.undo(items_with(0.9))
        self.assertEqual(back[0]["x"], 0.1)

    def test_redo_returns_the_state_after_the_undo(self):
        self.h.snapshot(items_with(0.1), "move")
        self.h.undo(items_with(0.9))
        forward = self.h.redo(items_with(0.1))
        self.assertEqual(forward[0]["x"], 0.9)

    def test_snapshots_are_copies(self):
        live = items_with(0.1)
        self.h.snapshot(live, "move")
        live[0]["x"] = 0.5
        self.assertEqual(self.h.undo(items_with(0.5))[0]["x"], 0.1)

    def test_same_tag_within_a_second_is_one_step(self):
        self.h.snapshot(items_with(0.1), "slider")
        self.clock.now += 0.4
        self.h.snapshot(items_with(0.2), "slider")
        self.clock.now += 0.4
        self.h.snapshot(items_with(0.3), "slider")
        self.assertEqual(self.h.undo(items_with(0.4))[0]["x"], 0.1)
        self.assertIsNone(self.h.undo(items_with(0.1)))

    def test_same_tag_after_a_pause_is_a_new_step(self):
        self.h.snapshot(items_with(0.1), "slider")
        self.clock.now += 5
        self.h.snapshot(items_with(0.2), "slider")
        self.assertEqual(self.h.undo(items_with(0.3))[0]["x"], 0.2)

    def test_a_different_tag_starts_a_new_step(self):
        self.h.snapshot(items_with(0.1), "move")
        self.h.snapshot(items_with(0.2), "rotate")
        self.assertEqual(self.h.undo(items_with(0.3))[0]["x"], 0.2)
        self.assertEqual(self.h.undo(items_with(0.2))[0]["x"], 0.1)

    def test_a_new_change_clears_redo(self):
        self.h.snapshot(items_with(0.1), "move")
        self.h.undo(items_with(0.9))
        self.h.snapshot(items_with(0.5), "move")
        self.assertIsNone(self.h.redo(items_with(0.5)))

    def test_only_the_last_steps_are_kept(self):
        for i in range(bd.History.LIMIT + 10):
            self.clock.now += 5
            self.h.snapshot(items_with(i), "move")
        steps = 0
        while self.h.undo(items_with(-1)) is not None:
            steps += 1
        self.assertEqual(steps, bd.History.LIMIT)

    def test_clear_forgets_everything_including_the_group(self):
        self.h.snapshot(items_with(0.1), "move")
        self.h.clear()
        self.assertIsNone(self.h.undo(items_with(0.2)))
        self.h.snapshot(items_with(0.3), "move")    # same tag straight after a clear is a new step
        self.assertEqual(self.h.undo(items_with(0.4))[0]["x"], 0.3)


if __name__ == "__main__":
    unittest.main()
