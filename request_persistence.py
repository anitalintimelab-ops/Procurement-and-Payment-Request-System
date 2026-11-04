"""Process-wide request I/O coordination, retained across Streamlit reruns."""
import hashlib
import os
import tempfile
import threading


# A lock created in a page script is recreated on every rerun/session. Keep one
# shared, reentrant lock here because saves call the synchronizer under the lock.
DATABASE_IO_LOCK = threading.RLock()


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
