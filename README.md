# GitHub Classroom, minus the server

Students open a link, enter their GitHub username, and get a private repo `<assignment>-<username>` in your org. Runs on GitHub Pages and Actions through a GitHub App installed only on the orgs you choose.

Publish this repo to any org and it works unedited. Requires `bash`, `git`, `openssl` and the [`gh` CLI](https://cli.github.com), logged in (`gh auth login`) as an owner of the org.

## Set up an org

1. Create a GitHub App at `https://github.com/organizations/myorg/settings/apps/new` (org Settings > Developer settings > GitHub Apps > New GitHub App):
   - **Name**: any globally unique name, e.g. `myorg-classroom`
   - **Homepage URL**: `https://myorg.github.io/signup/` (required, not used)
   - **Callback URL**, **Setup URL**: blank. Leave "Request user authorization", "Enable Device Flow" and "Expire user authorization tokens" unchecked.
   - **Webhook**: uncheck "Active"
   - **Repository permissions**: Administration: Read and write; Metadata: Read-only. No other permissions.
   - **Subscribe to events**: none
   - **Where can this GitHub App be installed?**: Only on this account

   Click **Create GitHub App**. On the next page, note the **App ID** and click **Generate a private key** (saves a `.pem`; keep it outside this directory, e.g. `~/Downloads/app.pem`). Then **Install App** (left sidebar) > install on `myorg` > **All repositories**.
2. From this directory:
   ```
   ORG=myorg; REPO=signup; APP_ID=12345; PEM=~/Downloads/app.pem

   gh repo create $ORG/$REPO --public --source . --remote $ORG --push
   gh api -X POST repos/$ORG/$REPO/pages -f 'source[branch]=main' -f 'source[path]=/'

   KEY=$(openssl rand -hex 32)
   printf %s "$KEY"    | gh secret set MASTER_KEY --repo $ORG/$REPO
   printf %s "$APP_ID" | gh secret set APP_ID     --repo $ORG/$REPO
   gh secret set APP_PRIVATE_KEY --repo $ORG/$REPO < $PEM

   (umask 077; mkdir -p ~/.config/gh_classroom; printf %s "$KEY" > ~/.config/gh_classroom/$(echo $ORG | tr A-Z a-z).key)
   shred -u $PEM    # the App key now lives only in the Actions secret
   ```
   GitHub never shows a secret again, so keep `~/.config/gh_classroom/<org>.key` (the `MASTER_KEY` value): `./classroom link` needs it.
   Any repo name works, except `$ORG.github.io`; if it isn't `signup`, run the commands below with `REPO=<name>`.
   If enabling Pages fails with "Pages creation disabled", allow it under Org settings > Member privileges > Pages creation (Public), then re-run that command.

To update an existing deployment, run `git push $ORG main`.

To limit `gh` to one org, set `GH_TOKEN` to a fine-grained PAT owned by that org (Administration, Contents, Pages, Secrets: read & write) instead of using `gh auth login`.

## Use

```
./classroom link  myorg F26_HW1 [days]   # prints the student link; valid 30 days unless you pass days
./classroom clone myorg F26_HW1 [dir]    # clones or pulls every repo named F26_HW1-*
```

Nothing is stored for an assignment: the link is derived from the org's key (`~/.config/gh_classroom/<org>.key`), the assignment name and the expiry date. Run `link` again any time for a fresh one. If you use https for git, run `gh auth setup-git` once so `clone` can pull.

## Harden the org

- Anyone with **write access to the signup repo** can read its Actions secrets, including the App key, which can administer every repo in the org. Keep write access to yourself and protect `main`.
- Do not create org-level Actions secrets visible to all repos: students can run workflows in their own repos.
- Restrict Actions (Org settings > Actions) to the signup repo, and leave "Allow forking of private repositories" off.
- Set base permissions to "No permission".

## Notes

- Anyone with the link can join until it expires. There is no early revoke; to cancel every link, replace the `MASTER_KEY` secret and `~/.config/gh_classroom/<org>.key`. The workflow refuses to create more than 300 repos per assignment.
- Students accept a collaborator invite; the workflow comment links to it.
- A student's repo is never reused. To redo one, delete the repo and have them open the link again.
- The repo is public so students can open issues.
