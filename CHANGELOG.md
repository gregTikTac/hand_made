# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/). Версии: v0.N = завершённый этап N из docs/ROADMAP.md.

## [Unreleased]

## [v0.2] — Stage 2: Каталог
### Added
- Модели `Category`, `Product`, `ProductImage`, `ProductVideo` (CHECK-ограничения цен, частичный unique на обложку, индексы); PDF — в закрытом хранилище, с проверкой заголовка `%PDF-`.
- Деньги — целые копейки (`KopecksField`, в админке вводятся рубли), фильтр `|rub`.
- `catalog/pricing.py`: единая функция цены (скидки не суммируются, округление вниз до рубля); тесты по таблице ARCHITECTURE §3. Кампании и предзаказ подключатся на этапе 6.
- Адмика (unfold): inline-фото с перетаскиванием и превью, видео-ссылки (VK/Rutube/YouTube), подсказки, действия публикации; нельзя опубликовать товар без PDF.
- Импорт/экспорт CSV (формат `sample-products.csv`), команды `import_media`, `seed_demo`.
- Витрина: `/catalog/`, `/catalog/combo/`, `/p/<slug>/`; сетка 2 в ряд, «Показать ещё» на HTMX, галерея со свайпом, видео по клику, предпросмотр черновика для сотрудников, «Популярные» на главной из БД.
- webp-варианты 360/720/1080 + `srcset`, явные width/height, lazy-загрузка (ADR-0006).
- HTMX 2.0.4 и Alpine.js 3.14.8 — self-host в `static/js/vendor/`.
- ADR-0006: изображения через Pillow без imagekit/sorl.
- Тесты: 154 (pricing, модели, медиа, админка, импорт, команды, витрина).

### Fixed
- `STATICFILES_DIRS` не был задан: стили и скрипты из `static/` давали 404 (сайт открывался без дизайна); добавлен тест.

### Допущения
- Кнопки «В корзину» отрисованы (`data-product-id`), но ничего не делают — это этап 3.
- Ссылки поддержки/соцсетей берутся из env (`SUPPORT_URL`, `VK_URL`, ...) до `SiteSettings` в этапе 7.
- Каталог без таба «Предзаказ» из макета: предзаказы — этап 6.
- В `seed_demo` фото — заглушки; реальные фото/PDF — через `import_media` на этапе 9.

## [v0.1] — Stage 1: Каркас
### Added
- Django 5.1 проект `config` и приложения `core`, `catalog`, `orders`, `payments`, `delivery`, `promo`, `pages`.
- Docker Compose: web, worker, beat, db (PostgreSQL 16), redis (7), mailpit; healthcheck у web; `.env.example`; Makefile (`up`, `test`, `lint`, `superuser`, `superuser-env` и др.).
- Админка на django-unfold, настройка через `UNFOLD` в settings.
- Базовые шаблоны (шапка, нижняя навигация, футер-заглушка), главная-заглушка в дизайне этапа 0.
- Два хранилища: `default` (публичное, фото) и `private` (PDF); локальная FS в dev, S3 в prod (`STORAGE_BACKEND=s3`).
- CI (GitHub Actions: ruff, `manage.py check`, проверка миграций, pytest) и `.pre-commit-config.yaml`.
- Тесты каркаса: `Env`, хранилища, админка.
- ADR-0005: кастомный CSS на токенах вместо Tailwind.

### Changed
- ADR-0001 принят (с уточнением по Tailwind); обновлён ARCHITECTURE.
- Код отформатирован `ruff format`.

### Fixed
- `Env.db_url` не принимал строку по умолчанию (падал `manage.py check` без `DATABASE_URL`).
- `beat` падал на чистой БД: теперь стартует после healthy `web` (миграции применены).
- Удалены неиспользуемые Tailwind-бинарник из Dockerfile и цель `make tailwind`; удалён неработающий `KnittingAdminSite`.

### Не вошло
- Staging на VPS — перенесён в этап 9 (нужны VPS и домен).

## [v0.0] — Stage 0: Дизайн-система и макеты
### Added
- `docs/design/` : tokens.css, components.css, 4 HTML-макета + страница компонентов.
- Палитра по референсу «Молочный и бордовый», расчёт контраста WCAG.
- Mobile-first, сетка 2 в ряд, нижняя навигация, карточка товара, галерея с видео, корзина/чекаут.

### Changed
- Промты в `docs/brief/knitting-shop-prompts.md` приведены в соответствие с брифом заказчицы (видео, категории, палитра, ADR, правила этапов).
- Заполнены `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, ADR 0001–0004.

## [0.0.0-pre] — Инициализация документации
### Added
- Структура репозитория и документации (`docs/brief`, `docs/adr`, `docs/design`).
- `.clinerules` — правила проекта для ИИ-ассистентов.
- `docs/client-questions.md` — вопросы заказчице.
