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
	bash ./scripts/coverage.sh

serve:
	serve htmlcov/ -p 3000
