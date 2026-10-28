# Self-hosted runner

GitHub's official Actions runner image, plus the Docker CLI and Compose plugin.
It registers itself on first start and is driven by `.github/workflows/deploy.yml`.

On the Pi:

```bash
mkdir -p ~/greencity-ci ~/greencity-runner
cd ~/greencity-runner
# copy compose.yml and Dockerfile here, then create .env:
printf 'RUNNER_TOKEN=%s\nDOCKER_GID=%s\n' "$TOKEN" "$(getent group docker | cut -d: -f3)" > .env
docker compose up -d --build
```

`RUNNER_TOKEN` is a repository registration token (`Settings → Actions → Runners →
New self-hosted runner`), valid for one hour and only needed for the first start.
The runner's config lives in the container, so normal restarts do not need a new
token. If the container is recreated, generate a new token and start it again;
`config.sh --replace` handles the old entry.

The job workspace is bind-mounted at the same absolute path on the host, because
`docker compose build` resolves build contexts on the host Docker daemon.
