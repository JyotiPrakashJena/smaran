import base64
import requests
import streamlit as st
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "smaran.db"

def _github_cfg():
    try:
        cfg = st.secrets["github"]
        return cfg["token"], cfg["repo"], cfg.get("branch", "main"), cfg.get("db_path", "data/smaran.db")
    except Exception:
        return None, None, None, None

def pull_db():
    """Download latest smaran.db from GitHub. Called once on app startup."""
    token, repo, branch, db_path = _github_cfg()
    if not token:
        return
    url = f"https://api.github.com/repos/{repo}/contents/{db_path}?ref={branch}"
    r = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"])
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH.write_bytes(content)

def push_db():
    """Upload smaran.db back to GitHub. Called after every write."""
    token, repo, branch, db_path = _github_cfg()
    if not token or not DB_PATH.exists():
        return
    content = base64.b64encode(DB_PATH.read_bytes()).decode()
    url = f"https://api.github.com/repos/{repo}/contents/{db_path}"
    # get current SHA (needed for update)
    r = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {"message": "chore: sync db", "content": content, "branch": branch}
    if sha:
        payload["sha"] = sha
    requests.put(url, json=payload, headers={"Authorization": f"token {token}"}, timeout=15)
