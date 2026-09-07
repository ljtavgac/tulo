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

When you deploy, set `FRONTEND_ORIGIN` to your real frontend URL (e.g. `https://tulo.com`).

`DATABASE_URL` defaults to a local SQLite file, which is fine for local development and for this early template-review stage. Render's free-tier disk is ephemeral (it resets on every deploy), so before real batch content goes live, `DATABASE_URL` should point at a persistent database instead (e.g. a Render Postgres instance) -- otherwise published content won't survive a redeploy. The same caveat applies to stock photos below: fetching them against the current SQLite setup on Render is pointless until that's fixed, since the next deploy would wipe them.

## Stock photos

Pages show a placeholder image slot until real photos are sourced. To turn that on:

1. Get free API keys: https://unsplash.com/developers and/or https://www.pexels.com/api/
2. Set `UNSPLASH_ACCESS_KEY` and/or `PEXELS_ACCESS_KEY` (both, if you want Pexels as a fallback when Unsplash has no result)
3. Run `python -m app.fetch_stock_images` (add `--force` to re-fetch pages that already have an image)

This is a one-time/occasional maintenance script, not something that runs automatically -- it searches each page's image query, picks the top result, and writes the image URL and photographer attribution into that page's content so it's fetched once and stays stable rather than being re-fetched on every page load. Only Recipe, Ingredient Hub, How-To, and Definition pages (single hero image) and Category Roundup pages (one image per recipe card) have an image slot -- Comparison, Substitute, Homepage, and Tool pages don't use photos in their design.
