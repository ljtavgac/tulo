# Tulo backend

A FastAPI app that serves recipe/content data as a REST API.

## Local development

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The API will be running at http://localhost:8000. Try http://localhost:8000/health.

On startup, the app creates its database tables if they don't exist and auto-seeds a small set of example content pages (one per page template) if the `pages` table is empty -- no manual setup step needed.

## API

| Endpoint | Purpose |
| -------- | ------- |
| `GET /health` | Health check, returns `{"status": "ok"}` |
| `GET /pages/{slug}` | Full content for one page |
| `GET /pages?template_type=recipe_or_dish` | List pages, optionally filtered by template type |

## Configuration

| Variable             | Purpose                                                              | Local default             |
| --------------------- | --------------------------------------------------------------------- | -------------------------- |
| `FRONTEND_ORIGIN`     | The deployed frontend's URL, used to allow it to call this API (CORS) | `http://localhost:3000`    |
| `DATABASE_URL`        | Database connection string                                            | `sqlite:///./tulo.db`      |
| `UNSPLASH_ACCESS_KEY` | Optional. Enables real stock photos -- see below.                     | unset                      |
| `PEXELS_ACCESS_KEY`   | Optional. Enables real stock photos -- see below.                     | unset                      |
| `ADMIN_TASK_TOKEN`    | Optional. Enables the `/admin/fetch-images` endpoint -- see below.    | unset                      |

When you deploy, set `FRONTEND_ORIGIN` to your real frontend URL (e.g. `https://tulo.com`).

`DATABASE_URL` defaults to a local SQLite file, which is fine for local development but not for production: Render's free-tier disk is ephemeral (it resets on every deploy), so published content -- and fetched stock photos -- won't survive a redeploy until this points at a persistent database instead.

### Setting up a persistent database on Render

1. In the Render dashboard: **New +** → **PostgreSQL**. Pick the same region as the `tulo-backend` web service. Note that Render's free Postgres plan is deleted automatically after a set number of days -- check the current terms when you create it, and use a paid Starter instance instead if you want it to stay up indefinitely.
2. Once it's created, copy its **Internal Database URL** (starts with `postgres://`) -- internal, not external, since the web service and database run in the same region and don't need to go over the public internet.
3. On the `tulo-backend` service's Environment tab, add `DATABASE_URL` with that value, then save (triggers a redeploy).

The app normalizes Render's `postgres://` scheme to the `postgresql://` SQLAlchemy expects, and `psycopg2-binary` is already a dependency -- no other code changes needed. On first boot against the new database it creates the tables and seeds the template-review pages, same as it does locally; every deploy after that leaves existing data alone (`seed()` only inserts pages that don't already exist), so anything fetched via `/admin/fetch-images` now sticks around.

## Stock photos

Pages show a placeholder image slot until real photos are sourced. To turn that on:

1. Get free API keys: https://unsplash.com/developers and/or https://www.pexels.com/api/
2. Set `UNSPLASH_ACCESS_KEY` and/or `PEXELS_ACCESS_KEY` (both, if you want Pexels as a fallback when Unsplash has no result)
3. Redeploy (or restart the app locally)

Once a key is set, fetching is automatic: app startup calls the same `fetch_images()` function described below for any page still missing a photo. It searches each page's image query, picks the top result, and writes the image URL and photographer attribution into that page's content, so it's fetched once and stays stable rather than being re-fetched on every page load. A page that already has an image is skipped with a plain dict check -- no API call -- so a redeploy with no new content does effectively nothing here, and only genuinely new pages (the next content batch, say) trigger a real search. With no key set, this is a complete no-op, not even a page loop. Recipe, Ingredient Hub, How-To, Definition, Comparison, and Substitute pages get a single hero image; Category Roundup pages get one image per recipe card. Homepage and Tool pages don't use photos in their design.

### Triggering it manually

Startup handles new content automatically, but you can also force a re-fetch (e.g. to pick up better search results, or after changing an image query) without waiting for a deploy:

```bash
python -m app.fetch_stock_images        # skip pages that already have an image
python -m app.fetch_stock_images --force  # re-fetch every page, including ones that already have an image
```

### Running it without shell access

The command above assumes you can open a shell on the host. Render's free tier doesn't offer one, so as an alternative, set `ADMIN_TASK_TOKEN` to any random secret string and visit:

```
https://YOUR-BACKEND-URL/admin/fetch-images?token=YOUR_ADMIN_TASK_TOKEN
```

in a browser (add `&force=true` to re-fetch pages that already have an image). It runs the same `fetch_images()` function as startup and the script, and returns a JSON summary plus the per-page log. Without `ADMIN_TASK_TOKEN` set, this endpoint always 404s -- it doesn't exist until you opt in. Treat the token like a password: anyone with it can trigger the (rate-limited, harmless-but-not-free-forever) image search, and a token in a URL can end up in server/proxy logs, so don't share the URL and rotate `ADMIN_TASK_TOKEN` if you ever suspect it leaked.
