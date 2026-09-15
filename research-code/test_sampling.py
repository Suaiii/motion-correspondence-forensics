import unittest
from sampling import fixed_rate_plan


class SamplingTests(unittest.TestCase):
    def test_eight_frames_not_seven(self):
        plan = fixed_rate_plan(8, 4)
        self.assertEqual(plan.indices, tuple(range(8)))
        self.assertEqual(plan.delta_times, (.25,) * 7)

    def test_downsample_same_rate(self):
        self.assertEqual(fixed_rate_plan(16, 8).indices, tuple(range(0, 16, 2)))
        self.assertEqual(fixed_rate_plan(60, 30).indices, (0, 7, 15, 22, 30, 37, 45, 52))

    def test_short_clip_rejected(self):
        with self.assertRaisesRegex(ValueError, "shorter"):
            fixed_rate_plan(44, 29.97)

    def test_low_fps_rejected(self):
        with self.assertRaisesRegex(ValueError, "below target"):
            fixed_rate_plan(8, 2)

    def test_actual_dt_not_silently_constant(self):
        plan = fixed_rate_plan(300, 29.97)
        self.assertEqual(len(plan.indices), 8)
        self.assertEqual(len(set(plan.indices)), 8)
        self.assertTrue(all(dt > 0 for dt in plan.delta_times))
        self.assertGreater(len(set(round(x, 8) for x in plan.delta_times)), 1)

    def test_nonfinite_fps_rejected(self):
        with self.assertRaises(ValueError):
            fixed_rate_plan(100, float('nan'))


if __name__ == "__main__":
    unittest.main()
