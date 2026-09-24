#!/usr/bin/env python3
"""Publish this repository as the signup repo of a GitHub org.

    python tools/deploy.py <org> [--repo NAME] [--app-id N --private-key app.pem]

Creates the repo if needed, pushes the contents of this repository (no local git repo or
remote required), enables Pages and generates the org's master key. Safe to re-run: it
refreshes the files but keeps the org's assignments.json.
"""
import argparse
import base64
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from classroom_lib import api, die, get_token, git_auth_args, load_config, save_config

ROOT = Path(__file__).resolve().parent.parent  # this repository
SKIP = {".git", "__pycache__", ".DS_Store"}


def git(args, cwd, token=None):
    cmd = ["git"] + (git_auth_args(token) if token else []) + args
    subprocess.run(cmd, cwd=cwd, check=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


def push_template(org, repo, token):
    url = f"https://github.com/{org}/{repo}.git"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        git(["clone", "-q", url, str(work)], tmp, token)
        git(["checkout", "-q", "-B", "main"], work)
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            for fn in filenames:
                if fn in SKIP:
                    continue
                src = Path(dirpath) / fn
                rel = src.relative_to(ROOT)
                dst = work / rel
                if str(rel) == "assignments.json" and dst.exists():
                    continue  # keep the org's existing assignments
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        git(["add", "-A"], work)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work).returncode == 0:
            print("Repo files already up to date.")
            return
        ident = ["-c", "user.name=classroom-deploy", "-c", "user.email=classroom-deploy@users.noreply.github.com"]
        git(ident + ["commit", "-q", "-m", "Deploy classroom files"], work)
        git(["push", "-q", "origin", "main"], work, token)
        print("Pushed files.")


def set_secret(org, repo, token, name, value):
    from nacl import public  # PyNaCl, optional

    status, key = api("GET", f"/repos/{org}/{repo}/actions/secrets/public-key", token)
    if status != 200:
        die(f"could not read the repo's public key ({status}): {key}")
    sealed = public.SealedBox(public.PublicKey(base64.b64decode(key["key"]))).encrypt(value.encode())
    status, out = api(
        "PUT", f"/repos/{org}/{repo}/actions/secrets/{name}", token,
        {"encrypted_value": base64.b64encode(sealed).decode(), "key_id": key["key_id"]},
    )
    if status not in (201, 204):
        die(f"could not set secret {name} ({status}): {out}")
    print(f"Set Actions secret {name}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("org")
    ap.add_argument("--repo", help="name of the repo to create in the org (default: signup, or the one used before)")
    ap.add_argument("--app-id", help="GitHub App ID; with --private-key, sets the Actions secrets for you (needs PyNaCl)")
    ap.add_argument("--private-key", help="path to the App's .pem private key")
    args = ap.parse_args()
    org = args.org

    cfg = load_config(org)
    repo = args.repo or cfg.get("repo", "signup")
    cfg["repo"] = repo
    if "master_key" not in cfg:
        cfg["master_key"] = secrets.token_hex(32)
        save_config(org, cfg)
        print(f"Generated a master key for {org} in ~/.classroom/{org}.json")
    save_config(org, cfg)
    token = get_token(org, cfg, "admin")

    status, info = api("GET", f"/repos/{org}/{repo}", token)
    if status == 404:
        status, info = api("POST", f"/orgs/{org}/repos", token, {
            "name": repo, "private": False, "has_issues": True,
            "description": "Self-service assignment repositories",
        })
        if status != 201:
            die(f"could not create {org}/{repo} ({status}): {info}")
        print(f"Created {org}/{repo}.")
    elif status != 200:
        die(f"could not read {org}/{repo} ({status}): {info}")
    elif info.get("private"):
        die(f"{org}/{repo} is private; it must be public so students can open issues and load the Pages site")

    push_template(org, repo, token)

    status, out = api("POST", f"/repos/{org}/{repo}/pages", token,
                      {"source": {"branch": "main", "path": "/"}})
    if status == 201:
        print("Enabled GitHub Pages.")
    elif status != 409:
        print(f"warning: could not enable Pages ({status}): {out}\n"
              f"  Enable it manually: {org}/{repo} > Settings > Pages > Deploy from branch main")

    if args.app_id and args.private_key:
        try:
            import nacl  # noqa: F401
        except ImportError:
            die("--app-id/--private-key need PyNaCl: pip install pynacl (or set the secrets by hand)")
        set_secret(org, repo, token, "MASTER_KEY", cfg["master_key"])
        set_secret(org, repo, token, "APP_ID", args.app_id)
        set_secret(org, repo, token, "APP_PRIVATE_KEY", Path(args.private_key).read_text())
    else:
        print(f"""
Remaining setup for {org} (one time):
  1. Create a GitHub App owned by {org}: {org} > Settings > Developer settings > GitHub Apps > New.
     - Uncheck "Webhook > Active"
     - Repository permissions: Administration (read & write), Contents (read & write), Metadata (read)
     - Where can it be installed: Only on this account
     Generate a private key (.pem), then install the App on {org} with "All repositories".
  2. Add these Actions secrets at https://github.com/{org}/{repo}/settings/secrets/actions
       APP_ID           the App's ID
       APP_PRIVATE_KEY  the full contents of the .pem file
       MASTER_KEY       {cfg['master_key']}
     (or re-run: python tools/deploy.py {org} --app-id <ID> --private-key <file.pem>, needs PyNaCl)
  3. Create an assignment:  python tools/new_assignment.py F26_HW1 --org {org}""")


if __name__ == "__main__":
    main()
