#!/usr/bin/env python3
"""Clone (or pull) every student repo for an assignment.

    python tools/clone.py F26_HW1 [dest] [--org myorg]

Repos are the org's repos named "<prefix>-<username>".
"""
import argparse
import subprocess
from pathlib import Path

from classroom_lib import GIT_GH_AUTH, die, gh, resolve_org


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prefix", help="assignment prefix, e.g. F26_HW1")
    ap.add_argument("dest", nargs="?", help="destination directory (default: ./<prefix>)")
    ap.add_argument("--org")
    args = ap.parse_intermixed_args()

    org = resolve_org(args.org)
    dest = Path(args.dest or args.prefix)
    dest.mkdir(parents=True, exist_ok=True)

    listing = gh("repo", "list", org, "--limit", "1000", "--json", "name", "--jq", ".[].name")
    names = sorted(n for n in listing.split() if n.startswith(args.prefix + "-"))
    if not names:
        die(f"no repos in {org} start with '{args.prefix}-'")

    failed = []
    for name in names:
        target = dest / name
        if target.exists():
            heads = subprocess.run(["git", *GIT_GH_AUTH, "-C", str(target), "ls-remote", "--heads", "origin"],
                                   capture_output=True, text=True)
            if heads.returncode == 0 and not heads.stdout.strip():
                print(f"empty {name} (student has not pushed yet)")
                continue
            print(f"pull  {name}")
            cmd = ["git", *GIT_GH_AUTH, "-C", str(target), "pull", "--ff-only", "-q"]
        else:
            print(f"clone {name}")
            cmd = ["gh", "repo", "clone", f"{org}/{name}", str(target), "--", "-q"]
        if subprocess.run(cmd).returncode != 0:
            failed.append(name)

    print(f"\n{len(names) - len(failed)}/{len(names)} repos up to date in {dest}/")
    if failed:
        die("failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
