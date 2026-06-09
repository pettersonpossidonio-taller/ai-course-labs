# Lab 01 - URL Shortener

Minimal URL shortener split into a FastAPI backend and a Next.js frontend.

## Project Structure

- `backend/` - FastAPI API, SQLite storage, backend tests, and deployment files for Railway
- `frontend/` - Next.js app and deployment configuration for Vercel

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e '.[dev]'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend environment variables:
- `SHORTENER_DB_PATH` - optional path to the SQLite database file. Defaults to `backend/shortener.db`.
- `FRONTEND_ORIGINS` - comma-separated list of allowed browser origins for local development and deployment. Defaults to `http://localhost:3000,http://127.0.0.1:3000`.

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Frontend environment variables:
- `NEXT_PUBLIC_API_BASE_URL` - backend API base URL used by the browser app. Defaults to `http://localhost:8000` when not set.

## Deployment

### Railway backend deployment

1. Create a new Railway project and connect this repository.
2. Set the service root directory to `lab01-url-shortener/backend`.
3. Use this Railway start command for the backend service:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

4. Add the backend environment variables in Railway:
   - `SHORTENER_DB_PATH=/data/shortener.db` or another writable path if you want to persist the SQLite file inside the service volume.
   - `FRONTEND_ORIGINS=<your Vercel domain>,http://localhost:3000,http://127.0.0.1:3000`
5. If you want SQLite persistence across restarts, attach a Railway volume and point `SHORTENER_DB_PATH` at that mounted path.
6. Deploy the service and record the public backend URL.

### Vercel frontend deployment

1. Create a new Vercel project and import the same repository.
2. Set the project root directory to `lab01-url-shortener/frontend`.
3. Keep the existing Next.js build configuration in `frontend/next.config.mjs`.
4. Add the frontend environment variable in Vercel:
   - `NEXT_PUBLIC_API_BASE_URL=<your Railway backend URL>`
5. Deploy the frontend.
6. After deployment, verify that the frontend can create a short URL and that the redirect lands on the original target.

## Verification Checklist

- Backend tests pass locally.
- Frontend builds locally.
- `POST /shorten` returns `short_code` and `short_url`.
- `GET /{short_code}` redirects to the original URL.
- Railway receives the backend start command and environment variables.
- Vercel receives the frontend API base URL.
