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

| Variable   | Purpose                                              | Local default           |
| ---------- | ----------------------------------------------------- | ------------------------ |
| `API_URL`  | Base URL of the backend API that pages fetch from      | `http://localhost:8000`  |

When you deploy, set `API_URL` to your deployed backend's HTTPS URL (e.g. `https://api.tulo.com`).
