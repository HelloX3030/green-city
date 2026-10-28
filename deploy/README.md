# Deploy

`deploy.sh` is the manual deploy path. It pulls the `app` branch, rsyncs the tree to
the Pi, rebuilds the two containers there, and waits until the public URL answers.

```bash
deploy/deploy.sh
# or another branch:
BRANCH=main deploy/deploy.sh
```

On the Pi the stack lives in `/home/parsa/greencity-src` and is managed by
`docker compose -p greencity`:

- `greencity` – nginx serving the static SvelteKit build, proxying the API paths
- `greencity-api` – FastAPI, data in the `greencity_greencity-data` volume
- host port `8081`, exposed by the existing Cloudflare tunnel as `greencity.parsalotfi.com`

Node and Python exist only inside the images. The Pi needs Docker only.

The last deployed commit is written to `/home/parsa/greencity-src/.deployed`.
