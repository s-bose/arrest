.PHONY: install clean lint lint-fix test coverage fixtures docs

install:
	uv sync --all-groups --all-extras

clean:
	bash ./scripts/clean.sh

lint: install
	bash ./scripts/lint.sh

lint-fix: install
	bash ./scripts/lint.sh --fix

test: install
	bash ./scripts/test.sh

coverage: install
	bash ./scripts/coverage.sh; \
	uv run coverage report --show-missing; \
	uv run coverage html


safety: install
	uv run safety scan -i 70612 # jinja2 SSTI vuln

fixtures:
	uv run python scripts/regenerate_fixtures.py

serve-docs: install
	serve htmlcov/ -p 3000
