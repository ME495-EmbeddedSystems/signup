#!/usr/bin/env python3
"""Clone (or pull) every student repo for an assignment.

    python clone.py F26_HW1 --org myorg [dest] [--ssh]

Repos are the org's repos named "<prefix>-<username>". Uses a fine-grained PAT
(GITHUB_TOKEN or ~/.classroom/<org>.json) that only needs Metadata + Contents read.
"""
import argparse
import subprocess
from pathlib import Path

from classroom_lib import die, get_token, git_auth_args, load_config, paginate, resolve_org


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prefix", help="assignment prefix, e.g. F26_HW1")
    ap.add_argument("dest", nargs="?", help="destination directory (default: ./<prefix>)")
    ap.add_argument("--org")
    ap.add_argument("--ssh", action="store_true", help="clone over SSH instead of HTTPS with the token")
    args = ap.parse_intermixed_args()

    org = resolve_org(args.org)
    cfg = load_config(org)
    token = get_token(org, cfg, "read")
    dest = Path(args.dest or args.prefix)
    dest.mkdir(parents=True, exist_ok=True)

    repos = paginate(f"/orgs/{org}/repos?type=all", token)
    names = sorted(r["name"] for r in repos if r["name"].startswith(args.prefix + "-"))
    if not names:
        die(f"no repos in {org} start with '{args.prefix}-'")

    auth = [] if args.ssh else git_auth_args(token)
    failed = []
    for name in names:
        target = dest / name
        if target.exists():
            heads = subprocess.run(["git"] + auth + ["-C", str(target), "ls-remote", "--heads", "origin"],
                                   capture_output=True, text=True)
            if heads.returncode == 0 and not heads.stdout.strip():
                print(f"empty {name} (student has not pushed yet)")
                continue
            cmd = ["git"] + auth + ["-C", str(target), "pull", "--ff-only", "-q"]
            verb = "pull "
        else:
            url = f"git@github.com:{org}/{name}.git" if args.ssh else f"https://github.com/{org}/{name}.git"
            cmd = ["git"] + auth + ["clone", "-q", url, str(target)]
            verb = "clone"
        print(f"{verb} {name}")
        if subprocess.run(cmd).returncode != 0:
            failed.append(name)

    print(f"\n{len(names) - len(failed)}/{len(names)} repos up to date in {dest}/")
    if failed:
        die("failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
