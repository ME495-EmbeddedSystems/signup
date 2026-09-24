"""Shared helpers for deploy.py, new_assignment.py and clone.py (standard library only)."""
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
CONFIG_DIR = Path.home() / ".classroom"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


def die(msg):
    sys.exit(f"error: {msg}")


# ---- per-org config (~/.classroom/<org>.json) -------------------------------

def config_path(org):
    return CONFIG_DIR / f"{org}.json"


def load_config(org):
    p = config_path(org)
    return json.loads(p.read_text()) if p.exists() else {}


def save_config(org, cfg):
    CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(config_path(org), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2)


def resolve_org(arg):
    org = arg or os.environ.get("CLASSROOM_ORG")
    if org:
        return org
    known = sorted(p.stem for p in CONFIG_DIR.glob("*.json")) if CONFIG_DIR.exists() else []
    if len(known) == 1:
        return known[0]
    die("specify the org with --org or CLASSROOM_ORG" + (f" (known: {', '.join(known)})" if known else ""))


def get_token(org, cfg, kind):
    """kind='admin' (write access, used by deploy/new_assignment) or 'read' (clone)."""
    keys = ("admin_token", "token") if kind == "admin" else ("token", "admin_token")
    token = os.environ.get("GITHUB_TOKEN") or next((cfg[k] for k in keys if cfg.get(k)), None)
    if token:
        return token
    if not sys.stdin.isatty():
        die(f"no token for {org}: set GITHUB_TOKEN or run interactively")
    label = "admin_token" if kind == "admin" else "token"
    token = getpass.getpass(f"Fine-grained PAT for {org} ({kind}): ").strip()
    cfg[label] = token
    save_config(org, cfg)
    return token


# ---- GitHub REST ------------------------------------------------------------

def api(method, path, token, data=None):
    """Returns (status, parsed_json_or_None). Never raises on HTTP errors."""
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(
        url, method=method, data=None if data is None else json.dumps(data).encode()
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "gh-classroom-scripts")
    try:
        with urllib.request.urlopen(req) as r:
            body, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    try:
        return status, (json.loads(body) if body else None)
    except ValueError:
        return status, None


def paginate(path, token):
    page, out = 1, []
    sep = "&" if "?" in path else "?"
    while True:
        status, items = api("GET", f"{path}{sep}per_page=100&page={page}", token)
        if status != 200:
            die(f"GET {path} failed ({status}): {items}")
        out.extend(items)
        if len(items) < 100:
            return out
        page += 1


# ---- assignment secrets (must match signup/index.html and the workflow) ------

def derive_secret(master_key, assignment, nonce):
    msg = f"{assignment}:{nonce}".encode()
    return hmac.new(master_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


def make_link(org, repo, assignment, secret):
    return f"https://{org.lower()}.github.io/{repo}/#{assignment}.{secret}"


# ---- git --------------------------------------------------------------------

def git_auth_args(token):
    """Pass the token per command so it is never written to a remote URL or git config."""
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
