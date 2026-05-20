Configure Allure reporting and the GitHub Actions CI workflow.

=== Allure configuration ===

In pyproject.toml [tool.pytest.ini_options] (or pytest.ini, whichever 
the scaffold used):
- Add --alluredir=allure-results to default addopts.
- Add markers if not already declared: smoke, regression, slow.

In tests/conftest.py, add a session-scoped autouse fixture that writes 
allure-results/environment.properties with these lines (one per line, 
format "key=value"):
  python.version=<sys.version short form>
  playwright.version=<playwright.__version__>
  profile=<os.getenv("PROFILE","dev")>
  base_url=<db.environments.get(profile).base_url>
  region=<env.region>
  headless=<env.headless>

Use the standard playwright python import path for version detection.

In tests/conftest.py, ensure these are attached to Allure on every test:
- Playwright trace: started on retry (use the existing pytest-playwright 
  --tracing=retain-on-failure CLI flag — set this in pyproject addopts 
  rather than reimplementing).
- Video on failure: --video=retain-on-failure (same).
- Screenshot on failure: --screenshot=only-on-failure (same).
- ScreenshotManager screenshots from services: services already attach 
  via allure.attach inline — do not duplicate from conftest.

Reference: pytest-playwright auto-attaches trace/video/screenshot to 
Allure when both plugins are active. Verify by reading the 
pytest-playwright plugin source if uncertain rather than guessing.

=== GitHub Actions workflow ===

Create .github/workflows/regression.yml:

name: regression
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  regression-chromium-headless:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Sync dependencies
        run: ~/.local/bin/uv sync
      - name: Install Playwright browsers
        run: ~/.local/bin/uv run playwright install --with-deps chromium
      - name: Run regression suite
        env:
          PROFILE: ci
        run: ~/.local/bin/uv run pytest -m regression -n 4 --alluredir=allure-results
        continue-on-error: true
      - name: Install Allure CLI
        run: |
          curl -o allure-2.27.0.tgz -Ls https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz
          tar -xzf allure-2.27.0.tgz
          echo "$PWD/allure-2.27.0/bin" >> $GITHUB_PATH
      - name: Generate Allure HTML report
        run: allure generate allure-results --clean -o allure-report
      - name: Upload Allure results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: allure-results
          path: allure-results/
          retention-days: 14
      - name: Upload Allure HTML report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: allure-report
          path: allure-report/
          retention-days: 14
      - name: Upload screenshots and logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: reports
          path: reports/
          retention-days: 14

=== Verification ===

1. uv run pytest --collect-only -m regression → must still collect 
   (Prompt 5's tests).
2. Validate the workflow YAML syntax:
   uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/regression.yml'))"
   Must print nothing (success) or raise a clear error.
3. Confirm pyproject.toml addopts include: 
   --alluredir, --tracing=retain-on-failure, --video=retain-on-failure, 
   --screenshot=only-on-failure.
4. Report the contents of the addopts line.
