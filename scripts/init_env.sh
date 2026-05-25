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

# --- Java JRE (required by Allure CLI; not on PyPI) ---
# Allure 2 is a JVM tool, so we need a JRE on PATH. If one is missing,
# install a portable Adoptium Temurin JRE into ~/.local/jre — no sudo
# required, works on any *nix box. This keeps the "any machine" promise
# of init_env.sh intact.
JRE_DIR="$HOME/.local/jre"
mkdir -p "$HOME/.local/bin"
if command -v java >/dev/null 2>&1; then
    echo "java: $(java -version 2>&1 | head -1) OK"
elif [ -x "$JRE_DIR/bin/java" ]; then
    export PATH="$JRE_DIR/bin:$PATH"
    echo "java: using portable JRE at $JRE_DIR"
else
    case "$(uname -s)" in
        Linux)  jre_os=linux ;;
        Darwin) jre_os=mac ;;
        *)      jre_os="" ;;
    esac
    case "$(uname -m)" in
        x86_64|amd64)  jre_arch=x64 ;;
        aarch64|arm64) jre_arch=aarch64 ;;
        *)             jre_arch="" ;;
    esac
    if [ -z "$jre_os" ] || [ -z "$jre_arch" ]; then
        echo "java: unsupported OS/arch ($(uname -s)/$(uname -m)); install JRE manually."
    else
        echo "java: installing portable Adoptium JRE 21 (${jre_os}/${jre_arch})..."
        url="https://api.adoptium.net/v3/binary/latest/21/ga/${jre_os}/${jre_arch}/jre/hotspot/normal/eclipse"
        curl -fsSL "$url" -o /tmp/jre.tar.gz
        mkdir -p "$JRE_DIR"
        # Tarball has a single top-level dir; --strip-components=1 places
        # bin/, lib/, etc. directly under $JRE_DIR.
        tar -xzf /tmp/jre.tar.gz -C "$JRE_DIR" --strip-components=1
        rm /tmp/jre.tar.gz
        export PATH="$JRE_DIR/bin:$PATH"
        echo "java: portable JRE installed to $JRE_DIR"
    fi
fi

# --- Allure CLI (Java-based; not on PyPI — uv sync cannot install it) ---
# The pip package `allure-pytest` (in uv.lock) only emits JSON results;
# rendering them as HTML needs the standalone Allure 2 binary. We write
# a launcher wrapper at ~/.local/bin/allure so the shell finds it on
# PATH (~/.local/bin is already there because uv put itself there).
# The wrapper pins JAVA_HOME to our portable JRE if one was installed
# above, so allure works even in shells where java is not otherwise
# visible.
ALLURE_VERSION="2.30.0"
ALLURE_HOME="$HOME/.local/allure-${ALLURE_VERSION}"
ALLURE_BIN="$HOME/.local/bin/allure"
if [ ! -x "$ALLURE_HOME/bin/allure" ]; then
    echo "installing allure CLI ${ALLURE_VERSION}..."
    curl -fsSL "https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.tgz" \
        -o /tmp/allure.tgz
    tar -xzf /tmp/allure.tgz -C "$HOME/.local"
    rm /tmp/allure.tgz
    echo "allure: installed to $ALLURE_HOME"
fi
# Write/refresh the launcher wrapper. Use the portable JRE if it
# exists, else trust the system java.
cat > "$ALLURE_BIN" <<EOF
#!/usr/bin/env bash
if [ -x "$JRE_DIR/bin/java" ]; then
    export JAVA_HOME="$JRE_DIR"
    export PATH="\$JAVA_HOME/bin:\$PATH"
fi
exec "$ALLURE_HOME/bin/allure" "\$@"
EOF
chmod +x "$ALLURE_BIN"
echo "allure: $($ALLURE_BIN --version 2>&1 | head -1) via $ALLURE_BIN"

# --- unit-test sanity ---
uv run pytest tests/unit -v

cat <<'EOF'

Environment ready.
Run regression:   PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
Run simulation:   uv run python scripts/simulate_usage.py
View Allure:      allure serve --host 0.0.0.0 -p 8080 allure-results
                  then open http://localhost:8080 in your browser.
                  The --host flag is required on WSL2 — without it Allure binds
                  to 127.0.1.1 (the WSL hostname alias), which Windows cannot
                  reach. The "Browse action not supported" stack trace from
                  Allure is non-fatal — it means Java can't auto-launch a
                  browser in a headless shell; the server is still serving.
EOF
