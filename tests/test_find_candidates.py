import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/rule-clash-check/find_candidates.py"
FIXTURE = ROOT / "tests/fixtures/CLAUDE.md"
spec = importlib.util.spec_from_file_location("find_candidates", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.rules = helper.extract_rules([FIXTURE])
        self.pairs = helper.find_candidates(self.rules)
        self.planted = {(3, 4), (5, 6), (7, 8)}

    def test_all_planted_pairs(self):
        found = {(p["a"]["line"], p["b"]["line"]) for p in self.pairs}
        self.assertTrue(self.planted <= found)
        self.assertEqual(len(self.pairs), 3)

    def test_top_three_are_planted_pairs(self):
        self.assertEqual({(p["a"]["line"], p["b"]["line"])
                          for p in self.pairs[:3]}, self.planted)
        scores = [p["score"] for p in self.pairs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_fenced_code_is_ignored(self):
        self.assertFalse(any("secret example" in r["text"] for r in self.rules))
        self.assertEqual(sum(r["file"] == str(FIXTURE) for r in self.rules), 25)

    def test_import_is_followed(self):
        imported = [r for r in self.rules if Path(r["file"]).name == "extra.md"]
        self.assertEqual(imported, [{"file": str(FIXTURE.parent / "extra.md"),
                                    "line": 1, "text": "- Pack fragile ceramics with padding."}])

    def test_json_cli(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE), "--json"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), self.pairs)
        self.assertEqual(result.stderr, "")

    def test_missing_file_warns_and_exits_zero(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE / "missing.md"),
                                 "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertIn("Warning:", result.stderr)

    def test_extraction_and_import_boundaries(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            root = Path(directory)
            (root / "root.md").write_text(
                "Heading\nWe MUST label packages.\n* Store invoices safely.\n"
                "1. Sort receipts.\n~~~python\n- Never label packages.\n"
                "```\n- Always label packages.\n~~~~\n"
                "@child.md\n@missing.md\n", encoding="utf-8")
            (root / "child.md").write_text("- Keep folders tidy.\n@nested.md\n", encoding="utf-8")
            (root / "nested.md").write_text("- Hide nested example.\n", encoding="utf-8")
            warnings = io.StringIO()
            with contextlib.redirect_stderr(warnings):
                rules = helper.extract_rules([root / "root.md", root / "child.md"])
            self.assertEqual([r["line"] for r in rules[:3]], [2, 3, 4])
            self.assertEqual(len(rules), 5)
            self.assertEqual(sum("folders" in r["text"] for r in rules), 1)
            self.assertIn("missing.md", warnings.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                shallow = helper.extract_rules([root / "root.md"])
            self.assertEqual(len(shallow), 4)

    def test_value_changes_and_polarity(self):
        for first, second in [("9 AM", "10 AM"), ("$500", "$1,000"),
                              ("Monday", "Friday"), ("2026-01-02", "2026-02-02")]:
            with self.subTest(first=first):
                rules = [{"file": "rules.md", "line": 1, "text": f"- Set invoice limit {first}."},
                         {"file": "rules.md", "line": 2, "text": f"- Set invoice limit {second}."}]
                pairs = helper.find_candidates(rules)
                self.assertEqual(len(pairs), 1)
                self.assertEqual(pairs[0]["score"], 3)
        self.assertEqual(helper.values("1. Set invoice limit $1,000."),
                         helper.values("2. Set invoice limit $1000."))
        self.assertFalse(helper.NEGATIVE.search("- Notify another notebook owner."))
        self.assertEqual(helper.find_candidates([
            {"file": "a", "line": 1, "text": "- Always archive invoices."},
            {"file": "b", "line": 1, "text": "- Always archive invoices."}]), [])

    def test_threshold_and_limit(self):
        self.assertEqual(helper.find_candidates(self.rules, min_shared=5), [])
        rules = [{"file": "rules.md", "line": n,
                  "text": f"- Set invoice limit {n}."} for n in range(30)]
        self.assertEqual(len(helper.find_candidates(rules)), 200)

    def test_invalid_arguments_exit_zero(self):
        for arguments in ([], [str(FIXTURE), "--min-shared", "bad"],
                          [str(FIXTURE), "--min-shared", "0"]):
            result = subprocess.run([sys.executable, str(SCRIPT), *arguments], capture_output=True)
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
