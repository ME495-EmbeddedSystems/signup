#!/usr/bin/env python3
"""Create or manage an assignment and print its shareable link.

    python tools/new_assignment.py F26_HW1 --org myorg [--template tpl-repo] [--max-repos 200]
    python tools/new_assignment.py F26_HW1 --org myorg --close | --reopen | --rotate
"""
import argparse
import base64
import json

from classroom_lib import NAME_RE, derive_secret, die, gh, load_config, make_link, resolve_org


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="assignment name, e.g. F26_HW1")
    ap.add_argument("--org")
    ap.add_argument("--prefix", help="repo name prefix (default: the assignment name)")
    ap.add_argument("--template", help="template repo copied for each student (repo or owner/repo)")
    ap.add_argument("--max-repos", type=int)
    ap.add_argument("--close", action="store_true", help="stop accepting new students")
    ap.add_argument("--reopen", action="store_true")
    ap.add_argument("--rotate", action="store_true", help="invalidate the old link and issue a new one")
    args = ap.parse_args()

    if not NAME_RE.match(args.name) or (args.prefix and not NAME_RE.match(args.prefix)):
        die("names may only contain letters, digits, '_' and '-'")
    org = resolve_org(args.org)
    cfg = load_config(org)
    if "master_key" not in cfg:
        die(f"no master key for {org}; run: python tools/deploy.py {org}")
    repo = cfg.get("repo", "signup")

    path = f"repos/{org}/{repo}/contents/assignments.json"
    f = json.loads(gh("api", path))
    data = json.loads(base64.b64decode(f["content"]))

    entry = data.get(args.name)
    if entry is None:
        if args.close or args.reopen or args.rotate:
            die(f"no assignment named {args.name}")
        entry = {"prefix": args.name, "nonce": "1", "template": None, "open": True, "max_repos": 200}
        verb = "Created"
    else:
        verb = "Updated"
    if args.prefix:
        entry["prefix"] = args.prefix
    if args.template:
        entry["template"] = args.template
    if args.max_repos:
        entry["max_repos"] = args.max_repos
    if args.close:
        entry["open"] = False
    if args.reopen:
        entry["open"] = True
    if args.rotate:
        entry["nonce"] = str(int(entry["nonce"]) + 1)
    data[args.name] = entry

    gh("api", "-X", "PUT", path, "--input", "-", input=json.dumps({
        "message": f"{verb} assignment {args.name}",
        "content": base64.b64encode((json.dumps(data, indent=2) + "\n").encode()).decode(),
        "sha": f["sha"],
    }))

    print(f"{verb} {args.name}: {json.dumps(entry)}")
    if entry["open"]:
        print("\nShareable link:")
        print(make_link(org, repo, args.name, derive_secret(cfg["master_key"], args.name, entry["nonce"])))
    else:
        print("Assignment is closed; new submissions are refused.")


if __name__ == "__main__":
    main()
