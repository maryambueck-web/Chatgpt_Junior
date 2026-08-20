# Production Deployment

The [Streamlit Community Cloud](https://share.streamlit.io) instructions in the README are the fastest way to get a shareable link, but its filesystem is ephemeral — every redeploy (and sometimes every restart after inactivity) wipes `src/data/`, so the Guardian Command Center's safety log and the child's age-band setting would silently reset. That's fine for a five-minute demo. It is not fine for a parent who actually relies on this.

This doc covers deploying so the app survives restarts: a host with a **persistent disk**, running the included `Dockerfile`.

## What changed to make this possible

- `shared_store.py` now stores settings and the safety log in SQLite instead of raw JSON files. SQLite handles concurrent writes safely (two people using the app at once no longer risk silently losing a log entry) and works correctly when its file lives on a mounted volume.
- The database path is configurable via `SAFECHATGPT_DB_PATH`. Point it at your mounted volume (e.g. `/data/safechatgpt.db`) and the log/settings survive restarts and redeploys. Leave it unset for local dev — it defaults to `src/data/safechatgpt.db`.
- If `src/data/settings.json` / `safety_log.json` already exist (from an earlier JSON-based run), they're imported into the database automatically the first time it starts — no history is lost switching over.

## Test it locally first

`docker-compose.yml` runs the exact same image with a mounted volume standing in for a platform's persistent disk, and `verify.sh` drives it end to end — builds it, waits for it to become healthy, exercises storage/ChatGPT/image search inside the running container, and restarts it to prove data actually survives:

```bash
./verify.sh          # build, run, verify, leave it running at http://localhost:8501
./verify.sh --down   # same, then tear the container down afterward
```

This needs Docker installed and running locally. Fix anything it flags before deploying anywhere.

## Deploying to Render

`render.yaml` in the repo root is a [Render Blueprint](https://render.com/docs/blueprint-spec) — push the repo, then **New +** → **Blueprint** and pick this repo; Render reads the file and provisions the service and disk for you.

**This needs a paid instance type.** Render's persistent disks require the Starter plan or above — the free web service tier does not support attached disks, so on Free your data would NOT survive a redeploy despite this config. `render.yaml` already sets `plan: starter`.

After the first deploy, set the secret env vars marked `sync: false` in the file (`OPENAI_API_KEY`, `PARENT_PIN`, `UNSPLASH_ACCESS_KEY`) in the Render dashboard — they're deliberately not synced from the repo.

To do it by hand instead: **New +** → **Web Service** → connect the repo (Render detects the `Dockerfile`) → under **Disks** add one at mount path `/data`, 1 GB → under **Environment** add the vars from [Configuration](../README.md#configuration) plus `SAFECHATGPT_DB_PATH=/data/safechatgpt.db`.

## Deploying to Fly.io or Railway instead

`fly.toml` and `railway.json` are in the repo root, same idea as Render — mount a volume, point `SAFECHATGPT_DB_PATH` at a file inside it:

- **Fly.io**: one-time setup — `fly launch --no-deploy`, `fly volumes create safechatgpt_data --size 1`, `fly secrets set OPENAI_API_KEY=... PARENT_PIN=... UNSPLASH_ACCESS_KEY=...` — then `fly deploy`. `fly.toml` already wires up the mount and health check.
- **Railway**: deploy from the repo (Railway detects the `Dockerfile` via `railway.json`), then in the service's Settings add a Volume mounted at `/data`, and under Variables set `SAFECHATGPT_DB_PATH=/data/safechatgpt.db` plus your secrets — Railway's config format has no first-class volume support, so this part has to be done in the dashboard.

## Before calling it "production"

- [ ] `PARENT_PIN` changed from the default (the app now warns in the dashboard if you haven't).
- [ ] `OPENAI_API_KEY` (and `OPENAI_BASE_URL`/`OPENAI_MODEL` if using a non-OpenAI provider) set — otherwise the app silently runs in mock mode.
- [ ] `UNSPLASH_ACCESS_KEY` set if you want real, content-matched image search rather than the picsum.photos fallback.
- [ ] Restart the service once after your first real session and confirm the Guardian Command Center still shows the earlier log entries — that's the actual test that persistence is working, not just configured.
- [ ] Read the [Limitations section in the README](../README.md#limitations) — this is still a proof of concept, not a fully hardened product.

## What this does *not* solve

- **Not multi-tenant.** One deployment is for one family. Two unrelated families sharing a URL would share the same PIN, the same age-band setting, and see each other's safety log. If you need that, it's a different (much larger) project — real accounts and per-family data isolation.
- **PIN lockout is global, not per-IP.** After 5 wrong PINs the dashboard locks for 5 minutes for everyone, which is enough to stop casual guessing but isn't a substitute for a real authentication system.
- **The per-session rate limit (15 messages/minute) is per browser session, not global.** It stops one runaway session from burning through your API budget; it won't stop coordinated abuse from many sessions at once.
