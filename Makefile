.PHONY: up down build migrate shell superuser superuser-env test lint fmt static

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

# Interactive superuser creation
superuser:
	docker compose run --rm web python manage.py createsuperuser

# Non-interactive: needs DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD in .env
superuser-env:
	docker compose run --rm web python manage.py createsuperuser --noinput

test:
	docker compose run --rm web pytest

lint:
	docker compose run --rm web sh -c "ruff check . && ruff format --check ."

fmt:
	docker compose run --rm web ruff format .

static:
	docker compose run --rm web python manage.py collectstatic --noinput
