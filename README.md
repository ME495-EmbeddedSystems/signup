# GitHub Classroom, minus the server

Students open a link, enter their GitHub username, and get a private repo `<assignment>-<username>` in your org. Runs on GitHub Pages and Actions through a GitHub App installed only on the orgs you choose.

Publish this repo to any org, under any name, and it works unedited.

## Set up an org

1. Create a fine-grained PAT: owner = the org, all repositories, read & write on Administration, Contents, Pages, Secrets.
2. Create a GitHub App owned by the org: webhook off, repository permissions Administration (R/W), Contents (R/W), Metadata (R), "Only on this account". Generate a private key. Install it on the org, all repositories.
3. Deploy:
   ```
   pip install pynacl
   python tools/deploy.py myorg --app-id 12345 --private-key app.pem
   ```
   This creates `myorg/signup` (`--repo NAME` to rename), pushes these files, enables Pages, and sets the Actions secrets. Re-run to update; assignments are kept. Without `--app-id`/`--private-key`, it prints the secrets to add by hand (`APP_ID`, `APP_PRIVATE_KEY`, `MASTER_KEY`).

The PAT and a per-org master key are stored in `~/.classroom/myorg.json`.

## Use

```
python tools/new_assignment.py F26_HW1 --org myorg            # prints the student link
python tools/new_assignment.py F26_HW1 --org myorg --template hw1-starter
python tools/new_assignment.py F26_HW1 --org myorg --close    # stop new sign-ups
python tools/new_assignment.py F26_HW1 --org myorg --rotate   # new link; old one stops working
python tools/clone.py F26_HW1 --org myorg [dest] [--ssh]      # clone or pull all student repos
```

`--org` may be omitted if only one org is configured, or set via `CLASSROOM_ORG`.

## Notes

- Anyone with the link can join. `--close` or `--rotate` if it leaks. `max_repos` in `assignments.json` (default 200) caps repos.
- Students accept a collaborator invite; the workflow comment links to it.
- The repo is public so students can open issues.
