# GitHub Classroom, minus the server

Students open a link, enter their GitHub username, and get a private repo `<assignment>-<username>` in your org. Runs on GitHub Pages and Actions through a GitHub App installed only on the orgs you choose.

Publish this repo to any org, under any name, and it works unedited.

Requires Python 3, `git`, and the [`gh` CLI](https://cli.github.com) logged in (`gh auth login`) as an owner of the org.

## Set up an org

1. Create a GitHub App at `https://github.com/organizations/myorg/settings/apps/new` (org Settings > Developer settings > GitHub Apps > New GitHub App):
   - **Name**: any globally unique name, e.g. `myorg-classroom`
   - **Homepage URL**: `https://myorg.github.io/signup/` (required, not used; match your repo name)
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
   printf %s "$KEY"    | gh secret set MASTER_KEY      --repo $ORG/$REPO
   printf %s "$APP_ID" | gh secret set APP_ID          --repo $ORG/$REPO
   gh secret set APP_PRIVATE_KEY --repo $ORG/$REPO < $PEM

   mkdir -p ~/.classroom && printf '{"master_key":"%s","repo":"%s"}\n' $KEY $REPO > ~/.classroom/$ORG.json
   chmod 600 ~/.classroom/$ORG.json
   shred -u $PEM    # the key now lives only in the Actions secret
   ```
   Any repo name works, except `$ORG.github.io`.

`python tools/deploy.py myorg --app-id 12345 --private-key ~/Downloads/app.pem` does all of step 2.

To update an existing deployment, just push. `new_assignment.py` commits `assignments.json` to the org repo, so pull first:
```
git pull --rebase $ORG main && git push $ORG main
```

To limit `gh` to one org, set `GH_TOKEN` to a fine-grained PAT owned by that org (Administration, Contents, Pages, Secrets: read & write) instead of using `gh auth login`.

## Use

```
python tools/new_assignment.py F26_HW1 --org myorg            # prints the student link
python tools/new_assignment.py F26_HW1 --org myorg --close    # stop new sign-ups
python tools/new_assignment.py F26_HW1 --org myorg --rotate   # new link; old one stops working
python tools/clone.py F26_HW1 --org myorg [dest]              # clone or pull all student repos
```

`--org` may be omitted if only one org is configured, or set via `CLASSROOM_ORG`.

## Harden the org

- Anyone with **write access to the signup repo** can read its Actions secrets, including the App key, which can administer every repo in the org. Keep write access to yourself and protect `main`.
- Do not create org-level Actions secrets visible to all repos: students can run workflows in their own repos.
- Restrict Actions (Org settings > Actions) to the signup repo, and leave "Allow forking of private repositories" off.
- Set base permissions to "No permission".

## Notes

- Anyone with the link can join. `--close` or `--rotate` if it leaks. `max_repos` in `assignments.json` (default 200) caps repos.
- Students accept a collaborator invite; the workflow comment links to it.
- The repo is public so students can open issues.
