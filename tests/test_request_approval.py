"""Approval transitions and notification ordering; no live transactions occur."""
import ast
import io
import tempfile
import types
import unittest

import pandas as pd

from test_request_save_reload import PageHarness, PAGES, PageRerun, PageStop


def approve(h, mode="single", stage="EXE"):
    h.env.update(
        r=dict(h.row(), 單號="20261103-07"), curr_name="Charles", CFO_NAME="Charles",
        can_sign=True, is_active=True, sign_type=stage, selected_ids=["20261103-07"],
        mobile_id="20261103-07", mobile_i=0, mobile_can_sign=True, is_btn_disabled=False,
        c_btn2=types.SimpleNamespace(button=lambda *a, **kw: True),
        batch_c1=types.SimpleNamespace(button=lambda *a, **kw: True),
    )
    prefix = {
        "single": "c_btn2.button('✅ 確認核准'",
        "batch": "batch_c1.button(f'✅ 確認核准",
        "mobile": "st.button('✅ 確認核准', key=f'mobile_sign_ok_",
    }[mode]
    handler = next(n for n in ast.walk(h.tree) if isinstance(n, ast.If)
                   and ast.unparse(n.test).startswith(prefix))
    try:
        exec(compile(ast.Module(body=[handler], type_ignores=[]), "approval_handler", "exec"), h.env)
    except PageRerun:
        pass


def cloud_row(h):
    frame, error = h.env["_read_database_chunks"](str(h.path), {}, "fixture/repo", "main")
    assert not error, error
    return frame.set_index("單號").loc["20261103-07"]


