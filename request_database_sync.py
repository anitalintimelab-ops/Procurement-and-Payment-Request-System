"""Versioned cloud snapshots for the production and demo payment databases."""
import base64
import io
from itertools import chain
import json
import os
import re
import tempfile
from urllib.parse import quote

import pandas as pd

from approval_state import merge_database_snapshots, normalize_approval_statuses
from request_performance import github_blob_digest
from request_persistence import apply_database_changes


PURGED_IDS = "purged_request_ids"
CLEANUP_STATES = frozenset({"已核准", "已駁回", "已刪除"})


def request_ids(frame):
    return frame["單號"].fillna("").astype(str).str.strip()


def next_request_id(frame, purged_ids, day):
    prefix = day.strftime("%Y%m%d") + "-"
    suffixes = (key[len(prefix):] for key in chain(request_ids(frame), purged_ids)
                if key.startswith(prefix))
    return f"{prefix}{max((int(s) for s in suffixes if s.isascii() and s.isdigit()), default=0) + 1:02d}"


def read_database_chunks(filepath, fetch, headers, repo, ref):
    filename = os.path.basename(filepath)
    root = f"https://api.github.com/repos/{repo}/contents/"
    manifest_name = filename + ".manifest.json"
    raw, sha, error = fetch(root + manifest_name, headers, ref)
    if error or not raw:
        return None, error
    try:
        manifest = json.loads(raw.decode("utf-8"))
        if manifest.get("format") != "timelab-database-chunks-v1" or manifest.get("source") != filename:
            raise ValueError("資料庫清單不屬於目前環境")
        purged = manifest.get(PURGED_IDS, [])
        if not isinstance(purged, list) or any(
            not isinstance(key, str) or not key or key.strip() != key for key in purged
        ):
            raise ValueError("清理紀錄格式不正確")
        blobs = {manifest_name: sha}
        frames = []
        for part in manifest["parts"]:
            name = part["name"]
            if not re.fullmatch(re.escape(filename) + r"\.part-[0-9]+\.csv", name) or name in blobs:
                raise ValueError("分段名稱重複或不屬於目前環境")
            content, part_sha, error = fetch(root + name, headers, ref)
            if error or not content:
                raise ValueError(error or f"找不到分段 {name}")
            frame = pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8-sig").fillna("")
            if len(frame) != part["rows"]:
                raise ValueError(f"{name} 筆數不符")
            blobs[name] = part_sha
            frames.append(frame)
        if not frames:
            raise ValueError("manifest 沒有資料分段")
        merged = pd.concat(frames, ignore_index=True, sort=False)
        keys = request_ids(merged)
        if (len(merged) != manifest["row_count"] or not keys.is_unique
                or keys.eq("").any() or keys.isin(purged).any()):
            raise ValueError("資料筆數、單號或清理紀錄不一致")
        merged.attrs.update({PURGED_IDS: tuple(purged), "cloud_blobs": blobs})
        return merged, ""
    except Exception as exc:
        return None, f"讀取分段資料庫失敗：{exc}"


def prepare_snapshot(remote, local, changes=None, purge=None):
    """Only explicit cleanup can remove rows; old snapshots cannot restore them."""
    purged = set(remote.attrs.get(PURGED_IDS, ())) if remote is not None else set()
    if purge is not None:
        if remote is None or not purge:
            raise ValueError("未確認雲端清理對象")
        states = normalize_approval_statuses(remote).set_index(request_ids(remote))["狀態"]
        for key, expected in purge.items():
            if key not in states.index or states.at[key] != expected or expected not in CLEANUP_STATES:
                raise ValueError(f"單號 {key} 已不存在或狀態已變更，本批未清理，請重新整理")
        purged.update(purge)
        result = remote.loc[~request_ids(remote).isin(purge)].copy()
    elif changes is not None:
        if purged.intersection(changes):
            raise ValueError("本次存檔包含已永久清理的單號，請重新整理")
        result = apply_database_changes(remote, changes) if remote is not None else local
    else:
        if local is not None:
            local = local.loc[~request_ids(local).isin(purged)]
        result = merge_database_snapshots(remote, local)
    if result is None or request_ids(result).isin(purged).any():
        raise ValueError("清理紀錄與待上傳資料不一致")
    return result, sorted(purged)


