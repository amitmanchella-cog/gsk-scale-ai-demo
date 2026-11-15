.PHONY: install lint typecheck test audit sbom run sync-benchmark check
PY ?= python

install:
	$(PY) -m pip install -e ".[dev]"
lint:
	ruff check . && ruff format --check .
typecheck:
	mypy
test:
	pytest
audit:
	pip-audit --skip-editable
sbom:
	cyclonedx-py environment --output-format JSON --output-file sbom.json
run:
	uvicorn pda_api.main:app --host 0.0.0.0 --port 8000
# Refresh the committed sample copy from a local pda-data run (make -C ../pda-data run).
sync-benchmark:
	cp ../pda-data/output/v1/trial_features/part-*.parquet tests/fixtures/benchmark/v1/trial_features.parquet
	cp ../pda-data/output/v1/recruiting_trials/part-*.parquet tests/fixtures/benchmark/v1/recruiting_trials.parquet
	cp ../pda-data/output/v1/_MANIFEST.json tests/fixtures/benchmark/v1/_MANIFEST.json
check: lint typecheck test audit
