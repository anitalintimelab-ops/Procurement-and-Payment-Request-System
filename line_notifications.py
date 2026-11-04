"""Explicit LINE opt-in; empty saved settings always disable notifications.

Only the non-secret enabled flag/token fingerprint is published to GitHub.
Credential overrides remain local and ignored by Git; after host replacement,
only a matching deployment secret can re-enable a previously enabled setting.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading


LINE_SETTINGS_LOCK = threading.RLock()


def _text(value):
    return "" if value is None else str(value).strip()


def _paths(credential_file):
    credential_file = Path(credential_file)
    prefix = "demo_" if credential_file.name.startswith("demo_") else ""
    return (
        credential_file.parent / f"{prefix}line_notification_settings.json",
        credential_file.parent / f"{prefix}line_notification_credentials.local",
    )


def _decode(value):
    value = _text(value)
    if not value:
        return ""
    try:
        decoded = base64.b64decode(value[4:] if value.startswith("b64:") else value, validate=True).decode()
        if value.startswith("b64:") or (decoded and all(c.isprintable() for c in decoded)):
            return decoded.strip()
    except (ValueError, UnicodeError):
        pass
    return "" if value.startswith("b64:") else value


def _read_credentials(filepath):
    lines = Path(filepath).read_text(encoding="utf-8-sig").splitlines()
    return tuple(_decode(lines[i]) if len(lines) > i else "" for i in (0, 1))


def get_line_settings(credential_file, fallback_token="", fallback_uid=""):
    with LINE_SETTINGS_LOCK:
        state_file, override_file = _paths(credential_file)
        try:
            state = json.loads(state_file.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return "", ""  # Missing/corrupt state is not consent to broadcast.
        if not isinstance(state, dict) or state.get("enabled") is not True or not state.get("token_sha256"):
            return "", ""
        try:
            if override_file.exists():
                candidates = [_read_credentials(override_file)]
            else:
                candidates = [(_text(fallback_token), _text(fallback_uid))]
                if Path(credential_file).exists():
                    candidates.append(_read_credentials(credential_file))
        except (OSError, ValueError, UnicodeError):
            return "", ""
        for token, uid in candidates:
            token, uid = _text(token), _text(uid)
            if token and hashlib.sha256(token.encode()).hexdigest() == state["token_sha256"]:
                return token, uid
        return "", ""


def _atomic_text(path, value):
    path = Path(path)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".line-setting-", delete=False) as stream:
            staged = stream.name
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
    finally:
        if staged and os.path.exists(staged):
            os.unlink(staged)


def save_line_settings(credential_file, token, uid, publish):
    """An empty token means OFF, never 'reuse the old token'. No LINE call here."""
    token, uid = _text(token), _text(uid)
    state_file, override_file = _paths(credential_file)
    with LINE_SETTINGS_LOCK:
        # Fail closed while publishing. An error cannot accidentally enable sends.
        _atomic_text(state_file, json.dumps({"version": 1, "enabled": False}, indent=2))
        _atomic_text(override_file, "\n".join(
            "b64:" + base64.b64encode(value.encode()).decode() for value in (token, uid)
        ))
        state = {"version": 1, "enabled": bool(token)}
        if token:
            state["token_sha256"] = hashlib.sha256(token.encode()).hexdigest()
        # Publish only a separate non-secret file; never upload the override.
        try:
            _atomic_text(state_file, json.dumps(state, indent=2))
            ok, error = publish(str(state_file))
            if not ok:
                raise ValueError(error or "LINE 通知開關尚未保存到 GitHub")
        except Exception:
            _atomic_text(state_file, json.dumps({"version": 1, "enabled": False}, indent=2))
            raise
        return bool(token)


def deployment_line_credentials(secrets, test=False):
    prefix = "TEST_" if test else ""
    values = []
    for key in ("LINE_TOKEN", "LINE_UID"):
        value = _text(os.getenv(prefix + key, ""))
        try:
            value = value or _text(secrets.get(prefix + key, ""))
            if test:
                value = value or _text(secrets.get("test", {}).get(key.lower(), ""))
        except Exception:
            pass
        values.append(value)
    return tuple(values)


def send_line_notification(credential_file, message, http, fallback_token="", fallback_uid="", prefix=""):
    message = _text(message)
    if not message:
        return False
    if prefix:
        message = f"{prefix}\n{message}"
    with LINE_SETTINGS_LOCK:
        token, _ = get_line_settings(credential_file, fallback_token, fallback_uid)
        if not token:
            return False
        try:
            response = http.post(
                "https://api.line.me/v2/bot/message/broadcast",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                json={"messages": [{"type": "text", "text": message}]}, timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False


def production_repository_config(base_dir, secrets):
    """Procurement uses the same production repository as payment settings."""
    try:
        github = secrets.get("github", {})
        values = [os.getenv(f"GITHUB_{key}", "") or secrets.get(f"GITHUB_{key}", "")
                  or github.get(key.lower(), "") for key in ("TOKEN", "REPO", "BRANCH")]
    except Exception:
        values = [os.getenv(f"GITHUB_{key}", "") for key in ("TOKEN", "REPO", "BRANCH")]
    credential_file = Path(base_dir) / "github_credentials.txt"
    if credential_file.exists():
        lines = credential_file.read_text(encoding="utf-8-sig").splitlines()
        for index in range(3):
            if not values[index] and len(lines) > index:
                values[index] = _decode(lines[index]) if index == 0 else lines[index].strip()
    return (_text(values[0]), _text(values[1]) or "anitalintimelab-ops/Procurement-and-Payment-Request-System",
            _text(values[2]) or "main")


def publish_line_state(filepath, config, http):
    token, repo, branch = config[:3]
    if not token or not repo:
        return False, "缺少 GitHub 設定，LINE 已在本機停用；請補齊設定後重新儲存"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo}/contents/{Path(filepath).name}"
    content = base64.b64encode(Path(filepath).read_bytes()).decode()
    for _ in range(3):
        response = http.get(url, params={"ref": branch}, headers=headers, timeout=20)
        if response.status_code not in (200, 404):
            return False, f"讀取 LINE 通知開關失敗（{response.status_code}）"
        data = {"message": "Update LINE notification preference (no credentials)",
                "content": content, "branch": branch}
        if response.status_code == 200:
            data["sha"] = response.json()["sha"]
        response = http.put(url, headers=headers, json=data, timeout=20)
        if response.status_code in (200, 201):
            return True, ""
        if response.status_code != 409:
            return False, f"保存 LINE 通知開關失敗（{response.status_code}）；請重新儲存"
    return False, "LINE 通知開關版本衝突，請重新儲存"
