.PHONY: install lint typecheck test audit sbom run snapshot check
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
	$(PY) -m pda_data.job --raw data/raw --out output
snapshot:
	$(PY) scripts/fetch_snapshot.py --out data/raw
check: lint typecheck test audit
