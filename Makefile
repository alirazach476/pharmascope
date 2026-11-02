# PharmaScope developer commands
# On Windows without make, use the PowerShell equivalents in the README.

.PHONY: install test lint typecheck download-events transform-events analytics api dashboard slice benchmarks

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src tests scripts

typecheck:
	mypy src/pharmascope

download-events:
	python scripts/download_data.py --source openfda_events --limit 200

transform-events:
	python scripts/run_transformations.py --source openfda_events

analytics:
	python scripts/run_analytics.py

slice:
	python -m pharmascope.cli run-slice --limit 200

benchmarks:
	python scripts/run_benchmarks.py

api:
	uvicorn pharmascope.api.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run src/pharmascope/dashboard/app.py
