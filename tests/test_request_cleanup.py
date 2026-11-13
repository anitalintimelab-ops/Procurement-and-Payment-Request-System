"""Exercise the real cleanup handlers without deleting any live request."""
import ast
import datetime
import json
import tempfile
import unittest

import pandas as pd

from request_database_sync import PURGED_IDS, next_request_id
from test_request_save_reload import PAGES, PageHarness, PageRerun, PageStop


class CleanupTests(unittest.TestCase):
    selected = {"20260115-02", "20260115-03", "20260115-05"}

    def both_pages(self, scenario):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                h = PageHarness(page, folder)
                h.seed = pd.DataFrame([
                    {"單號": "20260115-01", "狀態": "待簽核"},
                    {"單號": "20260115-02", "狀態": "已核准", "影像Base64": "receipt-fixture" * 45},
                    {"單號": "20260115-03", "狀態": "已駁回", "初審人": "Reviewer",
                     "影像Base64": "rejected-fixture" * 45},
                    {"單號": "20260115-04", "狀態": "已核准"},
                    {"單號": "20260115-05", "狀態": "已刪除", "初審人": "Reviewer",
                     "複審人": "Finance", "影像Base64": "deleted-fixture" * 45},
                ]).fillna("")
                h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
                h.publish()
                scenario(h)

    def cleanup(self, h, selected, *, click=True, admin=True):
        st = h.env["st"]
        st.subheader = lambda *_: None
        st.button = lambda *_, **__: click
        def editor(frame, **kwargs):
            result = frame.copy()
            self.assertFalse(frame["狀態"].isin({"待簽核", "待複審"}).any())
            result["勾選刪除"] = result["單號"].isin(selected)
            return result
        st.data_editor = editor
        h.env.update(is_admin=admin, curr_name="Tester", CFO_NAME="Finance", menu="8. 表單資料庫")
        handler = next(n for n in ast.walk(h.tree) if isinstance(n, ast.If)
                       and ast.unparse(n.test) == "menu == '8. 表單資料庫'")
        try:
            exec(compile(ast.Module(body=[handler], type_ignores=[]), "cleanup_handler", "exec"), h.env)
        except PageRerun:
            pass

    @staticmethod
    def cloud(h):
        frame, error = h.env["_read_database_chunks"](str(h.path), {}, "test/repo", "main")
        assert not error, error
        return frame

    def test_cleanup_then_relogin_and_one_click_sync_with_stale_copy(self):
        def scenario(h):
            old_part_count = len([k for k in h.remote if ".part-" in k])
            self.assertGreater(old_part_count, 1)
            before = self.cloud(h).set_index("單號")
            self.cleanup(h, self.selected)
            self.assertEqual(h.errors, [])
            self.assertEqual(h.github.published, 1)
            frame = self.cloud(h)
            self.assertEqual(set(frame.attrs[PURGED_IDS]), self.selected)
            pd.testing.assert_frame_equal(frame.set_index("單號"), before.drop(index=list(self.selected)))
            self.assertLess(len([k for k in h.remote if ".part-" in k]), old_part_count)
            self.assertFalse(any(b"receipt-fixture" in value or b"deleted-fixture" in value
                                 for value in h.remote.values()))
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.state.clear()
            self.assertEqual(set(h.env["load_data"]()["單號"]), {"20260115-01", "20260115-04"})
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            # Use the real one-click database path; other files are outside cleanup scope.
            h.env["sync_to_github"] = lambda path: (
                h.env["sync_to_github_core"](path) if path == str(h.path) else (True, "fixture"))
            self.assertTrue(all(ok for _, ok, _ in h.env["sync_all_data_to_github"]()))
            self.assertEqual(set(self.cloud(h)["單號"]), {"20260115-01", "20260115-04"})
            self.assertEqual(set(h.env["load_data"]()["單號"]), {"20260115-01", "20260115-04"})
            self.assertEqual(next_request_id(frame, frame.attrs[PURGED_IDS], datetime.date(2026, 1, 15)),
                             "20260115-06")
            if h.path.name.startswith("demo_"):
                self.assertTrue(all(name.startswith("demo_") for name in h.remote))
        self.both_pages(scenario)

    def test_last_row_can_be_removed_and_empty_cloud_does_not_fallback(self):
        def scenario(h):
            h.seed = h.seed[h.seed["單號"].eq("20260115-02")]
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.publish()
            self.cleanup(h, {"20260115-02"})
            self.assertEqual(h.errors, [])
            self.assertTrue(self.cloud(h).empty)
            fresh = h.env["load_data"]()
            self.assertTrue(fresh.empty)
            day = datetime.date(2026, 1, 15)
            key = next_request_id(fresh, h.state[f"_purged_ids:{h.path}"], day)
            self.assertEqual(key, "20260115-03")
            fresh.loc[0, ["單號", "狀態"]] = [key, "已存檔未提交"]
            h.env["save_data"](fresh)
            h.remote[h.path.name] = h.seed.to_csv(index=False).encode("utf-8-sig")
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.state.clear()
            self.assertEqual(h.env["load_data"]()["單號"].tolist(), [key])
        self.both_pages(scenario)

    def test_checkbox_only_does_not_delete_and_unauthorized_users_cannot_cleanup(self):
        def scenario(h):
            before = h.remote.copy()
            self.cleanup(h, self.selected, click=False)
            self.assertEqual(h.remote, before)
            with self.assertRaises(PageStop):
                self.cleanup(h, self.selected, admin=False)
            self.assertEqual(h.remote, before)
        self.both_pages(scenario)

    def test_changed_status_aborts_entire_batch(self):
        def scenario(h):
            h.env["load_data"]()  # The selection was made on this version.
            local = h.path.read_bytes()
            h.seed.loc[h.seed["單號"].eq("20260115-02"), "狀態"] = "待簽核"
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.publish()
            h.path.write_bytes(local)
            before = h.remote.copy()
            with self.assertRaises(PageStop):
                self.cleanup(h, self.selected)
            self.assertEqual(h.remote, before)
            self.assertNotIn(f"_cleanup_notice:{h.path}", h.state)
        self.both_pages(scenario)

    def test_conflicting_branch_update_keeps_all_rows_and_reports_failure(self):
        def scenario(h):
            before = h.remote.copy()
            h.github.before_publish = lambda: setattr(h.github, "head", "concurrent-update")
            with self.assertRaises(PageStop):
                self.cleanup(h, self.selected)
            self.assertEqual(h.remote, before)
            self.assertNotIn(f"_cleanup_notice:{h.path}", h.state)
        self.both_pages(scenario)

    def test_readback_missing_purge_record_does_not_report_success(self):
        def scenario(h):
            def corrupt():
                key = h.path.name + ".manifest.json"
                manifest = json.loads(h.remote[key])
                del manifest[PURGED_IDS]
                h.remote[key] = json.dumps(manifest).encode()
            h.github.after_publish = corrupt
            with self.assertRaises(PageStop):
                self.cleanup(h, self.selected)
            self.assertNotIn(f"_cleanup_notice:{h.path}", h.state)
            self.assertTrue(any("尚未確認清理成功" in error for error in h.errors))
        self.both_pages(scenario)
