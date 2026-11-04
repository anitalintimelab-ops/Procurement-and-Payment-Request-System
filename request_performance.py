"""Bounded, content-addressed caches; never cache authorization or mutable views."""
from collections import OrderedDict
from copy import deepcopy
import hashlib
import os
import threading

from request_persistence import database_fingerprint


class _BoundedCache:
    def __init__(self, max_bytes, max_entries):
        self.max_bytes, self.max_entries = max_bytes, max_entries
        self.entries, self.size = OrderedDict(), 0
        self.lock = threading.RLock()

    def get(self, key):
        with self.lock:
            if key not in self.entries:
                return None
            entry = self.entries.pop(key)
            self.entries[key] = entry
            return entry[0]

    def put(self, key, value, size):
        if size > self.max_bytes:
            return
        with self.lock:
            if key in self.entries:
                self.size -= self.entries.pop(key)[1]
            self.entries[key] = (value, size)
            self.size += size
            while self.size > self.max_bytes or len(self.entries) > self.max_entries:
                _, (_, removed_size) = self.entries.popitem(last=False)
                self.size -= removed_size

    def clear(self):
        with self.lock:
            self.entries.clear()
            self.size = 0


_BLOBS = _BoundedCache(32 * 1024 * 1024, 16)
_FRAMES = _BoundedCache(32 * 1024 * 1024, 4)


def github_blob_digest(content):
    digest = hashlib.sha1()  # Git object identity, not an authentication hash.
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


def _blob_key(url, headers, sha):
    authorization = str(headers.get("Authorization", headers.get("authorization", "")))
    return url, hashlib.sha256(authorization.encode()).hexdigest(), sha


def cached_github_blob(url, headers, sha):
    # The caller MUST obtain this SHA with a fresh authorized metadata GET first.
    return _BLOBS.get(_blob_key(url, headers, sha))


def remember_github_blob(url, headers, sha, content):
    content = bytes(content)
    _BLOBS.put(_blob_key(url, headers, sha), content, len(content))


class LocalSnapshotChanged(Exception):
    pass


def cached_database_frame(filepath, expected_fingerprint, loader):
    """Use actual file SHA-256, not a TTL/stat guess; return independent edits."""
    actual = database_fingerprint(filepath)
    if actual != expected_fingerprint:
        raise LocalSnapshotChanged()
    if actual is None:
        return loader()
    # A code deployment can change normalization without changing CSV bytes.
    key = os.path.abspath(filepath), actual, getattr(loader, "__code__", None)
    frame = _FRAMES.get(key)
    if frame is None:
        frame = loader()
        if database_fingerprint(filepath) != actual:
            raise LocalSnapshotChanged()
        if frame is None or frame.empty:
            return frame
        _FRAMES.put(key, frame, int(frame.memory_usage(index=True, deep=True).sum()))
    result = frame.copy(deep=True)
    result.attrs = deepcopy(frame.attrs)
    return result


def clear_performance_caches():
    """Tests/diagnostics only; no stored credentials or transactions are affected."""
    _BLOBS.clear()
    _FRAMES.clear()
