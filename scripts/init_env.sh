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

# --- Allure CLI (Java-based; not on PyPI — uv sync cannot install it) ---
# The pip package `allure-pytest` (in uv.lock) only emits JSON results;
# rendering them as HTML needs the standalone Allure 2 binary, which is
# a JVM tool distributed via GitHub releases. Install it into ~/.local
# on first run; require a JRE on PATH. If java is missing, skip and
# print a clear instruction — pytest itself is unaffected.
ALLURE_VERSION="2.30.0"
ALLURE_HOME="$HOME/.local/allure-${ALLURE_VERSION}"
ALLURE_BIN="$HOME/.local/bin/allure"
mkdir -p "$HOME/.local/bin"
if command -v allure >/dev/null 2>&1; then
    echo "allure: $(allure --version 2>&1 | head -1) OK"
elif ! command -v java >/dev/null 2>&1; then
    echo "allure: skipping (java JRE not found on PATH)."
    echo "  pytest will still emit results to allure-results/."
    echo "  To view locally: install a JRE (e.g. 'sudo apt install default-jre')"
    echo "  then re-run this script, or use the GitHub Actions artifact."
elif [ ! -x "$ALLURE_HOME/bin/allure" ]; then
    echo "installing allure CLI ${ALLURE_VERSION}..."
    curl -fsSL "https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.tgz" \
        -o /tmp/allure.tgz
    tar -xzf /tmp/allure.tgz -C "$HOME/.local"
    rm /tmp/allure.tgz
    ln -sf "$ALLURE_HOME/bin/allure" "$ALLURE_BIN"
    echo "allure: installed to $ALLURE_HOME (symlinked at $ALLURE_BIN)"
else
    ln -sf "$ALLURE_HOME/bin/allure" "$ALLURE_BIN"
    echo "allure: $ALLURE_HOME present"
fi

# --- unit-test sanity ---
uv run pytest tests/unit -v

cat <<'EOF'

Environment ready.
Run regression:   PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
Run simulation:   uv run python scripts/simulate_usage.py
View Allure:      allure serve allure-results
                  (if allure was skipped above, install a JRE and re-run init_env.sh,
                   or download the rendered report from GitHub Actions artifacts)
EOF
