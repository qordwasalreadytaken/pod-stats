import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_pipeline", ROOT / "scripts" / "site_pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def fixture(root):
    for directory in pipeline.ASSET_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for page in pipeline.PAGES:
        content = '<html><head><script data-site-root="./"></script></head><body></body></html>'
        if page == "items.html":
            content = content.replace("</body>", "<script>fetch(`jsons/${filename}`)</script></body>")
        (root / page).write_text(content)
    (root / "js" / "archive-banner.js").write_text("// banner")
    (root / "item-bases.js").write_text("// items")
    (root / "jsons").mkdir()
    for name in ("full-sets.js", "items_list.json"):
        (root / "jsons" / name).write_text("{}")
    (root / "Season").mkdir()


def data(root, metadata):
    (root / "jsons").mkdir(exist_ok=True)
    for mode in ("sc", "hc"):
        pipeline.write_json(root / f"{mode}_ladder.json", [{"Name": mode}])
        pipeline.write_json(root / "jsons" / f"{mode}_ladder.json", [{"Name": mode}])
        pipeline.write_json(root / "jsons" / f"{mode}-funfacts.json", [{"Name": mode}])
    pipeline.write_json(root / pipeline.STATE, metadata)


class SeasonTests(unittest.TestCase):
    def test_selects_current_and_most_recent_post_season(self):
        seasons = [{"season": 12, "current": False}, {"season": 13, "current": False}]
        with patch.object(pipeline, "get_json", return_value=seasons):
            self.assertEqual(pipeline.get_season(None)["status"], "post-season")
            seasons[0]["current"] = True
            self.assertEqual(pipeline.get_season(None)["season"], 12)

    def test_unknown_season_fails_closed(self):
        with patch.object(pipeline, "get_json", return_value=[]):
            with self.assertRaises(ValueError):
                pipeline.get_season(None)

    def test_invalid_page_fails_instead_of_publishing_partial_data(self):
        with patch.object(pipeline, "get_json", return_value={"error": "unavailable"}):
            with self.assertRaises(ValueError):
                pipeline.ladder_page(None, 13, 0, 0, 0)

    def test_collection_writes_expected_browser_datasets(self):
        row = {"charName": "Test", "rank": 1, "charClass": "ama", "level": 75, "account": "acct"}
        character = {"Name": "Test", "Class": "Amazon", "Stats": {"Level": 75},
                     "Inventory": [], "Equipped": [], "SkillTabs": []}
        firsts = [{"season": 13, "gameMode": 0, "charName": "Test", "charLevel": 75,
                   "charClass": "ama", "difficulty": "Hell", "bossName": "Diablo"}]
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pipeline, "ladder_page", return_value=[row]) as ladder_page, \
             patch.object(pipeline, "get_json", return_value=character):
            root = Path(temp)
            self.assertEqual(pipeline.collect_mode(None, 13, 0, root, firsts), 1)
            self.assertEqual(pipeline.read_json(root / "sc_ladder.json"), [character])
            self.assertEqual(pipeline.read_json(root / "jsons/scamazon.json"), [character])
            self.assertEqual(len(pipeline.read_json(root / "jsons/sc-top1k.json")), 5)
            self.assertEqual(pipeline.read_json(root / "jsons/sc_ladder_summary.json")["ladderFirsts"][0]["kills"],
                             ["First Diablo Kill"])
            for class_id in pipeline.CLASSES:
                for page in range(1, 6):
                    ladder_page.assert_any_call(None, 13, 0, class_id, page)
            for name in ("charms", "mercs", "funfacts", "classleaders"):
                self.assertTrue((root / "jsons" / f"sc-{name}.json").exists())


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.metadata = {"season": 13, "status": "post-season", "captured_at": "2026-03-28T06:00:00+00:00",
                         "counts": {"sc": 1, "hc": 1}, "version": 1}
        data(self.root, self.metadata)

    def test_archive_copies_snapshot_and_is_immutable(self):
        self.assertTrue(pipeline.create_archive(self.root, self.root, self.metadata, "monthly", "2026-03"))
        archive = self.root / "Season/13/snapshots/2026-03"
        self.assertEqual(pipeline.read_json(archive / "sc_ladder.json"), [{"Name": "sc"}])
        self.assertFalse((archive / "jsons/sc_ladder.json").exists())
        self.assertIn("fetch(`${filename}`)", (archive / "items.html").read_text())
        self.assertIn("js/archive-banner.js", (archive / "home.html").read_text())
        self.assertIn('data-site-root="../../../../"', (archive / "home.html").read_text())
        self.assertIn("../../../../history.html", (archive / "history.html").read_text())
        pipeline.write_json(self.root / "sc_ladder.json", [{"Name": "changed"}])
        self.assertFalse(pipeline.create_archive(self.root, self.root, self.metadata, "monthly", "2026-03"))
        self.assertEqual(pipeline.read_json(archive / "sc_ladder.json"), [{"Name": "sc"}])

    def test_manifest_includes_legacy_and_new_paths(self):
        old = self.root / "Season/12"
        old.mkdir()
        (old / "Home.html").write_text("legacy")
        pipeline.create_archive(self.root, self.root, self.metadata, "monthly", "2026-03")
        entries = pipeline.generate_manifest(self.root)
        self.assertIn({"season": 12, "kind": "legacy", "label": "Season archive",
                       "url": "Season/12/Home.html"}, entries)
        self.assertTrue(any(entry["kind"] == "post-season" and entry["label"] == "March 2026"
                            for entry in entries))

    def test_frozen_transition_preserves_previous_snapshot_without_fetching(self):
        previous = {**self.metadata, "status": "active"}
        data(self.root, previous)
        now = datetime(2026, 3, 29, tzinfo=timezone.utc)
        with patch.object(pipeline, "get_season", return_value={"season": 13, "status": "post-season", "end": None}), \
             patch.object(pipeline, "collect_snapshot") as collect:
            pipeline.run(self.root, {"post_season_updates": False, "archive_day": 28}, now)
        collect.assert_not_called()
        self.assertTrue((self.root / "Season/13/Final/home.html").exists())
        self.assertIn('data-site-root="../../../"',
                      (self.root / "Season/13/Final/home.html").read_text())
        self.assertTrue(any(entry["url"].endswith("/Final/home.html")
                            for entry in pipeline.read_json(self.root / pipeline.MANIFEST)["archives"]))
        self.assertEqual(pipeline.read_json(self.root / pipeline.STATE), previous)

    def test_season_change_does_not_publish_staged_data(self):
        now = datetime(2026, 3, 10, tzinfo=timezone.utc)
        current = {"season": 13, "status": "active", "end": None}
        changed = {"season": 13, "status": "post-season", "end": None}

        def fake_collect(session, season, destination, timestamp):
            data(destination, {**self.metadata, "status": "active"})
            return {**self.metadata, "status": "active"}

        with patch.object(pipeline, "get_season", side_effect=[current, changed]), \
             patch.object(pipeline, "collect_snapshot", side_effect=fake_collect):
            with self.assertRaises(RuntimeError):
                pipeline.run(self.root, {"post_season_updates": True, "archive_day": 28}, now)
        self.assertEqual(pipeline.read_json(self.root / pipeline.STATE), self.metadata)

    def test_collection_failure_does_not_publish_partial_data(self):
        now = datetime(2026, 3, 10, tzinfo=timezone.utc)
        season = {"season": 13, "status": "post-season", "end": None}
        with patch.object(pipeline, "get_season", return_value=season), \
             patch.object(pipeline, "collect_snapshot", side_effect=RuntimeError("API unavailable")):
            with self.assertRaisesRegex(RuntimeError, "API unavailable"):
                pipeline.run(self.root, {"post_season_updates": True, "archive_day": 28}, now)
        self.assertEqual(pipeline.read_json(self.root / pipeline.STATE), self.metadata)
        self.assertEqual(pipeline.read_json(self.root / "sc_ladder.json"), [{"Name": "sc"}])

    def test_previous_month_is_recovered_from_last_valid_snapshot(self):
        now = datetime(2026, 4, 2, tzinfo=timezone.utc)
        season = {"season": 13, "status": "post-season", "end": None}
        with patch.object(pipeline, "get_season", return_value=season), \
             patch.object(pipeline, "collect_snapshot", side_effect=RuntimeError("API unavailable")):
            with self.assertRaises(RuntimeError):
                pipeline.run(self.root, {"post_season_updates": True, "archive_day": 28}, now)
        archive = self.root / "Season/13/snapshots/2026-03"
        self.assertEqual(pipeline.read_json(archive / "archive_metadata.json")["captured_at"],
                         self.metadata["captured_at"])


if __name__ == "__main__":
    unittest.main()
