"""Rejection regressions: exercise page handlers, never the live app/database."""
import ast
import io
import tempfile
import unittest

import pandas as pd

from test_request_save_reload import PageHarness, PAGES, PageRerun, PageStop


def reject(h, mode="batch", sign_type="EXE", selected=None):
    selected = selected or ["20261103-07"]
    df = h.env["load_data"]()
    h.env.update(
        df_list=df, selected_ids=selected, curr_name="Charles", CFO_NAME="Charles",
        is_active=True, can_sign=True, sign_type=sign_type, reason="重新測試，\"核對\"\n退回原因",
        mobile_reason="重新測試，\"核對\"\n退回原因", mobile_id=selected[0],
        r=dict(df.set_index("單號").loc[selected[0]], 單號=selected[0]),
    )
    if mode == "batch":
        prefix = "st.button('確認批次駁回'"
    elif mode == "mobile":
        h.env["mobile_i"] = 0
        prefix = "st.button('確認駁回', key=f'mobile_sign_reject_"
    else:
        prefix = "st.button('確認駁回', key='btn_rej_conf'"
    handler = next(n for n in ast.walk(h.tree) if isinstance(n, ast.If)
                   and ast.unparse(n.test).startswith(prefix))
    try:
        exec(compile(ast.Module(body=[handler], type_ignores=[]), "rejection_handler", "exec"), h.env)
    except PageRerun:
        pass


class RejectionTests(unittest.TestCase):
    def each_page(self, scenario):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                scenario(PageHarness(page, folder))

    def test_local_reset_after_upload_does_not_block_rejection(self):
        def scenario(h):
            def upload_and_replace_checkout(*args):
                result = h.put(*args)
                if args[2].endswith(".manifest.json"):
                    h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
                return result
            h.env["_put_github_bytes"] = upload_and_replace_checkout
            reject(h)
            self.assertEqual(h.errors, [])
            self.assertTrue(h.messages)
            self.assertEqual(h.row()["狀態"], "已駁回")
        self.each_page(scenario)

    def test_local_reset_before_upload_cannot_change_staged_rejection(self):
        def scenario(h):
            sync = h.env["sync_to_github_core"]
            def sync_after_checkout_reset(filepath, prefer_local=False):
                h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
                return sync(filepath, prefer_local=prefer_local)
            h.env["sync_to_github_core"] = sync_after_checkout_reset
            reject(h)
            self.assertEqual(h.errors, [])
            self.assertEqual(h.row()["狀態"], "已駁回")
        self.each_page(scenario)

    def test_batch_and_single_executive_and_finance_rejection(self):
        def scenario(h):
            for mode in ("single", "batch"):
                for sign_type, prefix in (("EXE", "初審"), ("CFO", "複審")):
                    with self.subTest(mode=mode, stage=sign_type):
                        reject(h, mode=mode, sign_type=sign_type)
                        row = h.row()
                        self.assertEqual(row["狀態"], "已駁回")
                        self.assertEqual(row["駁回原因"], h.env["reason"])
                        self.assertEqual(row[prefix + "人"], "Charles")
                        self.assertTrue(row[prefix + "時間"])
            self.assertEqual(h.notifications, [])
        self.each_page(scenario)

    def test_mobile_executive_and_finance_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            h = PageHarness(PAGES[0], folder)
            for stage in ("EXE", "CFO"):
                reject(h, mode="mobile", sign_type=stage)
                self.assertEqual(h.row()["狀態"], "已駁回")
                self.assertEqual(h.row()["駁回原因"], h.env["reason"])
            self.assertEqual(h.notifications, [])

    def test_unselected_rows_are_unchanged(self):
        def scenario(h):
            before = h.env["load_data"]().set_index("單號").loc["20261103-02"].copy()
            reject(h)
            after = h.env["load_data"]().set_index("單號").loc["20261103-02"]
            pd.testing.assert_series_equal(before, after)
        self.each_page(scenario)

    def test_multiple_selected_rejections(self):
        def scenario(h):
            h.seed.loc[:, "專案負責人"] = "Charles"
            h.seed.to_csv(h.path, index=False, encoding="utf-8-sig")
            h.publish()
            ids = h.seed["單號"].tolist()
            reject(h, selected=ids)
            df = h.env["load_data"]().set_index("單號")
            self.assertTrue(df.loc[ids, "狀態"].eq("已駁回").all())
            self.assertEqual(len(df), len(h.seed))
        self.each_page(scenario)

    def test_actual_cloud_mismatch_still_blocks_success(self):
        def scenario(h):
            def corrupt_remote_status(*args):
                args = list(args)
                if ".part-" in args[2]:
                    frame = pd.read_csv(io.BytesIO(args[3]), dtype=str).fillna("")
                    frame.loc[frame["單號"].eq("20261103-07"), "狀態"] = "待簽核"
                    args[3] = frame.to_csv(index=False).encode("utf-8-sig")
                return h.put(*args)
            h.env["_put_github_bytes"] = corrupt_remote_status
            with self.assertRaises(PageStop):
                reject(h)
            self.assertEqual(h.messages, [])
            self.assertTrue(h.errors)
        self.each_page(scenario)

    def test_cloud_read_failure_is_not_success(self):
        def scenario(h):
            uploaded = False
            def put(*args):
                nonlocal uploaded
                result = h.put(*args)
                if args[2].endswith(".manifest.json"):
                    uploaded = True
                return result
            def fetch(*args):
                return (None, None, "receipt offline") if uploaded else h.fetch(*args)
            h.env.update(_put_github_bytes=put, _fetch_github_file=fetch)
            with self.assertRaises(PageStop):
                reject(h)
            self.assertEqual(h.messages, [])
            self.assertTrue(h.errors)
        self.each_page(scenario)


if __name__ == "__main__":
    unittest.main()
