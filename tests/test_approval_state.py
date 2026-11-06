import tempfile
import unittest
from pathlib import Path

import pandas as pd

from approval_state import (
    merge_database_snapshots,
    normalize_approval_statuses,
    repair_approval_statuses_in_file,
)


def row(request_id, status, first_reviewer="", first_time="", submitted="2026-11-06 10:00"):
    return {
        "單號": request_id,
        "狀態": status,
        "初審人": first_reviewer,
        "初審時間": first_time,
        "複審人": "",
        "複審時間": "",
        "提交時間": submitted,
    }


class ApprovalStateTests(unittest.TestCase):
    def test_first_approval_is_normalized_to_second_review(self):
        frame = pd.DataFrame([row("A", "待簽核", "Andy", "2026-11-06 11:00")])
        self.assertEqual(normalize_approval_statuses(frame).loc[0, "狀態"], "待複審")

    def test_terminal_states_are_not_rewritten(self):
        frame = pd.DataFrame([
            row("A", "已核准", "Andy", "2026-11-06 11:00"),
            row("B", "已駁回", "Andy", "2026-11-06 11:00"),
        ])
        self.assertEqual(normalize_approval_statuses(frame).loc[0, "狀態"], "已核准")
        self.assertEqual(normalize_approval_statuses(frame).loc[1, "狀態"], "已駁回")
        legacy = pd.DataFrame([row("C", "已完成", "Andy", "2026-11-06 11:00")])
        self.assertEqual(normalize_approval_statuses(legacy).loc[0, "狀態"], "已完成")

    def test_merge_keeps_more_advanced_remote_or_local_stage(self):
        remote = pd.DataFrame([row("A", "待複審", "Andy", "2026-11-06 11:00")])
        stale_local = pd.DataFrame([row("A", "待簽核")])
        merged = merge_database_snapshots(remote, stale_local)
        self.assertEqual(merged.loc[0, "狀態"], "待複審")

        remote_stale = pd.DataFrame([row("B", "待簽核")])
        local_signed = pd.DataFrame([row("B", "待簽核", "Andy", "2026-11-06 12:00")])
        merged = merge_database_snapshots(remote_stale, local_signed)
        self.assertEqual(merged.loc[0, "狀態"], "待複審")

    def test_requested_ids_are_repaired(self):
        frame = pd.DataFrame([
            row("20261103-01", "待簽核"),
            row("20261106-01", "待複審"),
        ])
        repaired = normalize_approval_statuses(frame)
        self.assertEqual(repaired.loc[0, "狀態"], "待複審")
        self.assertEqual(repaired.loc[1, "狀態"], "待簽核")

    def test_repair_persists_status_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "database.csv"
            pd.DataFrame([row("A", "待簽核", "Andy", "2026-11-06 11:00")]).to_csv(
                path, index=False, encoding="utf-8-sig"
            )
            self.assertEqual(repair_approval_statuses_in_file(str(path)), 1)
            self.assertEqual(repair_approval_statuses_in_file(str(path)), 0)
            saved = pd.read_csv(path, dtype=str).fillna("")
            self.assertEqual(saved.loc[0, "狀態"], "待複審")


if __name__ == "__main__":
    unittest.main()
