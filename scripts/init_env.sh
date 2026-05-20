#!/usr/bin/env bash
set -euo pipefail

# Idempotent local environment bootstrap. Safe to re-run.

# --- Python 3.11+ check ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 not found on PATH" >&2
    exit 1
fi
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "error: Python 3.11+ required (have ${PY_MAJOR}.${PY_MINOR})" >&2
    exit 1
fi
echo "python: ${PY_MAJOR}.${PY_MINOR} OK"

# --- uv ---
if ! command -v uv >/dev/null 2>&1; then
    echo "installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "uv: $(uv --version)"

# --- deps + browsers ---
uv sync
# Always fetch/refresh the browser binary (no sudo needed).
uv run playwright install chromium
# Then probe whether the system apt libs chromium links against are
# already present. If chromium launches headlessly, skip --with-deps and
# avoid the sudo prompt — important for re-runs and unattended cron use.
if uv run python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    b.close()
" >/dev/null 2>&1; then
    echo "chromium: system libs present; skipping --with-deps"
else
    echo "chromium: system libs missing; running --with-deps (sudo required, one-time)"
    uv run playwright install --with-deps chromium
fi

# --- .env (only if missing) ---
if [ -f .env.example ]; then
    cp -n .env.example .env || true
fi

# --- unit-test sanity ---
uv run pytest tests/unit -v

cat <<'EOF'

Environment ready.
Run regression:   PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
Run simulation:   uv run python scripts/simulate_usage.py
View Allure:      uv run allure serve allure-results
EOF
