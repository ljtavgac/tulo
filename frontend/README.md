# Tulo frontend

A Next.js (App Router, TypeScript) app that renders Tulo's pages, starting with routes under `/food`.

## Local development

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

The app will be running at http://localhost:3000. Visit http://localhost:3000/food to see it call the backend's `/health` endpoint.

The backend must also be running (see `../backend/README.md`) for the `/food` page to connect successfully.

## Configuration

| Variable            | Purpose                                                          | Local default           |
| ------------------- | ------------------------------------------------------------------ | ------------------------ |
| `API_URL`           | Base URL of the backend API that pages fetch from                  | `http://localhost:8000`  |
| `REVALIDATION_TOKEN`| Optional. Enables the `/api/revalidate` endpoint -- see below.     | unset                     |

When you deploy, set `API_URL` to your deployed backend's HTTPS URL (e.g. `https://api.tulo.com`).

## Cache revalidation

Every page is cached for an hour (`lib/api.ts`'s `REVALIDATE_SECONDS`), which is fine for content that only changes via a scheduled batch, but there's otherwise no way to make a page pick up a backend change sooner -- e.g. right after backfilling stock photos, or fixing a content bug.

Set `REVALIDATION_TOKEN` to any random secret string, then visit:

```
https://your-frontend-url/api/revalidate?token=YOUR_REVALIDATION_TOKEN
```

to force every cached page to refetch on its next visit. Without `REVALIDATION_TOKEN` set, this endpoint always 404s -- it doesn't exist until you opt in. Treat the token like a password, same as the backend's `ADMIN_TASK_TOKEN`.

Note: a Vercel redeploy alone does **not** reliably clear this cache -- Vercel's fetch-level Data Cache is persisted across deployments by design, keyed per URL, independent of the page/build cache. This endpoint is the actual way to force a refresh.
