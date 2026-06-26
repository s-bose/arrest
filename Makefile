.PHONY: install clean lint test coverage docs

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
	uv run safety check -i 70612 # jinja2 SSTI vuln

serve-docs: install
	serve htmlcov/ -p 3000
