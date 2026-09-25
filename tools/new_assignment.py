#!/usr/bin/env python3
"""Print the shareable link for an assignment.

    python tools/new_assignment.py F26_HW1 --org myorg [--days 30]

The link works until the end of its expiry day (UTC). Nothing is stored anywhere: the link is
derived from the org's master key, the assignment name and the expiry date.
"""
import argparse
from datetime import datetime, timedelta, timezone

from classroom_lib import NAME_RE, derive_secret, die, load_config, make_link, resolve_org


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="assignment name, e.g. F26_HW1; student repos are named <name>-<username>")
    ap.add_argument("--org")
    ap.add_argument("--days", type=int, default=30, help="days until the link expires (default: 30)")
    args = ap.parse_args()

    if not NAME_RE.match(args.name):
        die("the name may only contain letters, digits, '_' and '-'")
    org = resolve_org(args.org)
    cfg = load_config(org)
    if "master_key" not in cfg:
        die(f"no master key for {org}; run: python tools/deploy.py {org}")

    expiry = (datetime.now(timezone.utc) + timedelta(days=args.days)).strftime("%Y%m%d")
    secret = derive_secret(cfg["master_key"], args.name, expiry)
    print(make_link(org, cfg.get("repo", "signup"), args.name, expiry, secret))
    print(f"Valid through {expiry[:4]}-{expiry[4:6]}-{expiry[6:]} (UTC)")


if __name__ == "__main__":
    main()
