"""Run real page handlers with isolated files and an in-memory GitHub transport.

No Streamlit login, real database writes, GitHub writes or LINE messages occur.
Run: python -m unittest discover -s tests -p test_request_save_reload.py -v
"""
import ast
import base64
import datetime
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest

import pandas as pd
from approval_state import (
    normalize_approval_statuses, repair_approval_statuses_in_file, validate_approval_batch,
)
from request_database_sync import (
    CLEANUP_STATES, PURGED_IDS, next_request_id, read_database_chunks, request_ids,
    snapshot_head, sync_database, verify_purge,
)
from request_performance import github_blob_digest


ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "pages/2_請款單系統.py", ROOT / "pages/99_測試區-請款單系統.py"]


class PageStop(BaseException):
    pass


class PageRerun(BaseException):
    pass


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FakeGitHub:
    """A new branch version only becomes visible after a fast-forward update."""
    def __init__(self, files):
        self.files = files
        self.head = "base"
        self.blobs = {}
        self.pending = {}
        self.before_publish = lambda: None
        self.after_publish = lambda: None
        self.published = 0

    @staticmethod
    def response(status, **payload):
        return types.SimpleNamespace(status_code=status, json=lambda: payload)

    def get(self, url, **kwargs):
        assert "/commits/" in url, url
        return self.response(200, sha=self.head, commit={"tree": {"sha": self.head + "-tree"}})

    def post(self, url, *, json, **kwargs):
        if url.endswith("/blobs"):
            data = base64.b64decode(json["content"])
            sha = github_blob_digest(data)
            self.blobs[sha] = data
            return self.response(201, sha=sha)
        if url.endswith("/trees"):
            assert json["base_tree"] == self.head + "-tree"
            self.pending = self.files.copy()
            for item in json["tree"]:
                if item["sha"] is None:
                    del self.pending[item["path"]]
                else:
                    self.pending[item["path"]] = self.blobs[item["sha"]]
            return self.response(201, sha="pending-tree")
        assert url.endswith("/commits")
        self.parent, = json["parents"]
        return self.response(201, sha=f"snapshot-{self.published + 1}")

    def patch(self, url, *, json, **kwargs):
        assert "/refs/heads/" in url and json["force"] is False
        self.before_publish()
        if self.parent != self.head:
            return self.response(422)
        self.files.clear()
        self.files.update(self.pending)
        self.head = json["sha"]
        self.published += 1
        self.after_publish()
        return self.response(200)