def _checked(response, status, operation):
    if response.status_code != status:
        raise ValueError(f"{operation}失敗（GitHub HTTP {response.status_code}）")
    return response.json()


def snapshot_head(http, repo, branch, headers):
    url = f"https://api.github.com/repos/{repo}/commits/{quote(branch, safe='')}"
    payload = _checked(http.get(url, headers=headers, timeout=20), 200, "確認分支版本")
    return payload["sha"], payload["commit"]["tree"]["sha"]


def publish_snapshot(http, repo, branch, headers, parent, base_tree, files, previous, message):
    """Publish parts and their manifest together, without forcing a stale branch."""
    root = f"https://api.github.com/repos/{repo}/git/"
    tree = []
    for path, content in files.items():
        digest = github_blob_digest(content)
        if previous.get(path) == digest:
            continue
        blob = _checked(http.post(root + "blobs", headers=headers, timeout=90, json={
            "content": base64.b64encode(content).decode("ascii"), "encoding": "base64",
        }), 201, "建立資料分段")
        if blob["sha"] != digest:
            raise ValueError("GitHub 回傳的資料分段雜湊不符")
        tree.append(dict(path=path, mode="100644", type="blob", sha=digest))
    for path in previous.keys() - files.keys():
        tree.append(dict(path=path, mode="100644", type="blob", sha=None))
    if not tree:
        return
    created_tree = _checked(http.post(root + "trees", headers=headers, timeout=20, json={
        "base_tree": base_tree, "tree": tree,
    }), 201, "建立完整資料庫版本")
    commit = _checked(http.post(root + "commits", headers=headers, timeout=20, json={
        "message": message, "tree": created_tree["sha"], "parents": [parent],
    }), 201, "提交資料庫版本")
    _checked(http.patch(root + "refs/heads/" + quote(branch, safe="/"), headers=headers, timeout=20,
                        json={"sha": commit["sha"], "force": False}), 200, "更新分支，請重新整理後重試")


def sync_database(filepath, *, http, fetch, read_chunks, read_local, split,
                  repo, branch, headers, changes=None, purge=None):
    parent, tree = snapshot_head(http, repo, branch, headers)
    remote, error = read_chunks(filepath, headers, repo, parent)
    if error:
        raise ValueError(error)
    filename = os.path.basename(filepath)
    previous = remote.attrs["cloud_blobs"] if remote is not None else {}
    if remote is None:
        raw, _, error = fetch(f"https://api.github.com/repos/{repo}/contents/{filename}", headers, parent)
        if error:
            raise ValueError(error)
        if raw:
            remote = pd.read_csv(io.BytesIO(raw), dtype=str, encoding="utf-8-sig").fillna("")
    local = read_local(filepath) if os.path.exists(filepath) and purge is None else None
    if local is not None and "單號" not in local.columns:
        raise ValueError("本機資料庫缺少單號，未同步")
    candidate, purged = prepare_snapshot(remote, local, changes=changes, purge=purge)
    with tempfile.TemporaryDirectory(prefix="timelab-cloud-snapshot-") as staging:
        path = os.path.join(staging, filename)
        candidate.to_csv(path, index=False, encoding="utf-8-sig")
        parts, manifest, error = split(path)
    if error:
        raise ValueError(error)
    if purged:
        manifest[PURGED_IDS] = purged
    files = {name: content for name, content, _ in parts}
    files[filename + ".manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    publish_snapshot(http, repo, branch, headers, parent, tree, files, previous,
                     f"Update {filename} snapshot from TimeLab System")
    return f"同步成功（共 {manifest['row_count']} 筆）"


def verify_purge(frame, purge):
    if (frame is None or not set(purge).issubset(frame.attrs.get(PURGED_IDS, ()))
            or request_ids(frame).isin(purge).any()):
        raise ValueError("雲端回讀尚未確認清理成功，請重新整理確認")
