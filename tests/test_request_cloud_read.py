"""Cloud receipts must read the file version returned by GitHub metadata."""
import ast
import base64
import types
import unittest

from test_request_save_reload import PAGES


class Response:
    def __init__(self, status=200, payload=None, content=b"", text="fixture"):
        self.status_code, self.payload = status, payload
        self.content, self.text = content, text

    def json(self):
        return self.payload


class CloudReadTests(unittest.TestCase):
    def load_fetch(self, page, get):
        tree = ast.parse(page.read_text(encoding="utf-8-sig"))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_fetch_github_file")
        namespace = {"requests": types.SimpleNamespace(get=get), "base64": base64}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(page), "exec"), namespace)
        return namespace["_fetch_github_file"]

    def test_large_receipt_uses_blob_version_not_raw_branch_cache(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                url = "https://api.github.com/repos/test/repo/contents/database.csv.part-001.csv"
                blob_url = "https://api.github.com/repos/test/repo/git/blobs/new-version-sha"
                latest = "單號,狀態\n20261103-07,已駁回\n".encode()
                calls = []
                def get(request_url, headers, timeout):
                    calls.append(request_url)
                    if request_url == url + "?ref=main":
                        return Response(payload={"sha": "new-version-sha", "content": "",
                                                 "download_url": "https://raw.example/stale-main.csv"})
                    self.assertEqual(request_url, blob_url)
                    self.assertEqual(headers["Accept"], "application/vnd.github.raw+json")
                    return Response(content=latest)
                data, sha, error = self.load_fetch(page, get)(url, {"Authorization": "fake"}, "main")
                self.assertEqual(data, latest)
                self.assertEqual(sha, "new-version-sha")
                self.assertEqual(error, "")
                self.assertEqual(len(calls), 2)

    def test_inline_small_file_is_unchanged(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                content = b'{"parts": []}'
                get = lambda *a, **kw: Response(payload={
                    "content": base64.b64encode(content).decode(), "sha": "manifest-sha"})
                self.assertEqual(self.load_fetch(page, get)("https://example/contents/file", {}, "main"),
                                 (content, "manifest-sha", ""))

    def test_blob_download_failure_does_not_accept_stale_fallback(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                def get(url, **kw):
                    if "/git/blobs/" in url:
                        return Response(status=403)
                    return Response(payload={"sha": "version-sha", "content": "",
                                             "download_url": "https://raw.example/stale.csv"})
                data, _, error = self.load_fetch(page, get)("https://example/contents/file", {}, "main")
                self.assertIsNone(data)
                self.assertIn("403", error)

    def test_missing_manifest_preserves_legacy_fallback_contract(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                get = lambda *a, **kw: Response(status=404, payload={"message": "not found"})
                self.assertEqual(self.load_fetch(page, get)("https://example/contents/file", {}, "main"),
                                 (b"", None, ""))


if __name__ == "__main__":
    unittest.main()
