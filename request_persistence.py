"""Process-wide request I/O coordination, retained across Streamlit reruns."""
import hashlib
import os
import tempfile
import threading


# A lock created in a page script is recreated on every rerun/session. Keep one
# shared, reentrant lock here because saves call the synchronizer under the lock.
DATABASE_IO_LOCK = threading.RLock()
BASELINE_ATTR = "_request_database_baseline"


def _field_digest(column, value):
    text = str(value)
    # These three columns are converted to integer zero by the page loader.
    if column in {"總金額", "已請款金額", "尚未請款金額"} and text in {"", "0.0"}:
        text = "0"
    if column == "狀態":
        if "需要財務長" in text:
            text = "待複審"
        elif "需要執行長" in text:
            text = "待簽核"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def capture_database_baseline(frame):
    """Keep small cell hashes so an old form cannot resave unrelated old states."""
    rows = {}
    for row in frame.fillna("").astype(str).to_dict("records"):
        rows[row["單號"]] = {col: _field_digest(col, value) for col, value in row.items()}
    frame.attrs[BASELINE_ATTR] = rows
    return frame


def database_changes(frame):
    baseline = frame.attrs.get(BASELINE_ATTR)
    if baseline is None:
        return None  # Compatibility for explicit imports/newly assembled snapshots.
    changes = {}
    for row in frame.fillna("").astype(str).to_dict("records"):
        key = row["單號"]
        before = baseline.get(key)
        fields = {
            col: {"before": before.get(col) if before else None, "value": value}
            for col, value in row.items() if col != "單號"
            and (before is None or before.get(col) != _field_digest(col, value))
        }
        if fields:
            changes[key] = {"new": before is None, "fields": fields}
    return changes


def apply_database_changes(remote, changes):
    """Patch only edited cells; refuse a conflicting edit instead of overwriting it."""
    merged = remote.fillna("").astype(str).set_index("單號")
    if not merged.index.is_unique:
        raise ValueError("雲端資料含重複單號，已停止覆蓋")
    for change in changes.values():
        for column in change["fields"]:
            if column not in merged.columns:
                merged[column] = ""
    for key, change in changes.items():
        if change["new"] and key in merged.index:
            raise ValueError(f"單號 {key} 已存在，請重新整理後重試")
        if not change["new"] and key not in merged.index:
            raise ValueError(f"單號 {key} 已不存在，請重新整理後重試")
        if key not in merged.index:
            # Reindex also works for a header-only CSV after clearing the last row.
            merged = merged.reindex([*merged.index, key], fill_value="")
        for column, field in change["fields"].items():
            current = merged.at[key, column] if column in merged.columns else ""
            if not change["new"] and _field_digest(column, current) not in {
                field["before"], _field_digest(column, field["value"]),
            }:
                raise ValueError(f"單號 {key} 的 {column} 已被其他操作更新，請重新整理後重試")
            merged.loc[key, column] = field["value"]
    return merged.reset_index().fillna("")


def verify_database_changes(received, changes):
    if received is None or "單號" not in received.columns:
        raise ValueError("雲端回讀缺少單號，尚未確認存檔成功")
    indexed = received.fillna("").astype(str).set_index("單號")
    if not indexed.index.is_unique:
        raise ValueError("雲端回讀含重複單號，尚未確認存檔成功")
    for key, change in changes.items():
        if key not in indexed.index:
            raise ValueError(f"雲端回讀缺少單號 {key}，尚未確認存檔成功")
        for column, field in change["fields"].items():
            if column not in indexed.columns or _field_digest(column, indexed.at[key, column]) != _field_digest(column, field["value"]):
                raise ValueError(f"雲端回讀不一致：單號 {key}、欄位 {column}，尚未確認存檔成功")


def database_fingerprint(filepath):
    """Identify the actual local snapshot, not just whether this user logged in."""
    digest = hashlib.sha256()
    try:
        with open(filepath, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return None
    return digest.hexdigest()


def verify_database_snapshot(expected, received):
    """Check cloud CSV values, not pandas dtype metadata or a mutable checkout."""
    key = "單號"
    if received is None or key not in received.columns or key not in expected.columns:
        raise ValueError("雲端回讀缺少單號欄位，尚未確認存檔成功")
    expected = expected.fillna("").astype(str).set_index(key)
    received = received.fillna("").astype(str).set_index(key)
    if not expected.index.is_unique or not received.index.is_unique:
        raise ValueError("雲端回讀含重複單號，尚未確認存檔成功")
    if not expected.index.isin(received.index).all():
        raise ValueError("雲端回讀缺少本次存檔的單號，尚未確認存檔成功")
    if not expected.columns.isin(received.columns).all():
        raise ValueError("雲端回讀缺少本次存檔的欄位，尚未確認存檔成功")
    received = received.reindex(index=expected.index, columns=expected.columns)
    # CSV has no dtype metadata. Exact cell values still must match, including
    # amount, status, rejection reason, reviewer and time; never ignore a change.
    same = expected.to_numpy(dtype=object) == received.to_numpy(dtype=object)
    if not same.all():
        row, column = next(zip(*((~same).nonzero())))
        raise ValueError(
            f"雲端回讀不一致：單號 {expected.index[row]}、欄位 {expected.columns[column]}，"
            "尚未確認存檔成功，請重新整理確認後重試"
        )


def write_database_snapshot(frame, filepath):
    """Replace the local cache atomically and return the verified bytes' hash.

    Hash the staging file, not the destination: a deployment can replace the
    destination even while Python holds a lock. Its old bytes must not become
    the new session's accepted fingerprint.
    """
    staged = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", delete=False,
            dir=os.path.dirname(os.path.abspath(filepath)), prefix=".request-", suffix=".tmp",
        ) as stream:
            staged = stream.name
            frame.to_csv(stream, index=False)
            stream.flush()
            os.fsync(stream.fileno())
        signature = database_fingerprint(staged)
        os.replace(staged, filepath)
        return signature
    finally:
        if staged and os.path.exists(staged):
            os.unlink(staged)