class PageHarness:
    def __init__(self, page, folder):
        self.tree = ast.parse(page.read_text(encoding="utf-8-sig"))
        self.messages, self.errors, self.notifications = [], [], []
        self.state = State(req_edit_id="20260115-07", req_uploader_key=0)
        st = types.SimpleNamespace(
            session_state=self.state, error=self.errors.append,
            stop=lambda: self._raise(PageStop), rerun=lambda: self._raise(PageRerun),
            toast=lambda text, **kw: self.messages.append(text),
            success=self.messages.append, info=self.messages.append, button=lambda *a, **kw: True,
        )
        demo = page.name.startswith("99_")
        prefix = "demo_" if demo else ""
        self.path = Path(folder) / (prefix + "database.csv")
        self.remote = {}
        self.github = FakeGitHub(self.remote)
        self.env = {
            "st": st, "pd": pd, "os": os, "io": io, "json": json,
            "base64": base64, "datetime": datetime, "tempfile": tempfile,
            "time": types.SimpleNamespace(sleep=lambda seconds: None),
            "D_FILE": str(self.path), "G_FILE": str(Path(folder) / (prefix + "github_credentials.txt")),
            "L_FILE": str(Path(folder) / (prefix + "line_credentials.txt")),
            "S_FILE": str(Path(folder) / (prefix + "staff.csv")),
            "P_FILE": str(Path(folder) / (prefix + "projects.csv")),
            "V_FILE": str(Path(folder) / (prefix + "vendors.csv")),
            "GITHUB_SYNC_LOCK": threading.RLock(),
            "CSV_SYNC_KEYS": {self.path.name: "單號"}, "DATABASE_CHUNK_BYTES": 1500,
            "get_github_config": lambda: ("fake-token", "test/repo", "main", "fixture"),
            "get_test_github_config": lambda: ("fake-token", "test/demo", "main", "fixture"),
            "send_line_message": self.notifications.append,
            "is_active": True,
            "requests": self.github,
            "normalize_approval_statuses": normalize_approval_statuses,
            "validate_approval_batch": validate_approval_batch,
            "repair_approval_statuses_in_file": repair_approval_statuses_in_file,
            "CLEANUP_STATES": CLEANUP_STATES, "PURGED_IDS": PURGED_IDS,
            "next_request_id": next_request_id, "request_ids": request_ids,
            "snapshot_head": snapshot_head, "sync_database": sync_database,
            "read_database_chunks": read_database_chunks, "verify_purge": verify_purge,
        }
        wanted = {
            "_read_database_chunks", "_restore_database_chunks", "_merge_remote_csv",
            "_sync_database_to_github", "_split_database_csv", "sync_to_github_core",
            "sync_all_data_to_github",
            "restore_data_from_github_once", "_save_local_and_cloud", "read_csv_robust",
            "load_data", "_load_data_uncached", "save_data", "clean_amount", "safe_str", "get_taiwan_time", "approve_requests",
        }
        nodes = [n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(page), "exec"), self.env)
        try:
            from request_persistence import (
                database_fingerprint, verify_database_snapshot, write_database_snapshot,
                capture_database_baseline, database_changes, apply_database_changes, verify_database_changes,
            )
            self.env.update(
                database_fingerprint=database_fingerprint,
                verify_database_snapshot=verify_database_snapshot,
                write_database_snapshot=write_database_snapshot,
                capture_database_baseline=capture_database_baseline,
                database_changes=database_changes, apply_database_changes=apply_database_changes,
                verify_database_changes=verify_database_changes,
            )
        except ImportError:
            pass
        from request_performance import (
            github_blob_digest, cached_github_blob, remember_github_blob,
            cached_database_frame, LocalSnapshotChanged,
        )
        self.env.update(
            github_blob_digest=github_blob_digest, cached_github_blob=cached_github_blob,
            remember_github_blob=remember_github_blob, cached_database_frame=cached_database_frame,
            LocalSnapshotChanged=LocalSnapshotChanged,
        )
        self.env["_fetch_github_file"] = self.fetch
        self.seed = pd.DataFrame([
            {"單號": "20260115-07", "類型": "請款單", "專案名稱": "測試專案", "專案負責人": "Charles",
             "申請人": "Charles", "總金額": "341460", "狀態": "待簽核", "提交時間": "2026-11-03 11:02"},
            {"單號": "20260115-02", "類型": "請款單", "總金額": "599970", "狀態": "待複審"},
        ]).fillna("")
        self.seed.to_csv(self.path, index=False, encoding="utf-8-sig")
        self.publish()

    @staticmethod
    def _raise(exc):
        raise exc()

    def fetch(self, url, headers, branch):
        name = url.split("/contents/")[-1]
        data = self.remote.get(name, b"")
        return data, github_blob_digest(data) if data else None, ""

    def publish(self):
        parts, manifest, error = self.env["_split_database_csv"](str(self.path))
        assert not error, error
        self.remote.update({name: content for name, content, _ in parts})
        self.remote[self.path.name + ".manifest.json"] = json.dumps(manifest).encode()

    def row(self):
        df = self.env["load_data"]()
        return df.set_index("單號").loc["20260115-07"]

    def save_amount(self, gross=170730, deduct_fee=False):
        self.state.req_edit_id = "20260115-07"
        self.row()  # Initialize the real loader, as the UI does before rendering.
        self.env.update(
            btn_save=True, btn_preview=False, btn_print=False, btn_submit=False,
            pay="匯款(扣30手續費)" if deduct_fee else "匯款(不扣30手續費)",
            net_amt=gross - 8130, tax_amt=8130, pn="測試專案", pi="TEST-001", exe="Charles",
            app_val="Charles", curr_name="Charles", curr="TWD", vdr="測試廠商", acc="", inv_no="",
            desc="僅改金額", f_acc=None, f_ims=[], del_acc=False, del_ims=[], existing_ims=[],
            dv={"ab64": "", "acc_name": "", "ims_names": []},
        )
        handler = next(n for n in ast.walk(self.tree) if isinstance(n, ast.If)
                       and isinstance(n.test, ast.BoolOp)
                       and ast.unparse(n.test).startswith("btn_save or"))
        try:
            exec(compile(ast.Module(body=[handler], type_ignores=[]), "save_handler", "exec"), self.env)
        except PageRerun:
            pass

    def submit(self):
        self.env.update(b1=types.SimpleNamespace(button=lambda *a, **kw: True), i=0,
                        can_edit=True, r=self.row())
        self.env["r"] = dict(self.env["r"], 單號="20260115-07")
        handler = next(n for n in ast.walk(self.tree) if isinstance(n, ast.If)
                       and ast.unparse(n.test).startswith("b1.button('提交'"))
        try:
            exec(compile(ast.Module(body=[handler], type_ignores=[]), "submit_handler", "exec"), self.env)
        except PageRerun:
            pass

    def review(self, approve):
        self.env.update(
            r=dict(self.row(), 單號="20260115-07"), curr_name="Charles", CFO_NAME="Charles",
            c_btn2=types.SimpleNamespace(button=lambda *a, **kw: True), can_sign=True,
            sign_type="EXE", reason="測試退回",
        )
        prefix = "c_btn2.button('✅ 確認核准'" if approve else "st.button('確認駁回', key='btn_rej_conf'"
        handler = next(n for n in ast.walk(self.tree) if isinstance(n, ast.If)
                       and ast.unparse(n.test).startswith(prefix))
        try:
            exec(compile(ast.Module(body=[handler], type_ignores=[]), "review_handler", "exec"), self.env)
        except PageRerun:
            pass


