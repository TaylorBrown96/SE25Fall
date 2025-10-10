#!/usr/bin/env bash
set -euo pipefail

echo "[postCreate] Versions:"
python --version || true
pip --version || true
node -v || true
npm -v || true
pnpm -v || true

# Python deps (adjust to your project)
if [ -f "backend/requirements.txt" ]; then
  pip install -r backend/requirements.txt
fi

# Optional: bootstrap frontend if needed
if [ -d "frontend/react" ] && [ -f "frontend/react/package.json" ]; then
  (cd frontend/react && pnpm install || npm install)
fi

echo "[postCreate] Done."
