"""All HTTP is mocked. Tests must never send actual LINE messages."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import line_notifications as notifications


ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "pages/1_採購單系統.py", ROOT / "pages/2_請款單系統.py",
         ROOT / "pages/99_測試區-請款單系統.py"]
TOKEN = "fixture-LINE-token-not-a-real-credential"
UID = "fixture-user"


class Stopped(BaseException):
    pass


class FakeHttp:
    def __init__(self):
        self.files, self.posts, self.puts = {}, [], []
        self.fail_put = False

    def get(self, url, **kw):
        return types.SimpleNamespace(status_code=200 if url in self.files else 404,
                                     json=lambda: {"sha": "fixture-sha"})

    def put(self, url, json, **kw):
        self.puts.append((url, json))
        if self.fail_put:
            return types.SimpleNamespace(status_code=503)
        self.files[url] = base64.b64decode(json["content"])
        return types.SimpleNamespace(status_code=200)

    def post(self, url, **kw):
        self.posts.append((url, kw))
        return types.SimpleNamespace(status_code=200)


class LinePage:
    def __init__(self, page, folder):
        self.page, self.http, self.errors = page, FakeHttp(), []
        self.demo = page.name.startswith("99_")
        self.path = Path(folder) / ("demo_line_credentials.txt" if self.demo else "line_credentials.txt")
        self.env = dict(vars(notifications))
        self.env.update(
            L_FILE=str(self.path), B_DIR=str(folder), requests=self.http,
            st=types.SimpleNamespace(secrets={
                "LINE_TOKEN": TOKEN, "LINE_UID": UID,
                "TEST_LINE_TOKEN": TOKEN, "TEST_LINE_UID": UID,
                "GITHUB_TOKEN": "fixture-github-auth", "GITHUB_REPO": "fixture/production",
                "TEST_GITHUB_TOKEN": "fixture-test-github-auth",
            }, error=self.errors.append, stop=self.stop),
            get_github_config=lambda: ("fixture-github-auth", "fixture/production", "main", "fixture"),
            get_test_github_config=lambda: ("fixture-test-github-auth", "fixture/demo", "main", "fixture"),
        )
        tree = ast.parse(page.read_text(encoding="utf-8-sig"))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in {"get_line_credentials", "save_line_credentials", "send_line_message"}]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(page), "exec"), self.env)

    @staticmethod
    def stop():
        raise Stopped()

    def save(self, token, uid=UID):
        return self.env["save_line_credentials"](token, uid)

    def send(self, text="fixture notification"):
        return self.env["send_line_message"](text)

    def state(self):
        state, _ = notifications._paths(self.path)
        return json.loads(state.read_text())


class LineNotificationTests(unittest.TestCase):
    def setUp(self):
        isolated = patch.dict(os.environ, {key: "" for key in (
            "LINE_TOKEN", "LINE_UID", "TEST_LINE_TOKEN", "TEST_LINE_UID",
            "GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_BRANCH",
            "TEST_GITHUB_TOKEN", "TEST_GITHUB_REPO", "TEST_GITHUB_BRANCH",
        )})
        isolated.start()
        self.addCleanup(isolated.stop)

    def each_page(self, scenario):
        for page in PAGES:
            with self.subTest(page=page.name), tempfile.TemporaryDirectory() as folder:
                scenario(LinePage(page, folder))

    def test_default_off_even_with_old_token_and_deployment_secret(self):
        def scenario(h):
            h.path.write_text(TOKEN + "\n" + UID, encoding="utf-8")
            self.assertEqual(h.env["get_line_credentials"](), ("", ""))
            self.assertFalse(h.send())
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_whitespace_only_save_disables_without_falling_back(self):
        def scenario(h):
            self.assertTrue(h.save(TOKEN))
            self.assertTrue(h.send())
            self.assertFalse(h.save(" \t\n\u3000 ", " \t "))
            h.path.write_text(TOKEN + "\n" + UID, encoding="utf-8")  # Simulate old tracked-file restoration.
            self.assertFalse(h.send())
            self.assertEqual(h.env["get_line_credentials"](), ("", ""))
            self.assertFalse(h.state()["enabled"])
            self.assertEqual(len(h.http.posts), 1)
        self.each_page(scenario)

    def test_uid_without_token_cannot_send(self):
        def scenario(h):
            self.assertFalse(h.save("", UID))
            self.assertFalse(h.send())
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_filled_saved_token_and_message_send_once(self):
        def scenario(h):
            self.assertTrue(h.save("  " + TOKEN + " \n", " " + UID + " "))
            self.assertEqual(h.env["get_line_credentials"](), (TOKEN, UID))
            self.assertTrue(h.send("  fixture notification  "))
            self.assertEqual(len(h.http.posts), 1)
            _, request = h.http.posts[0]
            self.assertEqual(request["headers"]["Authorization"], "Bearer " + TOKEN)
            self.assertIn("fixture notification", request["json"]["messages"][0]["text"])
        self.each_page(scenario)

    def test_empty_messages_never_send_even_with_demo_prefix(self):
        def scenario(h):
            h.save(TOKEN)
            for message in ("", " \t\n\u3000 ", None):
                self.assertFalse(h.send(message))
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_saving_settings_never_sends_a_line_test_message(self):
        def scenario(h):
            h.save(TOKEN)
            h.save("")
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_only_nonsecret_preference_is_published(self):
        def scenario(h):
            h.save(TOKEN)
            h.save("")
            self.assertEqual(len(h.http.puts), 2)
            for url, body in h.http.puts:
                self.assertTrue(url.endswith("line_notification_settings.json"))
                decoded = base64.b64decode(body["content"]).decode()
                self.assertNotIn(TOKEN, decoded)
                self.assertNotIn(base64.b64encode(TOKEN.encode()).decode(), decoded)
                state = json.loads(decoded)
                self.assertLessEqual(set(state), {"version", "enabled", "token_sha256"})
        self.each_page(scenario)

    def test_disabled_preference_survives_host_loss_and_old_credentials(self):
        def scenario(h):
            h.save(TOKEN)
            h.save("")
            state_file, override = notifications._paths(h.path)
            published = list(h.http.files.values())[-1]
            override.unlink()  # Only a fixture file in TemporaryDirectory.
            state_file.write_bytes(published)
            h.path.write_text(TOKEN + "\n" + UID, encoding="utf-8")
            self.assertFalse(h.send())
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_enabled_preference_requires_matching_secret_after_host_loss(self):
        def scenario(h):
            h.save(TOKEN)
            _, override = notifications._paths(h.path)
            override.unlink()
            self.assertTrue(h.send())  # Matching fake deployment secret.
            h.env["st"].secrets["LINE_TOKEN"] = "different-fixture"
            h.env["st"].secrets["TEST_LINE_TOKEN"] = "different-fixture"
            self.assertFalse(h.send())
            self.assertEqual(len(h.http.posts), 1)
        self.each_page(scenario)

    def test_blank_authoritative_override_never_uses_nonempty_secrets(self):
        def scenario(h):
            h.save(TOKEN)
            _, override = notifications._paths(h.path)
            override.write_text("b64:\nb64:", encoding="utf-8")
            self.assertFalse(h.send())
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_failed_preference_save_cannot_enable_notifications(self):
        def scenario(h):
            h.http.fail_put = True
            with self.assertRaises(Stopped):
                h.save(TOKEN)
            self.assertFalse(h.send())
            self.assertTrue(h.errors)
            self.assertFalse(h.state()["enabled"])
        self.each_page(scenario)

    def test_failed_disable_publish_still_blocks_local_sends_and_reports_error(self):
        def scenario(h):
            h.save(TOKEN)
            h.http.fail_put = True
            with self.assertRaises(Stopped):
                h.save("")
            self.assertFalse(h.send())
            self.assertTrue(h.errors)
        self.each_page(scenario)

    def test_production_settings_shared_by_procurement_and_payment(self):
        with tempfile.TemporaryDirectory() as folder:
            procurement, payment = [LinePage(page, folder) for page in PAGES[:2]]
            procurement.save(TOKEN)
            self.assertTrue(payment.send())
            payment.save("")
            self.assertFalse(procurement.send())
            self.assertEqual(procurement.http.posts, [])

    def test_demo_settings_cannot_enable_or_disable_production(self):
        with tempfile.TemporaryDirectory() as folder:
            prod, demo = [LinePage(page, folder) for page in PAGES[1:]]
            prod.save(TOKEN)
            self.assertFalse(demo.send())
            demo.save("demo-fixture-token")
            demo.save("")
            self.assertTrue(prod.send())
            self.assertFalse(demo.send())
            self.assertTrue(all("demo_line_notification_settings.json" in url for url in demo.http.files))

    def test_corrupt_or_nonboolean_preference_is_fail_closed(self):
        def scenario(h):
            state_file, _ = notifications._paths(h.path)
            for text in ("invalid json", "null", "[]", '{"enabled": "true"}', '{"enabled": true}'):
                state_file.write_text(text, encoding="utf-8")
                self.assertFalse(h.send())
            self.assertEqual(h.http.posts, [])
        self.each_page(scenario)

    def test_legacy_encoding_is_compatible_only_after_explicit_enable(self):
        def scenario(h):
            h.save(TOKEN)
            _, override = notifications._paths(h.path)
            override.unlink()
            h.env["st"].secrets = {}
            for value in (TOKEN, base64.b64encode(TOKEN.encode()).decode(),
                          "b64:" + base64.b64encode(TOKEN.encode()).decode()):
                h.path.write_text(value + "\n" + UID, encoding="utf-8")
                self.assertTrue(h.send())
            self.assertEqual(len(h.http.posts), 3)
        self.each_page(scenario)

    def test_checked_in_preferences_contain_only_nonsecret_state(self):
        for name in ("line_notification_settings.json", "demo_line_notification_settings.json"):
            state = json.loads((ROOT / name).read_text())
            self.assertEqual(state["version"], 1)
            self.assertIsInstance(state["enabled"], bool)
            self.assertLessEqual(set(state), {"version", "enabled", "token_sha256"})
            if state["enabled"]:
                self.assertRegex(state["token_sha256"], r"^[0-9a-f]{64}$")

    def test_demo_deployment_secrets_do_not_fall_back_to_production(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as folder:
            self.assertEqual(notifications.deployment_line_credentials({"LINE_TOKEN": TOKEN}, test=True), ("", ""))
            self.assertEqual(notifications.production_repository_config(folder, {"TEST_GITHUB_TOKEN": "demo-only"})[0], "")


if __name__ == "__main__":
    unittest.main()
