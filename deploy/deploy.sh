#!/usr/bin/env bash
# Pull the deploy branch and ship it to the Raspberry Pi.
# Run from anywhere: deploy/deploy.sh
set -euo pipefail

BRANCH="${BRANCH:-app}"
HOST="${HOST:-raspberrypi.parsalotfi.com}"
REMOTE_DIR="${REMOTE_DIR:-/home/parsa/greencity-src}"
PUBLIC_URL="${PUBLIC_URL:-https://greencity.parsalotfi.com}"

cd "$(dirname "$0")/.."

echo "==> pulling $BRANCH"
git fetch --quiet origin "$BRANCH"
git switch --quiet "$BRANCH"
git pull --quiet --ff-only origin "$BRANCH"
COMMIT="$(git rev-parse --short HEAD)"
echo "==> deploying $COMMIT"

ssh "$HOST" "mkdir -p '$REMOTE_DIR'"
rsync -az --delete \
	--exclude .git \
	--exclude .deployed \
	--exclude node_modules \
	--exclude build \
	--exclude .svelte-kit \
	--exclude e2e/out \
	-e ssh \
	./ "$HOST:$REMOTE_DIR/"

echo "==> building and starting containers"
ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -p greencity up -d --build --remove-orphans"

echo "==> waiting for $PUBLIC_URL"
for _ in $(seq 1 30); do
	if curl -fsS --max-time 5 "$PUBLIC_URL/healthz" >/dev/null 2>&1; then
		break
	fi
	sleep 2
done
curl -fsS --max-time 10 "$PUBLIC_URL/healthz" >/dev/null
curl -fsS --max-time 10 "$PUBLIC_URL/clusters" >/dev/null

printf '%s %s\n' "$COMMIT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | ssh "$HOST" "cat > '$REMOTE_DIR/.deployed'"
echo "==> live: $PUBLIC_URL ($COMMIT)"
