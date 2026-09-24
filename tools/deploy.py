#!/usr/bin/env python3
"""Publish this repository as the signup repo of a GitHub org.

    python tools/deploy.py <org> [--repo NAME] [--app-id N --private-key app.pem]

Creates the repo if needed, pushes this directory's files, enables Pages, and generates the
org's master key. Safe to re-run: files are refreshed but the org's assignments.json is kept.
"""
import argparse
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from classroom_lib import GIT_GH_AUTH, die, gh, gh_try, load_config, save_config

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "__pycache__", ".DS_Store"}


def push_files(org, repo):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        gh("repo", "clone", f"{org}/{repo}", str(work))
        # Build on the remote's main if it exists (re-deploy); otherwise start it.
        if subprocess.run(["git", "checkout", "-q", "-B", "main", "origin/main"],
                          cwd=work, stderr=subprocess.DEVNULL).returncode != 0:
            subprocess.run(["git", "checkout", "-q", "-B", "main"], cwd=work, check=True)
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            for fn in filenames:
                src = Path(dirpath) / fn
                rel = src.relative_to(ROOT)
                dst = work / rel
                if fn in SKIP or (str(rel) == "assignments.json" and dst.exists()):
                    continue  # keep the org's existing assignments
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        subprocess.run(["git", "add", "-A"], cwd=work, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work).returncode == 0:
            print("Repo files already up to date.")
            return
        ident = ["-c", "user.name=classroom-deploy", "-c", "user.email=classroom-deploy@users.noreply.github.com"]
        subprocess.run(["git", *ident, "commit", "-q", "-m", "Deploy classroom files"], cwd=work, check=True)
        subprocess.run(["git", *GIT_GH_AUTH, "push", "-q", "origin", "main"], cwd=work, check=True)
        print("Pushed files.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("org")
    ap.add_argument("--repo", help="repo name (default: signup, or the one used before)")
    ap.add_argument("--app-id", help="GitHub App ID; with --private-key, sets the Actions secrets")
    ap.add_argument("--private-key", help="path to the App's .pem private key")
    args = ap.parse_args()
    org = args.org

    cfg = load_config(org)
    repo = args.repo or cfg.get("repo", "signup")
    cfg["repo"] = repo
    cfg.setdefault("master_key", secrets.token_hex(32))
    save_config(org, cfg)

    ok, out, _ = gh_try("api", f"repos/{org}/{repo}", "--jq", ".private")
    if not ok:
        gh("repo", "create", f"{org}/{repo}", "--public", "--description", "Self-service assignment repositories")
        print(f"Created {org}/{repo}.")
    elif out.strip() == "true":
        die(f"{org}/{repo} is private; it must be public so students can open issues and load Pages")

    push_files(org, repo)

    ok, _, err = gh_try("api", "-X", "POST", f"repos/{org}/{repo}/pages",
                        "-f", "source[branch]=main", "-f", "source[path]=/")
    if ok:
        print("Enabled GitHub Pages.")
    elif "already" not in err.lower():
        print(f"warning: could not enable Pages ({err}); enable it in the repo's Settings > Pages (branch main)")

    if args.app_id and args.private_key:
        for name, value in [("MASTER_KEY", cfg["master_key"]), ("APP_ID", args.app_id),
                            ("APP_PRIVATE_KEY", Path(args.private_key).read_text())]:
            gh("secret", "set", name, "--repo", f"{org}/{repo}", "--body", value)
            print(f"Set Actions secret {name}.")
    else:
        print(f"""
Add these Actions secrets at https://github.com/{org}/{repo}/settings/secrets/actions
  APP_ID           your GitHub App's ID
  APP_PRIVATE_KEY  contents of the App's .pem file
  MASTER_KEY       {cfg['master_key']}
or re-run with --app-id <ID> --private-key <file.pem>.""")


if __name__ == "__main__":
    main()
