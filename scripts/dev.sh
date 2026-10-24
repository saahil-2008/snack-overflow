#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${FARMPOOL_VENV:-/workspace/.snack-overflow-venv}"
runtime_dir="${FARMPOOL_RUNTIME:-/workspace/.snack-overflow-runtime}"
mkdir -p "$runtime_dir/audio"
if [[ ! -x "$venv_dir/bin/python" ]]; then
  echo "Python environment missing. Follow the install steps in frontend/README.md." >&2
  exit 1
fi
export DATABASE_URL="${DATABASE_URL:-sqlite:///$runtime_dir/app.db}"
export AUDIO_DIR="${AUDIO_DIR:-$runtime_dir/audio}"
export PYTHONDONTWRITEBYTECODE=1
cd "$project_dir"
"$venv_dir/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
backend_pid=$!
cleanup() { kill "$backend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
cd frontend
npm run dev
