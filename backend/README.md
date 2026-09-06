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

## Configuration

| Variable         | Purpose                                                              | Local default             |
| ---------------- | --------------------------------------------------------------------- | -------------------------- |
| `FRONTEND_ORIGIN` | The deployed frontend's URL, used to allow it to call this API (CORS) | `http://localhost:3000`    |

When you deploy, set `FRONTEND_ORIGIN` to your real frontend URL (e.g. `https://tulo.com`).
