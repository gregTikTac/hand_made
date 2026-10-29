# Статус этапа 1: Каркас

**Ветка:** `stage-1-karkas`  
**Дата:** 2026-10-30  
**Статус:** готов к финальному коммиту этапа 1, но часть функциональности перенесена на этапы 2–5.

## Что сделано
- Создан Django-проект (`config`) и приложения: `core`, `catalog`, `orders`, `payments`, `delivery`, `promo`, `pages`.
- Настроены `requirements.txt` / `requirements-dev.txt` (Django 5.1, psycopg-binary, celery[redis], django-unfold, whitenoise, django-celery-beat и др.).
- Написан `pyproject.toml` с ruff, pytest-django, `config.settings_test`.
- Создан `Dockerfile` и `docker-compose.yml` с сервисами: `web`, `worker`, `beat`, `db` (postgres 16), `redis` (7), `mailpit`.
- Добавлен `docker-compose.override.yml` для dev-режима с `runserver`.
- Создан `.env.example` со всеми переменными; `.env` не коммитится.
- Создан `Makefile` с командами: `up`, `down`, `build`, `migrate`, `shell`, `superuser`, `test`, `lint`, `fmt`, `static`.
- Настроен `config/settings.py` (через `config/env.py`): переменные окружения, PostgreSQL по `DATABASE_URL`, Redis, Celery, кэш, локальное/S3-хранилище.
- Админка настроена на `django-unfold`: кастомный `core.admin.KnittingAdminSite` (заголовок «Петелька»).
- Созданы базовые шаблоны Django (в `templates/`), использующие CSS-дизайн-систему из этапа 0:
  - `base.html`
  - `components/header.html`
  - `components/footer.html`
  - `components/bottom_nav.html`
  - `pages/home.html` — заглушка главной с 4 товарами-образцами из `docs/brief/sample-products.json`.
- Дизайн-токены и компоненты из `docs/design/` скопированы в `static/css/` и подключаются в base.html.
- Создан `pages/views.py::home` и `pages/tests.py` — smoke-тест главной (200 OK).

## Проверки
| Проверка | Результат | Где запускалось |
|---|---|---|
| `ruff check .` | ✅ | host venv |
| `pytest` | ✅ (1 passed) | host venv |
| `python manage.py check` | ✅ | host venv (SQLite) |
| `docker compose run --rm web python manage.py check` | ✅ | Docker |
| `docker compose run --rm web python manage.py migrate` | ✅ | Docker (PostgreSQL) |
| `docker compose up -d` | ✅ | Docker |
| `curl http://localhost:8000/` | 200 | Docker |
| `curl http://localhost:8000/admin/` | 302 (редирект на логин) | Docker |

## Отклонения от архитектуры
- **Tailwind standalone CLI**: в ARCHITECTURE был заявлен Tailwind. На практике дизайн-система этапа 0 реализована через CSS variables + custom components, что проще для текущего масштаба и соответствует макетам 1:1. Добавление Tailwind потребует нового ADR, если заказчица/разработчик настаивает.
- **django-environ**: заменён на `python-dotenv` + самописный `Env` + `dj-database-url` для уменьшения зависимостей.
- **S3-хранилище**: в Dockerfile и зависимостях есть `django-storages[boto3]`, но логика переключения `local`/`s3` пока не покрыта полноценно; будем дорабатывать на этапе 5.
- ** django-celery-beat**: добавлено вместо отдельного cron для планировщика задач.

## Что осталось / блокеры
1. **Модели данных** (этап 2): пока нет ни одной модели. Будем добавлять Product, ProductImage, Category и т.д. именно в этапе 2.
2. **Импорт из CSV**: шаблон `docs/brief/sample-products.csv` готов, но команда импорта появится в этапе 2.
3. **Tailwind / CSS**: решить окончательно, оставить custom CSS или перейти на Tailwind. Если custom CSS — удалить скачивание tailwindcss из Dockerfile.
4. **CI / pre-commit**: конфигурация GitHub Actions не создана (в ROADMAP — этап 9/8). `pyproject.toml` готов к подключению.
5. **Реальные фото и PDF**: бинарные файлы из `ChatExport_2026-10-29` не коммитятся; они понадобятся локально для тестового импорта.

## Что дальше
- Этап 2: реализация каталога — модели, админка, список товаров 2 в ряд, карточка товара, импорт товаров из CSV.
- Параллельно: получить ответы из `docs/client-questions.md` (особенно статус СЗ/ИП и домен).
