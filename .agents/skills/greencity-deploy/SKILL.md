---
name: greencity-deploy
description: Deploy the GreenCity web app and API from GitHub to the Raspberry Pi. Use whenever the user says deploy, release, ship, "pull and deploy", "make it live", "update the Pi", "is it deployed", or asks about the GreenCity production/deployment state — even if they don't use the word deploy.
---

# GreenCity deploy

The release process is: changes are pushed to `origin/app`, then run `deploy/deploy.sh`.
The script pulls that branch, rsyncs it to `/home/parsa/greencity-src` on the Pi, rebuilds
both containers there, and health-checks the public URL. GitHub is the source of truth.

## Before deploying

Run from the repo root and check the tree is clean:

```bash
git branch --show-current
git status --short
```

If anything is dirty, stop: commit and push first. The script deploys the working tree,
so uncommitted edits would ship silently. Show what is about to ship:

```bash
git fetch origin app
git log --oneline HEAD..origin/app
git rev-parse --short origin/app
```

If `HEAD` is ahead of `origin/app`, push first — the Pi pulls from GitHub, not from the Mac.

## Deploy

```bash
./deploy/deploy.sh
```

For another branch: `BRANCH=main ./deploy/deploy.sh`.

Success ends with `==> live: https://greencity.parsalotfi.com (<sha>)`. Do not report
success before that line. A failed check or build aborts before the containers are
replaced, so the previous release keeps serving.

## Verify

```bash
curl -fsS https://greencity.parsalotfi.com/healthz
curl -fsS https://greencity.parsalotfi.com/clusters
ssh raspberrypi.parsalotfi.com 'docker compose -p greencity ps'
ssh raspberrypi.parsalotfi.com 'cat /home/parsa/greencity-src/.deployed'
```

Report the deployed SHA and whether both containers are healthy.

## What runs on the Pi

- `greencity` — nginx on host port 8081, public via the Cloudflare tunnel. Serves the
  static SvelteKit build and proxies `/reports`, `/clusters`, `/sensors`, `/bikes` to the API.
- `greencity-api` — FastAPI/uvicorn on internal port 8000. SQLite lives in the
  `greencity_greencity-data` volume at `/data/reports.db`; `history.json` is beside it.
- The host has no Node or Python for this app; both exist only inside the images.
- Leave `my-open-webui` alone. MariaDB was removed; GreenCity uses SQLite.

## If it fails

- **Build or type check fails**: the script exits before `compose up`, old containers keep
  serving. Read the `npm run check` / `npm run build` / `uv sync` output, fix, commit, push, rerun.
- **Health check fails**: `ssh raspberrypi.parsalotfi.com 'cd /home/parsa/greencity-src && docker compose -p greencity logs --tail=100'`.
  If the API is unhealthy, check `api` logs specifically.
- **Public URL down, containers healthy**: check `systemctl is-active cloudflared` and that
  port 8081 is listening. The tunnel route is `greencity.parsalotfi.com → http://localhost:8081`.
- **SSH**: use `raspberrypi.parsalotfi.com` (Cloudflare tunnel). `raspberrypi5.local` does not
  resolve on this network.
- Never run `docker compose down -v` on this stack: `-v` would delete the SQLite volume.
  Data survives normal deploys because `up -d` only recreates containers.
