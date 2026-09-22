.PHONY: cleancache lint test tox release-guards build-check publish

VERSION := $(shell grep -oP '__version__ = "\K[^"]+' codenerix/__init__.py)

cleancache:
	-# Clean cache...
	@for d in __pycache__ .mypy_cache .pytest_cache .cache .tox ; do \
		find . -type d -name "$$d" -exec rm -rf {} +; \
	done
	@pyclean . || true

lint:
	-# Lint and type checks, same commands as the CI workflow...
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy codenerix
	uv run basedpyright codenerix

test:
	-# Run tests...
	uv run python -m pytest

tox:
	-# Run tests in all environments...
	uv run tox

release-guards:
	-# Pre-flight checks for $(VERSION)...
	@test -n "$(VERSION)" || { echo "ERROR: could not read __version__"; exit 1; }
	@if git rev-parse "v$(VERSION)" >/dev/null 2>&1; then \
		echo "ERROR: tag v$(VERSION) already exists locally (forgot to bump __version__?)"; exit 1; fi
	@if git ls-remote --tags --exit-code origin "refs/tags/v$(VERSION)" >/dev/null 2>&1; then \
		echo "ERROR: tag v$(VERSION) already exists on origin (forgot to bump __version__?)"; exit 1; fi
	@grep -q "^## \[$(VERSION)\]" CHANGELOG || { \
		echo "ERROR: no CHANGELOG entry for $(VERSION)"; exit 1; }
	@# `git commit -am` below only picks up TRACKED files, so an untracked file
	@# that belongs in the release would be silently left out of it.
	@untracked=$$(git ls-files --others --exclude-standard); \
	 if [ -n "$$untracked" ]; then \
		echo "ERROR: untracked files present -- git add them, or add them to .gitignore:"; \
		echo "$$untracked" | sed 's/^/  /'; exit 1; fi
	@echo "OK: $(VERSION) ready (tag free locally and on origin, changelog present, no untracked files)"

build-check:
	-# Local build and static-asset verification in the wheel...
	@rm -rf dist
	uv build
	@n=$$(unzip -l dist/*.whl | grep -cE '\.(js|css|html)$$'); \
	 echo "Static assets in wheel: $$n"; \
	 test "$$n" -gt 0 || { echo "ERROR: wheel is missing static assets"; exit 1; }

publish: release-guards lint test build-check
	-# Commit, tag and push $(VERSION)...
	git commit -am "Release $(VERSION)"
	@# Annotated tag, so the release notes live in the tag itself. The message
	@# is the CHANGELOG section for this version, which release-guards already
	@# verified is present.
	@awk '/^## \[$(VERSION)\]/{f=1;print;next} f&&/^## \[/{exit} f' CHANGELOG > .tagmsg
	git tag -a "v$(VERSION)" -F .tagmsg
	@rm -f .tagmsg
	git push origin master --tags
	-# Wait for CI on the pushed commit BEFORE publishing anything...
	@# The local gate only covers one Python; CI runs the whole matrix. A red
	@# CI must stop the release, not be discovered after it is public.
	@sha=$$(git rev-parse HEAD); \
	 echo "Waiting for a CI run on $$sha..."; \
	 for i in $$(seq 1 30); do \
		id=$$(gh run list --commit "$$sha" --workflow CI --limit 1 \
			--json databaseId --jq '.[0].databaseId' 2>/dev/null); \
		[ -n "$$id" ] && break; \
		sleep 5; \
	 done; \
	 test -n "$$id" || { echo "ERROR: no CI run found for $$sha after 150s"; exit 1; }; \
	 gh run watch "$$id" --exit-status
	-# CI is green, publish the release (this triggers the PyPI workflow)...
	gh release create "v$(VERSION)" --title "$(VERSION)" --notes-from-tag
	gh run watch
