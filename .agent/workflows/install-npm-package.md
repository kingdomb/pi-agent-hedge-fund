---
description: How to install new npm packages into Docker-hosted services (backend, frontend). Prevents the anonymous volume caching bug.
---

# Installing New NPM Packages in Docker Services

> **Root Cause:** The `docker-compose.dev.yml` uses anonymous volumes (e.g. `- /app/node_modules`) to
> persist `node_modules` across container restarts for performance. However, this means that when you
> `docker compose build`, the NEW image has the updated `node_modules`, but the OLD anonymous volume
> is mounted over it — hiding the newly installed package.

## Steps

// turbo-all

### 1. Install the package locally (so `package.json` and `package-lock.json` are updated)
```bash
cd backend   # or cd frontend
npm install --legacy-peer-deps <package-name>
```

### 2. Rebuild the Docker image (this bakes the new packages into the image layer)
```bash
docker compose -f docker-compose.dev.yml build <service-name>
```
Where `<service-name>` is `backend` or `ai-os-ui`.

### 3. Recreate the container WITH `-V` flag to renew anonymous volumes
```bash
docker compose -f docker-compose.dev.yml up -d <service-name> -V
```

> ⚠️ **CRITICAL:** The `-V` (`--renew-anon-volumes`) flag is what destroys the stale anonymous volume
> and creates a fresh one from the rebuilt image. Without this flag, the old `node_modules` volume
> persists and the new package will NOT be found at runtime.

### 4. Verify the package is available
```bash
docker exec <container-name> ls node_modules/<package-name>
```

## Common Mistakes
- **Just running `docker compose build && up -d`** — This WILL NOT work because the anonymous volume persists.
- **Installing only inside the container** — The package will be lost on the next rebuild.
- **Forgetting `--legacy-peer-deps`** — Required due to the Express 5 vs 4 peer dependency conflict.

## Service Reference
| Service Name | Container Name | Directory |
|-------------|---------------|-----------|
| `backend` | `ai_corp_backend` | `./backend` |
| `ai-os-ui` | `ai_os_ui` | `./frontend` |
