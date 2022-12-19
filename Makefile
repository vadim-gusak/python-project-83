dev:
		poetry run flask --app page_analyzer:app --debug run

lint:
		poetry run flake8 page_analyzer

test-cov:
		poetry run pytest --cov=page_analyzer --cov-report xml

install:
		poetry install

PORT ?= 8000
start:
		poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

all: db-create schema-load

db-create:
	createdb database || echo 'skip'

schema-load:
	psql database < schema.sql
