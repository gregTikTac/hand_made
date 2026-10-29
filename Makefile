.PHONY: up down build migrate shell test lint fmt collect static

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm web python manage.py migrate

shell:
	docker compose run --rm web python manage.py shell

superuser:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose run --rm web pytest

lint:
	ruff check .

fmt:
	ruff format .

static:
	docker compose run --rm web python manage.py collectstatic --noinput

tailwind:
	docker compose run --rm web python manage.py tailwind_build
