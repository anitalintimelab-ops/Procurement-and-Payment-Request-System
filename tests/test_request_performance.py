"""Performance optimizations may not weaken content checks or edit isolation."""
import ast
import os
from pathlib import Path
import tempfile
import types
import unittest

import pandas as pd

from request_performance import (
    _BoundedCache, github_blob_digest, cached_github_blob, remember_github_blob,
    cached_database_frame, LocalSnapshotChanged, clear_performance_caches,
)
from request_persistence import database_fingerprint
from test_request_save_reload import PageHarness, PAGES


class Reply:
    def __init__(self, status=200, payload=None, content=b""):
        self.status_code, self.payload, self.content = status, payload, content
        self.text = "fake response"

    def json(self):
        return self.payload


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        clear_performance_caches()

    def http_functions(self, page, http):
        tree = ast.parse(page.read_text(encoding="utf-8-sig"))
        names = {"_fetch_github_file", "_put_github_bytes", "_github_file_sha"}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        import base64
        env = dict(
            requests=http, base64=base64, time=types.SimpleNamespace(sleep=lambda *a: None),
            github_blob_digest=github_blob_digest, cached_github_blob=cached_github_blob,
            remember_github_blob=remember_github_blob,
        )
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(page), "exec"), env)
        return env

    def test_repeated_load_parses_once_but_returns_independent_edits(self):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                h = PageHarness(page, folder)
                original = h.env["_load_data_uncached"]
                count = 0
                def loader():
                    nonlocal count
                    count += 1
                    return original()
                h.env["_load_data_uncached"] = loader
                first = h.env["load_data"]()
                first.loc[:, "狀態"] = "do not cache this edit"
                first.attrs["_request_database_baseline"].clear()
                for _ in range(4):
                    other = h.env["load_data"]()
                    self.assertNotIn("do not cache this edit", other["狀態"].tolist())
                    self.assertTrue(other.attrs["_request_database_baseline"])
                self.assertEqual(count, 1)

    def test_same_size_and_timestamp_still_use_full_content_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.csv"
            path.write_text("id,value\n1,old\n", encoding="utf-8")
            before = path.stat()
            count = 0
            def loader():
                nonlocal count
                count += 1
                return pd.read_csv(path, dtype=str)
            first = cached_database_frame(path, database_fingerprint(path), loader)
            path.write_text("id,value\n1,new\n", encoding="utf-8")
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            second = cached_database_frame(path, database_fingerprint(path), loader)
            self.assertEqual(first.at[0, "value"], "old")
            self.assertEqual(second.at[0, "value"], "new")
            self.assertEqual(count, 2)

    def test_changed_file_between_verification_and_parsing_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.csv"
            path.write_text("id,value\n1,old\n", encoding="utf-8")
            expected = database_fingerprint(path)
            def loader():
                path.write_text("id,value\n1,new\n", encoding="utf-8")
                return pd.read_csv(path, dtype=str)
            with self.assertRaises(LocalSnapshotChanged):
                cached_database_frame(path, expected, loader)

    def test_normalizer_code_changes_invalidate_prepared_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.csv"
            path.write_text("id,value\n1,same\n", encoding="utf-8")
            fingerprint = database_fingerprint(path)
            first = cached_database_frame(path, fingerprint, lambda: pd.DataFrame({"schema": ["old"]}))
            second = cached_database_frame(path, fingerprint, lambda: pd.DataFrame({"schema": ["new"]}))
            self.assertEqual(first.at[0, "schema"], "old")
            self.assertEqual(second.at[0, "schema"], "new")

    def test_local_cache_is_separate_for_production_and_demo_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            prod, demo = [Path(folder) / name for name in ("database.csv", "demo_database.csv")]
            for path in (prod, demo):
                path.write_text("id,value\n1,same\n", encoding="utf-8")
            def load(label):
                return lambda: pd.DataFrame({"label": [label]})
            self.assertEqual(cached_database_frame(prod, database_fingerprint(prod), load("prod")).at[0, "label"], "prod")
            self.assertEqual(cached_database_frame(demo, database_fingerprint(demo), load("demo")).at[0, "label"], "demo")

    def test_cache_memory_and_entry_counts_are_bounded(self):
        cache = _BoundedCache(max_bytes=5, max_entries=2)
        cache.put("one", b"111", 3)
        cache.put("two", b"222", 3)
        self.assertIsNone(cache.get("one"))
        self.assertEqual(cache.get("two"), b"222")
        cache.put("too-large", b"123456", 6)
        self.assertIsNone(cache.get("too-large"))
        cache.put("a", b"", 0)
        cache.put("b", b"", 0)
        self.assertLessEqual(cache.size, 5)
        self.assertLessEqual(len(cache.entries), 2)

    def test_blob_cache_uses_fresh_metadata_for_every_read_and_changed_sha(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                clear_performance_caches()
                content, metadata_gets, blob_gets = b"old", 0, 0
                url = "https://api.github.com/repos/fake/repo/contents/data.csv"
                def get(request_url, **kw):
                    nonlocal metadata_gets, blob_gets
                    if "/git/blobs/" in request_url:
                        blob_gets += 1
                        return Reply(content=content)
                    metadata_gets += 1
                    return Reply(payload={"sha": github_blob_digest(content), "content": ""})
                fetch = self.http_functions(page, types.SimpleNamespace(get=get))["_fetch_github_file"]
                self.assertEqual(fetch(url, {}, "main")[0], b"old")
                self.assertEqual(fetch(url, {}, "main")[0], b"old")
                content = b"new"
                self.assertEqual(fetch(url, {}, "main")[0], b"new")
                self.assertEqual(metadata_gets, 3)
                self.assertEqual(blob_gets, 2)

    def test_cached_blob_cannot_bypass_revoked_authorization(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                url, headers = "https://example/contents/data.csv", {"Authorization": "fake-A"}
                remember_github_blob(url, headers, "version", b"private fixture")
                http = types.SimpleNamespace(get=lambda *a, **kw: Reply(status=403, payload={"message": "denied"}))
                data, _, error = self.http_functions(page, http)["_fetch_github_file"](url, headers, "main")
                self.assertIsNone(data)
                self.assertIn("403", error)

    def test_blob_cache_isolated_by_credentials_and_repository(self):
        url = "https://api.github.com/repos/fake/prod/contents/data.csv"
        remember_github_blob(url, {"Authorization": "fake-A"}, "same-sha", b"fixture")
        self.assertIsNone(cached_github_blob(url, {"Authorization": "fake-B"}, "same-sha"))
        self.assertIsNone(cached_github_blob(url.replace("prod", "demo"), {"Authorization": "fake-A"}, "same-sha"))
        self.assertIsNone(cached_github_blob(url, {"Authorization": "fake-A"}, "changed-sha"))

    def test_unchanged_file_skips_put_only_after_remote_sha_check(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                content, gets, puts = b"identical csv contents", [], []
                http = types.SimpleNamespace(
                    get=lambda *a, **kw: (gets.append(a[0]) or Reply(payload={"sha": github_blob_digest(content)})),
                    put=lambda *a, **kw: (puts.append(a[0]) or Reply()),
                )
                put = self.http_functions(page, http)["_put_github_bytes"]
                self.assertEqual(put("fake/repo", "main", "data.csv", content, {}, "fixture"), (True, ""))
                self.assertEqual(len(gets), 1)
                self.assertEqual(puts, [])

    def test_successful_upload_cache_still_needs_fresh_remote_confirmation(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                clear_performance_caches()
                content, gets, puts = b"old", [], []
                def get(url, **kw):
                    gets.append(url)
                    self.assertNotIn("/git/blobs/", url)  # Confirmed bytes need not be redownloaded.
                    return Reply(payload={"sha": github_blob_digest(content), "content": ""})
                def put(url, json, **kw):
                    nonlocal content
                    import base64
                    content = base64.b64decode(json["content"])
                    puts.append(url)
                    return Reply()
                env = self.http_functions(page, types.SimpleNamespace(get=get, put=put))
                self.assertTrue(env["_put_github_bytes"]("fake/repo", "main", "data.csv", b"new", {}, "fixture")[0])
                data, _, error = env["_fetch_github_file"]("https://api.github.com/repos/fake/repo/contents/data.csv", {}, "main")
                self.assertEqual(data, b"new")
                self.assertEqual(error, "")
                self.assertEqual(len(gets), 2)
                self.assertEqual(len(puts), 1)

    def test_metadata_error_does_not_skip_upload_checks(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                calls = []
                http = types.SimpleNamespace(
                    get=lambda *a, **kw: Reply(status=403, payload={"message": "denied"}),
                    put=lambda *a, **kw: calls.append(a),
                )
                ok, error = self.http_functions(page, http)["_put_github_bytes"]("fake/repo", "main", "data.csv", b"contents", {}, "fixture")
                self.assertFalse(ok)
                self.assertIn("403", error)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
