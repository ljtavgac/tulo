# Tulo

Tulo is a content website, starting with a food/recipes vertical. This is a monorepo with two independent apps:

```
/frontend   Next.js (App Router, TypeScript) — renders pages, e.g. /food
/backend    FastAPI (Python) — serves recipe/content data as a REST API
```

## How the two talk to each other

The frontend and backend are two separate apps that get deployed separately (e.g. the frontend on Vercel, the backend on Render/Fly/Railway/etc.). They are **not** bundled together.

- The **backend** exposes a REST API (currently just `GET /health`, which returns `{"status": "ok"}`).
- The **frontend** fetches from that API over HTTPS. The backend's URL is configured via an environment variable (`API_URL`) so the frontend can be pointed at a different backend URL in each environment (local, staging, production) without code changes.
- The backend allows cross-origin requests from the frontend's URL via an environment variable (`FRONTEND_ORIGIN`).

See `frontend/app/food/page.tsx` for the example that fetches the backend's health check and displays it, and `backend/app/main.py` for the health check endpoint itself.

## Running locally

1. Start the backend (see `backend/README.md`) — it runs at `http://localhost:8000`.
2. Start the frontend (see `frontend/README.md`) — it runs at `http://localhost:3000`.
3. Visit `http://localhost:3000/food`. If both are running, you should see `Backend says: {"status":"ok"}`.

## What you'll need to configure when you deploy

Neither app has secrets in it yet, but both read a couple of environment variables that you'll need to set in whatever hosting platform you use:

| App      | Variable          | Set it to                                                      |
| -------- | ----------------- | ---------------------------------------------------------------- |
| backend  | `FRONTEND_ORIGIN` | Your deployed frontend's URL, e.g. `https://tulo.com`             |
| frontend | `API_URL`         | Your deployed backend's HTTPS URL, e.g. `https://api.tulo.com`    |

Each app also has a `.env.example` (backend) / `.env.local.example` (frontend) file showing the local defaults — copy those to `.env` / `.env.local` for local development.

## Deploying

**Frontend (Vercel):** already connected — Vercel builds `/frontend` on every push (see `frontend/vercel.json`).

**Backend (Render):** this repo includes a `render.yaml` at the root so Render can auto-detect the service. To deploy it:

1. Go to [render.com](https://render.com) and sign in with your GitHub account.
2. Click **New +** → **Blueprint**, and select the `ljtavgac/tulo` repo. Render will read `render.yaml` and configure the `tulo-backend` web service automatically.
3. When prompted, set the `FRONTEND_ORIGIN` environment variable to your Vercel URL (e.g. `https://tulo.vercel.app`).
4. Once deployed, copy the backend's URL (e.g. `https://tulo-backend.onrender.com`) and set it as the `API_URL` environment variable in your Vercel project (Settings → Environment Variables), then redeploy the frontend.
5. Visit your live `/food` page — it should now show `Backend says: {"status":"ok"}`.

Note: Render's free plan spins the service down after inactivity, so the first request after a while may take ~30–60 seconds to respond.
