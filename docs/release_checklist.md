# Release Checklist

Use this checklist before publishing a new `ai-runtime` release.

## Pre-release

- [ ] All tests pass locally (`pytest`).
- [ ] All tests pass in CI (if configured).
- [ ] `ruff check .` and `mypy ai_runtime` report no new errors.
- [ ] Documentation is updated (`docs/`, `README.md`).
- [ ] `CHANGELOG.md` has an entry for the new version under `Unreleased`
      or the target version header with the date.
- [ ] Version is bumped in **both** places:
      - `ai_runtime/version.py` (`__version__`)
      - `pyproject.toml` (`[project].version`)
- [ ] Deprecated aliases in `ai_runtime/compat.py` are still present and
      emit `DeprecationWarning`.
- [ ] No breaking public API changes without a major version bump and a
      compatibility shim.

## Versioning

This project follows [Semantic Versioning](https://semver.org):

- **MAJOR** — incompatible API changes (remove shims, rename core symbols).
- **MINOR** — backwards-compatible features (new providers, new events).
- **PATCH** — backwards-compatible bug fixes.

## Packaging

1.  Update version in `ai_runtime/version.py` and `pyproject.toml`.
2.  Build:

    ```bash
    python -m build
    ```

3.  Check:

    ```bash
    twine check dist/*
    ```

4.  Upload to TestPyPI:

    ```bash
    twine upload --repository testpypi dist/*
    ```

5.  Upload to PyPI:

    ```bash
    twine upload dist/*
    ```

6.  Tag the release:

    ```bash
    git tag v$(python -c "import ai_runtime; print(ai_runtime.__version__)")
    git push --tags
    ```

## Post-release

- [ ] GitHub release created with `CHANGELOG.md` notes.
- [ ] Announce if this is a major/minor release.