class SaveReloadTests(unittest.TestCase):
    def both_pages(self, scenario):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                scenario(PageHarness(page, folder))

    def test_save_only_changes_amount_and_stays_draft(self):
        def scenario(h):
            h.save_amount()
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
            self.assertEqual(h.notifications, [])
            self.assertEqual(h.errors, [])
        self.both_pages(scenario)

    def test_deployment_reset_in_same_session_restores_latest_draft(self):
        def scenario(h):
            h.save_amount()
            # Git checkout/deployment restores the old tracked database.csv.
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
        self.both_pages(scenario)

    def test_explicit_submit_is_required(self):
        def scenario(h):
            h.save_amount()
            self.assertEqual(h.notifications, [])
            h.submit()
            self.assertEqual(h.row()["狀態"], "待簽核")
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(len(h.notifications), 1)
        self.both_pages(scenario)

    def test_fee_calculation_unchanged(self):
        def scenario(h):
            h.save_amount(deduct_fee=True)
            self.assertEqual(h.row()["總金額"], 170700)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
        self.both_pages(scenario)

    def test_new_login_restores_latest_cloud_amount_and_state(self):
        def scenario(h):
            h.save_amount()
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.state.clear()
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
        self.both_pages(scenario)

    def test_failed_restore_blocks_stale_display_and_retries(self):
        def scenario(h):
            h.save_amount()
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.env["_fetch_github_file"] = lambda *a: (None, None, "offline test")
            with self.assertRaises(PageStop):
                h.row()
            self.assertEqual(len(h.errors), 1)
            h.env["_fetch_github_file"] = h.fetch
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
        self.both_pages(scenario)

    def test_failed_upload_never_shows_save_success(self):
        def scenario(h):
            h.github.post = lambda *a, **kw: h.github.response(403)
            with self.assertRaises(PageStop):
                h.save_amount()
            self.assertEqual(h.messages, [])
            self.assertEqual(h.notifications, [])
            self.assertEqual(len(h.errors), 1)
        self.both_pages(scenario)

    def test_local_reset_after_upload_restores_verified_cloud_receipt(self):
        def scenario(h):
            h.github.after_publish = lambda: h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.save_amount()
            self.assertEqual(h.errors, [])
            self.assertEqual(h.row()["總金額"], 170730)
            self.assertEqual(h.row()["狀態"], "已存檔未提交")
            self.assertEqual(h.notifications, [])
        self.both_pages(scenario)

    def test_other_rows_and_old_review_details_are_preserved(self):
        def scenario(h):
            old = h.env["load_data"]().set_index("單號").loc["20260115-02"].copy()
            old_submission = h.row()["提交時間"]
            h.save_amount()
            current = h.env["load_data"]().set_index("單號").loc["20260115-02"]
            pd.testing.assert_series_equal(old, current)
            self.assertEqual(h.row()["提交時間"], old_submission)
        self.both_pages(scenario)

    def test_approval_and_rejection_survive_deployment_reset(self):
        def scenario(h):
            h.review(approve=False)
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            self.assertEqual(h.row()["狀態"], "已駁回")
            self.assertEqual(h.row()["駁回原因"], "測試退回")
            h.submit()  # A rejected request must be explicitly resubmitted first.
            h.review(approve=True)
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            self.assertEqual(h.row()["狀態"], "待複審")
            self.assertEqual(h.row()["初審人"], "Charles")
        self.both_pages(scenario)

    def test_environment_markers_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            prod, demo = [PageHarness(page, folder) for page in PAGES]
            demo.state = prod.state
            demo.env["st"].session_state = demo.state
            prod.save_amount()
            demo.save_amount(gross=200000)
            self.assertEqual(prod.row()["總金額"], 170730)
            self.assertEqual(demo.row()["總金額"], 200000)
            self.assertEqual(prod.row()["狀態"], "已存檔未提交")
            self.assertTrue(all(name.startswith("demo_") for name in demo.remote))


if __name__ == "__main__":
    unittest.main()
