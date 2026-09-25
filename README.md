# Serverless GitHub Classroom

Students open a link, enter their GitHub username, and get a private repo `<assignment>-<username>` in your org. It runs entirely on GitHub Pages and Actions, through a GitHub App installed only on the orgs you choose.

## Requirements

- Linux with `bash`, `git` and `openssl`
- The [`gh` CLI](https://cli.github.com), logged in (`gh auth login`) as an owner of the org
- An SSH key added to your GitHub account (used by `./classroom clone`)

## Set up an org (once per org)

### 1. Create the GitHub App

Go to `https://github.com/organizations/<org>/settings/apps/new` (org **Settings > Developer settings > GitHub Apps > New GitHub App**) and fill in:

| Field | Value |
|---|---|
| GitHub App name | Any unused name, e.g. `<org>-classroom` |
| Homepage URL | `https://<org>.github.io/signup/` (required, but not used) |
| Callback URL, Setup URL | Leave blank |
| Request user authorization, Enable Device Flow, Expire user authorization tokens | Leave unchecked |
| Webhook > Active | Uncheck |
| Repository permissions | **Administration: Read and write**. Metadata stays Read-only. Nothing else. |
| Organization and account permissions | None |
| Subscribe to events | None |
| Where can this GitHub App be installed? | **Only on this account** |

Click **Create GitHub App**, then on the App's page:

1. Note the **App ID** near the top.
2. Click **Generate a private key**. This downloads a `.pem` file. Keep it outside this directory.
3. Click **Install App** in the left sidebar, choose your org, and select **All repositories**.

### 2. Run the setup script

From this directory:

```
./setup <org> <app-id> <path-to-private-key.pem>
```

It creates the public `<org>/signup` repo from this directory, turns on GitHub Pages, stores the three Actions secrets (`APP_ID`, `APP_PRIVATE_KEY`, `MASTER_KEY`), and saves the org's master key in `~/.config/gh_classroom/<org>.key`. Then delete the `.pem` file.

**Keep `~/.config/gh_classroom/<org>.key`.** It is the only copy of the master key (GitHub never shows a secret again), and `./classroom link` needs it.

If setup stops because Pages creation is disabled, allow it under org **Settings > Member privileges > Pages creation (Public)** and run `./setup` again.

### 3. Test it

Make a short-lived link, open it, sign up as yourself, then delete the test repo:

```
./classroom link <org> SETUPTEST 1
```

## Use

```
./classroom link  <org> <assignment> [days]   # print the student link (valid 30 days by default)
./classroom clone <org> <assignment> [dir]    # clone every <assignment>-* repo not yet cloned
```

Nothing is stored per assignment: a link is derived from the org's master key, the assignment name and the expiry date. Run `link` again whenever you need a fresh one.

## Update an existing org

Commit your changes here, then `git push <org> main`.

## Harden the org

- Anyone with **write access to `signup`** can read its Actions secrets, including the App key, which can administer every repo in the org. Keep write access to yourself, and add a ruleset on `main` that blocks force-pushes and deletion.
- Do not create org-level Actions secrets visible to all repos: students can run workflows in their own repos.
- Restrict Actions (org **Settings > Actions**) to the `signup` repo, and leave "Allow forking of private repositories" off.
- Set the org's base permissions to "No permission".
- To keep `gh` from reaching your other orgs, set `GH_TOKEN` to a fine-grained PAT owned by this org (Administration, Contents, Pages, Secrets: read & write) instead of using `gh auth login`.

## Notes

- Anyone with the link can join until it expires. There is no early revoke; to cancel every link, replace both the `MASTER_KEY` secret and `~/.config/gh_classroom/<org>.key` with a new key.
- Students must accept a collaborator invite; the workflow's comment links to it.
- A student's repo is never reused. To redo one, delete the repo and have the student open the link again.
- Keep assignment names short: a repo name (`<assignment>-<username>`) can be at most 100 characters.
- `signup` is public so students can open issues, which also makes its git history and commit author emails public. Commit with a `users.noreply.github.com` address if you don't want yours shown.
