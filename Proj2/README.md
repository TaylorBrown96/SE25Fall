# Weeklies – Full Stack (FastAPI + React)

## How this repo is organized
- `.devcontainer/` → Developer image (Python + Node) for VS Code Dev Containers.
- `backend/` → FastAPI app + production Dockerfile.
- `frontend/react/` → React (Vite) app + production Dockerfile.
- `docker-compose.yml` → Runs frontend+backend together (prod-like).

## Dev workflow (VS Code Dev Container)
1. Open in VS Code → Command Palette → “Dev Containers: Reopen in Container”
2. Start API:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
3. Start web:
   ```bash
   cd frontend/react
   pnpm dev

## Prod-like run (no DevContainer needed)
1. Run this:
   ```bash
   docker compose up --build
