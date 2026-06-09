cleancache:
	-# Clean cache...
	@for d in __pycache__ .mypy_cache .pytest_cache .cache .tox ; do \
		find . -type d -name "$$d" -exec rm -rf {} +; \
	done
	@pyclean . || true
