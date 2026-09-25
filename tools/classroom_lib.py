"""Shared helpers for deploy.py, new_assignment.py and clone.py. Uses the `gh` CLI for all GitHub access."""
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".classroom"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
# Lets plain git use gh's login for push/ls-remote without touching global git config.
GIT_GH_AUTH = ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]


def die(msg):
    sys.exit(f"error: {msg}")


def gh_try(*args, input=None):
    """Run gh; returns (ok, stdout, stderr)."""
    r = subprocess.run(["gh", *args], input=input, capture_output=True, text=True)
    return r.returncode == 0, r.stdout, r.stderr.strip()


def gh(*args, input=None):
    ok, out, err = gh_try(*args, input=input)
    if not ok:
        die(f"gh {' '.join(args[:2])} failed: {err}")
    return out


# ---- per-org config (~/.classroom/<org>.json: master_key, repo) -------------

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


# ---- assignment secrets (must match index.html and the workflow) -------------

def derive_secret(master_key, assignment, expiry):
    msg = f"{assignment}:{expiry}".encode()
    return hmac.new(master_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


def make_link(org, repo, assignment, expiry, secret):
    return f"https://{org.lower()}.github.io/{repo}/#{assignment}.{expiry}.{secret}"
