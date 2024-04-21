.PHONY: install clean lint test coverage docs

install:
	poetry install
	poetry install --with dev,docs

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

lint:
	poetry run black --check .
	poetry run flake8 .
	isort --check-only --diff tests

test:
	poetry run pytest -vvv

coverage:
	poetry run pytest tests --cov=arrest --cov-report=term-missing --cov-report=html

serve:
	serve htmlcov/ -p 3000

tox:
	tox -- --cov=arrest --cov-append --cov-report=term-missing --cov-report=term
