# Магазин PDF-мастер-классов по вязанию

Интернет-магазин цифровых товаров (PDF-схемы амигуруми): каталог 2 в ряд, гостевой чекаут по email, автоматическая выдача PDF, предзаказы, массовые акции, админка для автора.

## Документация
| Файл | Что внутри |
|---|---|
| `docs/brief/client-brief-transcript.txt` | Расшифровка требований заказчицы (первоисточник) |
| `docs/brief/palette-reference.jpg` | Референс палитры: молочный + бордовый |
| `docs/brief/knitting-shop-prompts.md` | Пакет промтов для ИИ (архитектура → дизайн → этапы) |
| `docs/ARCHITECTURE.md` | Архитектура (черновик, сверить с Opus по промту 1) |
| `docs/ROADMAP.md` | Этапы, задачи, DoD, оценки |
| `docs/adr/` | Архитектурные решения |
| `docs/client-questions.md` | Вопросы заказчице |
| `.clinerules` | Правила проекта для ИИ-ассистентов |

## Статус
Этапы 0 (дизайн) и 1 (каркас) завершены, следующий — этап 2 (каталог). Подробности: `docs/ROADMAP.md`, `CHANGELOG.md`.

## Быстрый старт
```bash
cp .env.example .env        # при необходимости поправить значения
make up                     # docker compose up -d
make superuser              # создать администратора
```
- Сайт: http://localhost:8000/, админка: http://localhost:8000/admin/, почта (Mailpit): http://localhost:8025/

| Команда | Действие |
|---|---|
| `make test` | pytest в контейнере |
| `make lint` / `make fmt` | ruff check + format / автоформат |
| `make migrate` | применить миграции |

Установка pre-commit: `pip install pre-commit && pre-commit install`.
