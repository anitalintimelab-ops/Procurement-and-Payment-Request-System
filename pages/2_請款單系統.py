def sync_to_github_core(filepath):
    """將本機檔案同步到 GitHub Contents API；遇到 409 時重新取得 sha 後重試。"""
    filename = os.path.basename(filepath)
    token, repo = DEFAULT_GITHUB_TOKEN, DEFAULT_GITHUB_REPO

    if os.path.exists(G_FILE):
        try:
            with open(G_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            raw_t = "".join(c for c in lines[0] if c.isascii()).strip() if len(lines) > 0 else ""
            r_val = "".join(c for c in lines[1] if c.isascii()).strip() if len(lines) > 1 else ""
            if raw_t:
                if raw_t.startswith("ghp_"):
                    token = raw_t
                else:
                    try:
                        token = base64.b64decode(raw_t).decode()
                    except Exception:
                        token = raw_t
            if r_val:
                repo = r_val
        except Exception:
            pass

    if not token or not repo or not os.path.exists(filepath):
        return False, "GitHub Token、Repository 或本機檔案不存在"

    get_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache",
    }

    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        data = {
            "message": f"Auto sync {filename} from TimeLab System",
            "content": content,
        }

        # 409 代表遠端版本可能在讀取 sha 後已變更；重新讀取最新 sha 再重試。
        for attempt in range(3):
            remote = requests.get(get_url, headers=headers, timeout=5)
            if remote.status_code == 200:
                sha = remote.json().get("sha")
                if sha:
                    data["sha"] = sha
            elif remote.status_code == 404:
                data.pop("sha", None)
            else:
                try:
                    detail = remote.json().get("message", remote.text)
                except Exception:
                    detail = remote.text
                return False, f"讀取 GitHub 遠端檔案失敗（錯誤碼：{remote.status_code}）：{detail}"

            resp = requests.put(get_url, headers=headers, json=data, timeout=10)
            if resp.status_code in (200, 201):
                return True, "同步成功"
            if resp.status_code != 409 or attempt == 2:
                try:
                    detail = resp.json().get("message", resp.text)
                except Exception:
                    detail = resp.text
                return False, f"上傳 {filename} 被 GitHub 拒絕（錯誤碼：{resp.status_code}）：{detail}"

            # 下一輪會重新 GET 最新 sha。
            time.sleep(0.5)

    except Exception as e:
        return False, f"上傳 {filename} 時發生錯誤：{e}"
