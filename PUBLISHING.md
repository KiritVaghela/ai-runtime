# Publishing `forge-ai-runtime` as a Python Package

This guide walks through validating, packaging, and publishing the
`ai_runtime` library to PyPI so it can be installed anywhere with:

```bash
pip install forge-ai-runtime
```

> **Two names to keep straight:**
> - **Distribution name** = `forge-ai-runtime` — what you type in `pip install`
>   (defined in `pyproject.toml` → `[project] name`).
> - **Import package** = `ai_runtime` — what you write in code
>   (`import ai_runtime`). The directory on disk is `ai_runtime/`.
>
> The **web app** (`web/`) is intentionally **not** part of the package.
> See [Excluding the web app](#excluding-the-web-app) below.

---

## 1. Package naming

The published distribution name is **`forge-ai-runtime`**. The internal import package stays **`ai_runtime`** — only the
distribution name changed, so no code or imports were touched.

If you ever rename the distribution, update one place:

1. `pyproject.toml` → `[project] name = "..."`

The importable package directory (`ai_runtime/`) and all `import ai_runtime`
statements stay the same.

---

## 2. Prerequisites

```bash
# From the repo root
./venv/bin/python -m pip install --upgrade build twine
```

You also need a **PyPI account** and an **API token**:
<https://pypi.org/manage/account/token/>

Export it for the upload step:

```bash
export PYPI_API_TOKEN="pypi-xxxxxxxxxxxx"
```

---

## 3. Validate the project

Run the full test suite before every release:

```bash
TMPDIR="$HOME/ai-runtime-tmp" ./venv/bin/python -m pytest -q
```

Expected: `127 passed, 1 skipped`.

Optional quality gates:

```bash
./venv/bin/python -m ruff check ai_runtime
./venv/bin/python -m mypy ai_runtime
```

---

## 4. Bump the version

Edit `ai_runtime/version.py`:

```python
__version__ = "0.8.0"
```

Follow [Semantic Versioning](https://semver.org/):
- **patch** (`0.7.1`) — bug fixes only
- **minor** (`0.8.0`) — new features, backward-compatible
- **major** (`1.0.0`) — breaking changes

Also update `version` in `pyproject.toml` if you keep it in sync (currently
the single source of truth is `ai_runtime/version.py`, surfaced via
`dynamic = ["version"]` or hardcoded — keep them equal).

---

## 5. Build the distribution

```bash
rm -rf dist build *.egg-info
./venv/bin/python -m build
```

This produces (note: PyPI normalizes the hyphen to an underscore in the
filename — `forge-ai-runtime` ↔ `forge_ai_runtime`):

```
dist/
├── forge_ai_runtime-0.8.0-py3-none-any.whl   # installable wheel
└── forge_ai_runtime-0.8.0.tar.gz            # source sdist
```

---

## 6. Inspect the artifacts

Confirm the **web app is excluded** and only the library ships:

```bash
# web/ must appear 0 times in both artifacts
unzip -l dist/forge_ai_runtime-0.8.0-py3-none-any.whl | grep -c "web/"
tar tzf  dist/forge_ai_runtime-0.8.0.tar.gz            | grep -c "web/"
```

Expected output: `0` for both.

List the wheel contents to sanity-check the package layout (you should see
`ai_runtime/...`, not `web/`):

```bash
unzip -l dist/forge_ai_runtime-0.8.0-py3-none-any.whl
```

---

## 7. Test install in a clean environment

Never trust the build without a clean install test:

```bash
python3 -m venv /tmp/pkgtest
/tmp/pkgtest/bin/pip install dist/forge_ai_runtime-0.8.0-py3-none-any.whl

/tmp/pkgtest/bin/python -c "
import ai_runtime
print('version:', ai_runtime.__version__)
from ai_runtime.providers.default_registry import create_default_registry
print('providers:', [p.value for p in create_default_registry().list_providers()])
"
rm -rf /tmp/pkgtest
```

---

## 8. Upload to PyPI

```bash
./venv/bin/python -m twine upload dist/*
```

Twine reads `PYPI_API_TOKEN` from the environment (or prompts for
username/password). Use `__token__` as the username with the token as the
password if prompted interactively.

> **Test first on TestPyPI** to avoid polluting the real index:
>
> ```bash
> ./venv/bin/python -m twine upload --repository testpypi dist/*
> pip install --index-url https://test.pypi.org/simple/ forge-ai-runtime
> ```

---

## 9. Verify the published package

```bash
pip install forge-ai-runtime==0.8.0
python -c "import ai_runtime; print(ai_runtime.__version__)"
```

---

## 10. Tag the release (git)

```bash
git add -A
git commit -m "Release v0.8.0"
git tag v0.8.0
git push origin main --tags
```

---

## Excluding the web app

The `web/` directory is excluded from the package by two mechanisms:

1. **`pyproject.toml`** — `setuptools.packages.find` only includes
   `ai_runtime*` packages, so the top-level `web/` folder is never treated as
   an importable package.
2. **`MANIFEST.in`** — explicitly excludes `web`, `tests`, `docs`, `venv`, and
   other non-library directories from the sdist:

   ```ini
   recursive-exclude web *
   recursive-exclude tests *
   recursive-exclude docs *
   recursive-exclude venv *
   ```

This guarantees `pip install forge-ai-runtime` ships **only the library**, not
the web frontend.

---

## Integrating the web app with the published package

The web app imports `ai_runtime.*` (e.g. `from ai_runtime.providers import
ProviderConfig`). As long as `forge-ai-runtime` is installed in the same Python
environment that runs `web/app.py`, no code changes are required:

```bash
# In the web app's environment
pip install forge-ai-runtime
./venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8787
```

During local development you can instead install the library in editable
mode so changes to `ai_runtime/` are picked up without reinstalling:

```bash
pip install -e .
```
