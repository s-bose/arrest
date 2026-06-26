.PHONY: install clean lint test coverage docs

install:
	uv sync
	uv sync --group dev --group docs

clean:
	bash ./scripts/clean.sh

lint:
	bash ./scripts/lint.sh

test:
	bash ./scripts/test.sh

coverage:
	bash ./scripts/coverage.sh; \
	uv run coverage report --show-missing; \
	uv run coverage html


safety:
	uv run safety check -i 70612 # jinja2 SSTI vuln

serve:
	serve htmlcov/ -p 3000
