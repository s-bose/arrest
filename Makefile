.PHONY: install clean lint test coverage docs

install:
	poetry install
	poetry install --with dev,docs

clean:
	bash ./scripts/clean.sh

lint:
	bash ./scripts/lint.sh

test:
	bash ./scripts/test.sh

coverage:
	bash ./scripts/coverage.sh; \
	poetry run coverage report --show-missing; \
	poetry run coverage html


safety:
	poetry run safety check -i 70612 # jinja2 SSTI vuln

serve:
	serve htmlcov/ -p 3000
