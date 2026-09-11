.PHONY: cleancache test tox release-guards build-check publish

VERSION := $(shell grep -oP '__version__ = "\K[^"]+' codenerix/__init__.py)

cleancache:
	-# Clean cache...
	@for d in __pycache__ .mypy_cache .pytest_cache .cache .tox ; do \
		find . -type d -name "$$d" -exec rm -rf {} +; \
	done
	@pyclean . || true

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
	@echo "OK: $(VERSION) ready (tag free locally and on origin, changelog present)"

build-check:
	-# Local build and static-asset verification in the wheel...
	@rm -rf dist
	uv build
	@n=$$(unzip -l dist/*.whl | grep -cE '\.(js|css|html)$$'); \
	 echo "Static assets in wheel: $$n"; \
	 test "$$n" -gt 0 || { echo "ERROR: wheel is missing static assets"; exit 1; }

publish: release-guards test build-check
	-# Commit, tag, push and publish $(VERSION)...
	git commit -am "Release $(VERSION)"
	git tag "v$(VERSION)"
	git push origin master --tags
	gh release create "v$(VERSION)" --title "$(VERSION)" --generate-notes
	gh run watch
