.PHONY: cleancache test tox

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