class ApprovalTests(unittest.TestCase):
    def each_page(self, scenario):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                scenario(PageHarness(page, folder))

    def test_notification_only_after_cloud_contains_second_review_state(self):
        def scenario(h):
            def notify(message):
                self.assertEqual(cloud_row(h)["狀態"], "待複審")
                self.assertEqual(h.row()["狀態"], "待複審")
                self.assertIn("待複審提醒", message)
                self.assertIn("狀態：待複審", message)
                self.assertNotIn("待簽核提醒", message)
                self.assertIn("\n", message)
                self.assertNotIn("\\n", message)
                h.notifications.append(message)
            h.env["send_line_message"] = notify
            approve(h)
            self.assertEqual(len(h.notifications), 1)
        self.each_page(scenario)

    def test_failed_save_does_not_send_approved_notification(self):
        def scenario(h):
            h.env["_put_github_bytes"] = lambda *a: (False, "simulated upload failure")
            with self.assertRaises(PageStop):
                approve(h)
            self.assertEqual(h.notifications, [])
            self.assertEqual(h.messages, [])
            self.assertEqual(cloud_row(h)["狀態"], "待簽核")
        self.each_page(scenario)

    def test_cloud_receipt_mismatch_does_not_send_approved_notification(self):
        def scenario(h):
            def corrupt_receipt(*args):
                args = list(args)
                if ".part-" in args[2]:
                    frame = pd.read_csv(io.BytesIO(args[3]), dtype=str).fillna("")
                    frame.loc[frame["單號"].eq("20261103-07"), "狀態"] = "待簽核"
                    args[3] = frame.to_csv(index=False).encode("utf-8-sig")
                return h.put(*args)
            h.env["_put_github_bytes"] = corrupt_receipt
            with self.assertRaises(PageStop):
                approve(h)
            self.assertEqual(h.notifications, [])
            self.assertEqual(h.messages, [])
            self.assertTrue(h.errors)
        self.each_page(scenario)

    def test_complete_transition_and_replay_for_every_entrypoint(self):
        for page in PAGES:
            modes = ("single", "batch", "mobile") if page == PAGES[0] else ("single", "batch")
            for mode in modes:
                with self.subTest(page=page.name, mode=mode), tempfile.TemporaryDirectory() as folder:
                    h = PageHarness(page, folder)
                    approve(h, mode=mode)
                    first = h.row().copy()
                    self.assertEqual(first["狀態"], "待複審")
                    self.assertTrue(first["初審時間"])
                    approve(h, mode=mode, stage="CFO")
                    final = h.row().copy()
                    self.assertEqual(final["狀態"], "已核准")
                    self.assertEqual(cloud_row(h)["狀態"], "已核准")
                    self.assertEqual(final["初審時間"], first["初審時間"])
                    self.assertEqual(final["複審人"], "Charles")
                    self.assertTrue(final["複審時間"])
                    approve(h, mode=mode)  # Old executive view must not downgrade a completed request.
                    approve(h, mode=mode, stage="CFO")
                    pd.testing.assert_series_equal(h.row(), final)
                    self.assertEqual(len(h.notifications), 1)

    def test_other_old_form_save_cannot_revert_approval_or_final_review(self):
        def scenario(h):
            old_form = h.env["load_data"]()
            approve(h)
            old_form.loc[old_form["單號"].eq("20261103-02"), "駁回原因"] = "另張單據的修改"
            h.env["save_data"](old_form)
            self.assertEqual(cloud_row(h)["狀態"], "待複審")
            self.assertEqual(h.row()["狀態"], "待複審")
            another_old_form = h.env["load_data"]()
            approve(h, stage="CFO")
            another_old_form.loc[another_old_form["單號"].eq("20261103-02"), "請款說明"] = "另張單據的說明"
            h.env["save_data"](another_old_form)
            self.assertEqual(cloud_row(h)["狀態"], "已核准")
            self.assertEqual(h.row()["狀態"], "已核准")
        self.each_page(scenario)

    def test_same_field_conflict_is_not_silently_overwritten(self):
        def scenario(h):
            old_form = h.env["load_data"]()
            approve(h)
            old_form.loc[old_form["單號"].eq("20261103-07"), "狀態"] = "已駁回"
            with self.assertRaises(PageStop):
                h.env["save_data"](old_form)
            self.assertEqual(cloud_row(h)["狀態"], "待複審")
            self.assertIn("其他操作更新", h.errors[-1])
        self.each_page(scenario)

    def test_latest_cloud_state_checked_even_when_local_file_is_unchanged(self):
        def scenario(h):
            h.row()
            for name, content in list(h.remote.items()):
                if ".part-" not in name:
                    continue
                frame = pd.read_csv(io.BytesIO(content), dtype=str).fillna("")
                frame.loc[frame["單號"].eq("20261103-07"), "狀態"] = "已核准"
                h.remote[name] = frame.to_csv(index=False).encode("utf-8-sig")
            approve(h)
            self.assertEqual(cloud_row(h)["狀態"], "已核准")
            self.assertEqual(h.row()["狀態"], "已核准")
            self.assertEqual(h.notifications, [])
        self.each_page(scenario)

    def test_wrong_approver_inactive_user_and_out_of_order_cfo_cannot_approve(self):
        def scenario(h):
            h.env.update(curr_name="Charles", CFO_NAME="Charles", is_active=True)
            self.assertEqual(h.env["approve_requests"](["20261103-07"], "CFO"), 0)
            h.env["curr_name"] = "Andy"
            self.assertEqual(h.env["approve_requests"](["20261103-07"], "EXE"), 0)
            h.env.update(curr_name="Charles", is_active=False)
            self.assertEqual(h.env["approve_requests"](["20261103-07"], "EXE"), 0)
            self.assertEqual(cloud_row(h)["狀態"], "待簽核")
            self.assertEqual(h.notifications, [])
        self.each_page(scenario)

    def test_new_record_does_not_republish_other_old_statuses(self):
        def scenario(h):
            old_form = h.env["load_data"]()
            approve(h)
            baseline = old_form.attrs.copy()
            new_row = old_form.iloc[0].copy()
            new_row["單號"], new_row["狀態"] = "NEW-REQUEST", "已存檔未提交"
            with_new = pd.concat([old_form, pd.DataFrame([new_row])], ignore_index=True)
            with_new.attrs = baseline
            h.env["save_data"](with_new)
            self.assertEqual(cloud_row(h)["狀態"], "待複審")
            frame = h.env["load_data"]().set_index("單號")
            self.assertEqual(frame.at["NEW-REQUEST", "狀態"], "已存檔未提交")
        self.each_page(scenario)


if __name__ == "__main__":
    unittest.main()
