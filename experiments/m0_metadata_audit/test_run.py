import copy
import unittest
from run import source_prefix, select_records, validate_records


class AuditTests(unittest.TestCase):
    def fixture(self):
        return [{"real_file": f"E:/data/original{i//2}-Scene-{i:03d}.mp4", "fake_file": f"E:/data/{i}.mp4", "fake_source": "t2vz" if i % 2 else "opensora"} for i in range(240)]

    def test_group_prefix_preserves_original_id(self):
        self.assertEqual(source_prefix("E:/data/--abc-def-Scene-021.mp4"), "--abc-def")

    def test_deterministic_source_group_selection(self):
        a = select_records(self.fixture(), 123)
        b = select_records(self.fixture(), 123)
        self.assertEqual(a, b)
        validate_records(a)
        self.assertEqual(len({r["group_id"] for r in a}), 120)

    def test_duplicate_content_rejected(self):
        a = select_records(self.fixture(), 123)
        for r in a:
            r["sha256"] = r["sample_id"]
        a[70]["sha256"] = a[0]["sha256"]
        with self.assertRaisesRegex(ValueError, "duplicate sha256"):
            validate_records(a, require_digest=True)

    def test_cross_role_group_rejected(self):
        a = select_records(self.fixture(), 123)
        a[37]["group_id"] = a[0]["group_id"]
        with self.assertRaisesRegex(ValueError, "duplicate group_id"):
            validate_records(a)


if __name__ == "__main__":
    unittest.main()
