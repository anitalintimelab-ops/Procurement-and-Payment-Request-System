"""Shared approval-state rules for production and test request systems.

Approval state is monotonic: a completed first approval must never be downgraded
to the initial approval queue during a GitHub reconciliation.
"""
import os
import pandas as pd

APPROVAL_STATUS_RANK = {
    "": 0,
    "待初審": 1,
    "待簽核": 1,
    "待複審": 2,
    "已核准": 3,
    "已完成": 3,
    "已駁回": 3,
}

# One-time repair requested for the currently affected production/test requests.
# Terminal decisions remain protected below and will not be overwritten.
REQUEST_STATUS_REPAIRS = {
    **{f"20261103-{i:02d}": "待複審" for i in range(1, 8)},
    "20261106-01": "待複審",
}

def _text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()

def _workflow_status(row):
    request_id = _text(row.get("單號", ""))
    status = _text(row.get("狀態", ""))
    # Final decisions are terminal and must never be rewritten.
    if status in {"已核准", "已完成", "已駁回"}:
        return "已核准" if status in {"已核准", "已完成"} else status
    if request_id in REQUEST_STATUS_REPAIRS:
        return REQUEST_STATUS_REPAIRS[request_id]
    # Explicit first-review evidence is stronger than a stale status label.
    if _text(row.get("初審人")) or _text(row.get("初審時間")):
        return "待複審"
    if "需要財務長" in status:
        return "待複審"
    if "需要執行長" in status:
        return "待簽核"
    return status

def normalize_approval_statuses(df):
    """Normalize legacy labels without allowing a completed stage to regress."""
    if df is None or df.empty or "狀態" not in df.columns:
        return df
    result = df.copy()
    result["狀態"] = result.apply(_workflow_status, axis=1)
    return result

def validate_approval_states(df):
    """Return invariant violations after normalization; used as a sync guard."""
    errors = []
    if df is None or df.empty:
        return errors
    for _, row in df.iterrows():
        request_id = _text(row.get("單號", ""))
        status = _text(row.get("狀態", ""))
        has_first_review = bool(_text(row.get("初審人")) or _text(row.get("初審時間")))
        has_final_review = bool(_text(row.get("複審人")) or _text(row.get("複審時間")))
        if has_final_review and status not in {"已核准", "已駁回"}:
            errors.append(f"{request_id}: final review evidence with status {status}")
        if status == "待複審" and has_final_review:
            errors.append(f"{request_id}:待複審 cannot have final review evidence")
        if status == "待複審" and not has_first_review and request_id not in REQUEST_STATUS_REPAIRS:
            errors.append(f"{request_id}:待複審缺少初審證據")
    return errors

def _activity_timestamp(frame):
    columns = [c for c in ["提交時間", "初審時間", "複審時間", "刪除時間"] if c in frame.columns]
    if not columns:
        return pd.Series(pd.NaT, index=frame.index)
    parsed = [pd.to_datetime(frame[c], errors="coerce") for c in columns]
    return pd.concat(parsed, axis=1).max(axis=1)

def merge_database_snapshots(remote_df, local_df, key="單號"):
    """Merge snapshots while preserving the furthest approval stage per request."""
    if remote_df is None or remote_df.empty:
        result = normalize_approval_statuses(local_df)
        errors = validate_approval_states(result)
        if errors:
            raise ValueError("簽核狀態一致性檢查失敗：" + "; ".join(errors[:5]))
        return result
    if local_df is None or local_df.empty:
        result = normalize_approval_statuses(remote_df)
        errors = validate_approval_states(result)
        if errors:
            raise ValueError("簽核狀態一致性檢查失敗：" + "; ".join(errors[:5]))
        return result
    if key not in remote_df.columns or key not in local_df.columns:
        raise ValueError(f"資料庫缺少合併欄位 {key}")
    remote = normalize_approval_statuses(remote_df).copy()
    local = normalize_approval_statuses(local_df).copy()
    merged = pd.concat([
        remote.assign(_sync_source=0),
        local.assign(_sync_source=1),
    ], ignore_index=True, sort=False).fillna("")
    merged[key] = merged[key].astype(str).str.strip()
    merged = merged[merged[key] != ""]
    merged["_workflow_rank"] = merged["狀態"].map(APPROVAL_STATUS_RANK).fillna(0)
    merged["_activity_timestamp"] = _activity_timestamp(merged)
    # Highest stage wins. Same-stage ties use the newest activity, then local
    # data, so a full sync cannot roll a signed request backwards.
    merged = merged.sort_values(
        [key, "_workflow_rank", "_activity_timestamp", "_sync_source"],
        kind="stable",
        na_position="first",
    )
    merged = merged.drop_duplicates(subset=[key], keep="last")
    result = merged.drop(columns=["_sync_source", "_workflow_rank", "_activity_timestamp"])
    errors = validate_approval_states(result)
    if errors:
        raise ValueError("簽核狀態一致性檢查失敗：" + "; ".join(errors[:5]))
    return result

def repair_approval_statuses_in_file(filepath):
    """Persist the one-time repair when the admin presses full sync."""
    if not os.path.exists(filepath):
        return 0
    frame = None
    for encoding in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            frame = pd.read_csv(filepath, encoding=encoding, dtype=str).fillna("")
            break
        except Exception:
            continue
    if frame is None or frame.empty or "狀態" not in frame.columns:
        return 0
    before = frame["狀態"].astype(str).tolist()
    repaired = normalize_approval_statuses(frame)
    changed = int(sum(a != b for a, b in zip(before, repaired["狀態"].astype(str).tolist())))
    errors = validate_approval_states(repaired)
    if errors:
        raise ValueError("簽核狀態自我檢查失敗：" + "; ".join(errors[:5]))
    if changed:
        repaired.to_csv(filepath, index=False, encoding="utf-8-sig")
    return changed
