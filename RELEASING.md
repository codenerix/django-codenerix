# Releasing django-codenerix

This document describes how to cut and publish a new release of
`django-codenerix` to PyPI.

## How it works

- **Single source of truth for the version:** `codenerix/__init__.py`
  (`__version__ = "X.Y.Z"`). Hatchling reads it at build time via
  `[tool.hatch.version]`.
- **Releases are driven by Git tags + GitHub Releases.** Publishing a
  GitHub Release triggers `.github/workflows/release.yml`, which builds
  the sdist + wheel and uploads them to PyPI.
- **No tokens or secrets.** Publishing uses PyPI Trusted Publishing
  (OIDC): the workflow proves its identity to PyPI with a short-lived
  token that only exists during the run.

The release workflow enforces two guards and refuses to publish if either
fails:

1. **Tag matches `__version__`** — the tag (`vX.Y.Z`) must match the
   version string in `codenerix/__init__.py`.
2. **Static assets are bundled** — the wheel must contain JS/CSS/HTML
   assets. This catches build regressions (e.g. the historical
   `_codenerix` symlink that produced an empty wheel).

## One-time setup

Done once per project; you do **not** repeat this for each release.

1. **PyPI Trusted Publisher.** On PyPI, go to the project
   (`django-codenerix`) then *Settings → Publishing → Add a new
   publisher*, and register:
   - Owner: `codenerix`
   - Repository: `django-codenerix`
   - Workflow: `release.yml`
   - Environment: `pypi`

   For a brand-new project that has never been uploaded, create a
   *pending publisher* from your PyPI account publishing settings instead.
2. **GitHub environment.** In GitHub, go to *Settings → Environments* and
   create an environment named `pypi`. Optionally add required reviewers
   there to require manual approval before each publish.

## Cutting a release

Example: releasing `5.0.81`.

1. **Bump the version.** Edit `codenerix/__init__.py`:

   ```python
   __version__ = "5.0.81"
   ```

2. **Update the changelog.** Add an entry for `5.0.81` to `CHANGELOG`.

3. **Commit:**

   ```bash
   git commit -am "Release 5.0.81"
   ```

4. **Tag and push.** The tag must be `v` + the exact version:

   ```bash
   git tag v5.0.81
   git push origin master --tags
   ```

5. **Create the GitHub Release.** On GitHub, go to *Releases → Draft a new
   release*, pick the `v5.0.81` tag, write the notes, and click *Publish
   release*.

6. **Watch the Actions tab.** The `Release` workflow runs the guards,
   builds, and publishes. A green check means it is live on PyPI:
   <https://pypi.org/project/django-codenerix/>

## Versioning convention

Semantic-ish `MAJOR.MINOR.PATCH`:

- **PATCH** (`5.0.80` → `5.0.81`) — bug fixes, no API changes.
- **MINOR** (`5.0.x` → `5.1.0`) — new backwards-compatible features.
- **MAJOR** (`5.x` → `6.0.0`) — backwards-incompatible changes.

The Git tag is always `v` + the version (e.g. `v5.0.81`).

## Testing the pipeline on TestPyPI (optional)

Before a real release you can dry-run against TestPyPI:

1. Register a Trusted Publisher on <https://test.pypi.org> for this repo.
2. Temporarily add `--publish-url https://test.pypi.org/legacy/` to the
   `uv publish` step.
3. Push a test tag and publish a pre-release.

## Building locally (no publish)

```bash
uv build
unzip -l dist/*.whl | grep -cE '\.(js|css|html)$'
```

The second command is a coherence check that assets are bundled; it should
print a number greater than 0.

## Troubleshooting

- **Workflow fails on "Tag must match `__version__`".** You tagged a
  version that does not match `codenerix/__init__.py`. Fix the version
  string (or the tag) so they agree, then re-tag.
- **Workflow fails on "Verify static assets are bundled" (count 0).** The
  wheel was built without its static/template files. Make sure the
  `_codenerix` symlink is **not** present in the repo; with it gone the
  default build is correct. The `[tool.hatch.build.targets.sdist]
  only-include` block also keeps the source tarball clean.
- **`uv publish` is rejected by PyPI.** The Trusted Publisher config on
  PyPI does not match this repo/workflow/environment. Re-check owner,
  repository, workflow filename, and environment name.
