# ARCHITECTURE.md — магазин PDF-мастер-классов

> Статус: **черновик v0.1** (подготовлен по промту 1, требует сверки с Opus и ответов из `docs/client-questions.md`).
> Всё, что помечено **[проверить]**, — условия внешних сервисов/законов, которые нужно подтвердить по актуальным источникам.

## 0. Контекст
- Цифровые товары: PDF-схемы (80+, рост ~2 предзаказа/мес).
- Аудитория — мобильная. Каталог — **всегда 2 карточки в ряд**.
- Покупка без регистрации: корзина → email → оплата → письмо со ссылкой на PDF.
- Один разработчик, ограниченный бюджет → максимум готовых решений.

## 1. Выбор стека

| Критерий | A) Django + admin + HTMX/Alpine + Tailwind | B) Next.js + Headless CMS | C) FastAPI + react-admin |
|---|---|---|---|
| Скорость разработки одним человеком | ★★★★★ админка, ORM, формы, миграции | ★★★ два приложения, два деплоя | ★★ админку и auth писать самому |
| SEO | ★★★★★ SSR по умолчанию | ★★★★★ SSR/SSG | ★★★ нужен SSR-слой |
| Админка для нетехнического человека | ★★★★ после настройки (тема, inline-фото) | ★★★★★ CMS удобнее из коробки | ★★★ зависит от усилий |
| Хостинг | 1 VPS | VPS + Node + CMS | 1 VPS |
| Соответствие навыкам (Python) | полное | частичное (TS) | полное |
| Риски | «старомодный» фронт (решает HTMX) | два стека, обновления CMS | долгий MVP |

**Решение: вариант A** (см. `adr/0001-stack.md`).
- Django 5.x, PostgreSQL 16, Redis 7, Celery + celery-beat (письма, рассылка предзаказов, расписание акций).
- Шаблоны Django + HTMX (корзина без перезагрузки) + Alpine.js (галерея, табы) + Tailwind (standalone CLI).
- Админка: Django admin + тема django-unfold [проверить актуальность] + django-import-export (CSV).
- Изображения: генерация webp в нескольких размерах (django-imagekit или sorl-thumbnail).
- Хранилище: django-storages (S3-совместимое): публичный бакет для фото, **приватный** для PDF.

## 2. Модель данных

```
Category *─* Product 1─* ProductImage
              │ 1─* ProductVideo
              │ 1─* ComboItem *─1 Product (входящие)
              │ 1─0..1 PreorderRelease
Order 1─* OrderItem *─1 Product
Order 1─* Payment
OrderItem 1─* DownloadLink
EmailLog *─1 Order (nullable)
DiscountCampaign (глобальная)   SiteSettings (singleton)   Page
```

Все деньги — **integer в копейках**.

### Product
| Поле | Тип | Примечание |
|---|---|---|
| title | varchar(200) | |
| slug | varchar(220) unique | ЧПУ, транслит |
| short_description | varchar(300) | карточка / OG |
| description | text | «PDF-схема…», размер, уровень |
| base_price | int | CHECK > 0 |
| compare_price | int null | ручная «старая цена» |
| materials_image | image | «Необходимые материалы» фотографией |
| pdf_file | file (private) null | null допустим только у предзаказа |
| status | draft / published / archived | |
| is_combo | bool | |
| sort_order, popularity | int | порядок каталога, «популярные» |
| seo_title, seo_description | varchar | опционально |

Индексы: `(status, sort_order)`, `(status, is_combo)`. CHECK: `status='published' AND pdf_file IS NULL` → только при наличии PreorderRelease (проверка в `clean()`).

### ProductImage / ProductVideo
- `ProductImage`: product, image, alt, position, is_cover (частичный unique по product WHERE is_cover).
- `ProductVideo`: product, provider (vk / rutube / youtube; file — v2), url, position. MVP — embed по ссылке.

### Category, ComboItem
- `Category`: title, slug unique, position, is_visible. «Все мастер-классы» — виртуальная (без записи).
- `ComboItem`: combo → Product, item → Product, unique (combo, item), CHECK combo ≠ item. Если у комбо нет своего PDF — выдаются PDF входящих товаров.

### PreorderRelease
product (1:1), sales_start, sales_end, release_date (показывается на карточке), discount_percent, status (`scheduled → selling → closed → released | failed`), released_at.

### DiscountCampaign
title, percent (1–90), starts_at, ends_at (CHECK ends > starts), is_active, exclude_preorders (bool), applies_to (all; categories — v2). Пересечение активных кампаний запрещено (валидация + опционально exclusion constraint по `tstzrange`).

### Order
| Поле | Примечание |
|---|---|
| id UUID PK | не перебирается в URL |
| number unique | `K-2026-000123` для писем и поддержки |
| email (citext, индекс) | |
| status | см. §4 |
| subtotal, discount_total, total | снимок на момент создания |
| consent_offer_at, consent_pdn_at | обязательны |
| marketing_consent | bool, default **false** |
| ip, user_agent, created_at, paid_at | |

### OrderItem
order, product (PROTECT), **снимок**: title, unit_price, price_source (base / campaign / preorder), campaign_id. unique (order, product) — цифровой товар, количество всегда 1.

### Payment
order, provider, provider_payment_id **unique**, idempotence_key unique, amount, status, receipt_status, raw_payload (jsonb), timestamps.

### DownloadLink
order_item, token_hash unique (храним хеш, токен только в письме), expires_at, max_downloads, download_count, revoked, last_ip.

### EmailLog
order (null), to, template, status (queued / sent / failed / bounced), provider_message_id, attempts, error, **dedup_key unique** (`receipt:{order}`, `release:{preorder}:{item}`) — защита от двойной отправки.

### SiteSettings (singleton), Page
- `SiteSettings`: instagram_url, vk_url, telegram_url (опц.), support_url, support_email, реквизиты, текст баннера акции.
- `Page`: slug (about / offer / privacy / pdn-consent / marketing-consent), title, body, image, is_published.

## 3. Логика цены

Одна функция `catalog/pricing.py::get_price(product, now) -> PriceInfo(final, old, source, badge)`.

Правила (приоритет):
1. Предзаказ в окне продаж → `base × (1 − preorder%)`.
2. Активная кампания (и товар не исключён) → `base × (1 − campaign%)`.
3. Если применимы оба — **берётся большая скидка, скидки не суммируются** (подтвердить: вопрос 14).
4. Иначе `base`; если задан `compare_price > base` — показываем как старую цену.
5. Округление — до целого рубля вниз (`floor`, затем ×100).

| base | кампания | предзаказ | итог | old | бейдж |
|---|---|---|---|---|---|
| 600 ₽ | — | — | 600 | — | — |
| 600 ₽ | 30% | — | 420 | 600 | −30% |
| 600 ₽ | — | 20% | 480 | 600 | Предзаказ |
| 600 ₽ | 30% | 20% | 420 | 600 | Предзаказ, −30% |
| 590 ₽ | 30% | — | 413 | 590 | −30% |

«Старая цена» не хранится, а **вычисляется** (= base). Так нет рассинхрона после окончания акции.

Защита от рассинхрона корзина ↔ оплата:
- В корзине (сессия) храним только `product_id`. Цены пересчитываются при каждом показе.
- При «Оплатить» цены фиксируются в `OrderItem` (снимок), `Order.total` → сумма в платёжку.
- Если цена изменилась с момента показа корзины — показываем «Цена обновилась», требуем подтверждения.
- Неоплаченный заказ истекает через 60 мин (`expired`); повторная попытка создаёт новый Payment по актуальному снимку.

## 4. Платежи

| | ЮKassa | T-Bank (эквайринг) | Prodamus | CloudPayments |
|---|---|---|---|---|
| Самозанятые | да [проверить] | [проверить] | да, популярен у авторов курсов [проверить] | [проверить] |
| Чеки 54-ФЗ | свой сервис чеков / интеграция с «Мой налог» для СЗ [проверить] | онлайн-касса T-Bank [проверить] | автоматически, вкл. СЗ [проверить] | CloudKassir [проверить] |
| Webhooks | HTTP-уведомления; проверка через запрос статуса по API / IP [проверить] | notification с Token-подписью | подпись (Sign) [проверить] | HMAC-подпись |
| Идемпотентность | заголовок Idempotence-Key | OrderId | [проверить] | InvoiceId |
| Комиссия | [проверить] | [проверить] | [проверить] | [проверить] |
| API / доки | хорошие, Python SDK | хорошие | проще, больше «платёжная страница» | хорошие |

**Предварительный выбор:** СЗ → Prodamus или ЮKassa; ИП → ЮKassa или T-Bank. Решение — после вопроса 1 (`adr/0002-payments.md`).
Код делаем через интерфейс `PaymentProvider` (create_payment, parse_webhook, verify, refund), чтобы смена провайдера ≈ один адаптер.

### State machine заказа
```
created ──pay──▶ pending ──webhook succeeded──▶ paid ──files sent──▶ fulfilled
   │                │                              │
   │                ├─webhook canceled──▶ canceled  ├─(preorder)──▶ awaiting_release ──release──▶ fulfilled
   │                └─timeout 60m──▶ expired        └─refund──▶ refunded
```
- Переходы — только через `orders/services.py::transition(order, event)`, недопустимые → исключение.
- Webhook: проверить подпись/IP → найти Payment по `provider_payment_id` → `select_for_update` → если статус уже финальный, вернуть 200 без действий → иначе переход + постановка задачи на выдачу.
- Сумму в webhook сверяем с `Order.total`; при несовпадении → `needs_review` и алерт.
- Служебный статус `needs_review` (вне основного потока) — ручной разбор в админке.

## 5. Выдача файлов
- PDF лежат в **приватном** бакете S3 (Selectel / Yandex Object Storage / VK Cloud — [проверить цены]); публичного доступа нет.
- Письмо содержит ссылку на наш сайт `/d/<token>/`, **не** на S3 и **не** вложение (тяжёлые вложения режутся почтовиками; ссылка позволяет считать скачивания).
- `/d/<token>/` → проверка: токен существует, не отозван, `expires_at` > now, `download_count < max_downloads` → атомарный инкремент (`F()`) → 302 на presigned URL S3 с TTL 5 мин.
- По умолчанию: 30 дней, 5 скачиваний (вопрос 17).
- Защита от шаринга: лимиты + **водяной знак** «Куплено: email, заказ №» на страницах (pikepdf/pypdf, генерация в Celery при оплате, кэш в приватном бакете) — опция, вопрос 18.
- Повторная отправка: кнопка в админке заказа (новая ссылка, старая отзывается) + форма «Не пришло письмо?» (rate limit, отправка только на email заказа).
- «Мои покупки» (v2): magic-link на email → список заказов этого email, сессия 24 ч, без пароля.

## 6. Email
- Провайдер: российский транзакционный сервис (Unisender Go / SendPulse / Mailganer и т.п.) — [проверить цены и лимиты].
- Домен отправки: `mail.<домен>`; SPF, DKIM, DMARC (`p=none` → через месяц `quarantine`).
- Шаблоны (HTML + текст): `order_paid`, `preorder_paid` (с датой релиза), `preorder_released`, `resend_links`, `magic_link` (v2).
- Очередь: Celery + Redis, `autoretry_for`, экспоненциальный backoff, до 5 попыток; запись в EmailLog с `dedup_key`.
- Webhook провайдера о bounce/complaint → статус в EmailLog, видно в админке заказа.
- Dev: Mailpit в compose — все письма видны локально.

## 7. Предзаказ
1. Автор создаёт товар без PDF + PreorderRelease (окно продаж, дата релиза, скидка) → `scheduled`.
2. celery-beat каждые 5 мин: наступил `sales_start` → `selling` (бейдж «Предзаказ», «Файл придёт DD.MM»).
3. Прошёл `sales_end` → `closed` (товар скрыт или продаётся по обычной цене — настройка).
4. Покупатель получает письмо «Спасибо, файл придёт DD.MM»; заказ → `awaiting_release`.
5. Автор загружает PDF и жмёт «Выпустить» (или авто в `release_date`, если PDF загружен) → задача `release_preorder`: на каждый OrderItem создаётся DownloadLink и письмо с `dedup_key=release:{preorder}:{item}`; батчи по 50, повторный запуск безопасен.
6. В админке: отправлено N / ошибок M, кнопка «Повторить для ошибок». Нет PDF к `release_date` → алерт автору.

## 8. Юридическое и ПДн (152-ФЗ)
- Страницы: оферта, политика обработки ПДн, согласие на обработку ПДн, согласие на рассылку, реквизиты в футере.
- Чекаут: обязательное согласие с офертой и на обработку ПДн (форма отдельного согласия — [проверить актуальные требования]); **отдельный непредзаполненный** чекбокс на рассылку. Храним время согласия и версию документа.
- Отписка одним кликом в каждом маркетинговом письме.
- Локализация: БД с ПДн граждан РФ — на серверах в РФ (ч. 5 ст. 18 152-ФЗ). Уведомление Роскомнадзора об обработке ПДн — [проверить применимость].
- Минимизация: только email (+ IP для антифрода).

## 9. Безопасность
- CSRF на всех формах; HTMX передаёт токен через `hx-headers`.
- Rate limiting (django-ratelimit + Redis): чекаут, «не пришло письмо», скачивание, вход в админку.
- Webhooks: подпись / IP-allowlist + перепроверка статуса через API провайдера; только POST.
- Админка: нестандартный URL, 2FA (django-otp), HTTPS + HSTS, `SECURE_*` настройки.
- Секреты: `.env` на сервере (chmod 600), `.env.example` в репозитории.
- Бэкапы: ежедневный `pg_dump` → отдельный бакет, хранение 14 дневных + 8 недельных; ежемесячная проверка восстановления; versioning PDF-бакета.
- Логи: JSON в stdout, Sentry/GlitchTip для ошибок.


## 10. Производительность
- Изображения: webp + jpeg fallback, `srcset` (360/720/1080), `loading="lazy"`, явные width/height (без CLS).
- CDN перед публичным бакетом фото.
- Кэш: фрагменты каталога в Redis, инвалидация по сохранению Product/Campaign; цены не кэшируем дольше 1 мин (акции по времени).
- Статика: WhiteNoise + `ManifestStaticFilesStorage`; Tailwind purge → ~15–30 КБ CSS.
- Цель: LCP < 2,5 с на 4G, Lighthouse mobile ≥ 90.

## 11. SEO
- ЧПУ: `/catalog/`, `/catalog/combo/`, `/p/<slug>/`, `/about/`.
- `<title>`, meta description, canonical, Open Graph (og:image 1200×630).
- `sitemap.xml`, `robots.txt`, schema.org `Product` + `Offer` (price, RUB, availability InStock / PreOrder).
- Яндекс.Вебмастер + Яндекс.Метрика (cookie-уведомление — [проверить требования]).

## 12. Инфраструктура
- Docker Compose: `web` (gunicorn), `worker` (celery), `beat`, `db` (postgres 16), `redis`, `caddy` (TLS Let's Encrypt), dev: `mailpit`.
- Окружения: `dev` (compose.override), `prod` (тот же compose, prod env). Staging — по желанию на том же VPS.
- Деплой: CI (GitHub/GitLab Actions): ruff + pytest → build образа → ssh `docker compose pull && up -d` → `migrate`. На старте допустим `make deploy`.
- Мониторинг: внешний uptime-чек, Sentry, алерты в Telegram.

| Статья | Оценка, ₽/мес [проверить] |
|---|---|
| VPS 2 vCPU / 4 ГБ / 40 ГБ (РФ) | 600–1200 |
| S3 (≈5–20 ГБ) + CDN | 50–300 |
| Email (≈1–3 тыс. писем) | 0–500 |
| Домен | ~100 (в пересчёте) |
| **Итого** | **≈ 800–2100** |

## 13. Риски
| Риск | Влияние | Мера |
|---|---|---|
| Долгое подключение платёжки / выбор СЗ-ИП | блок этапа 4 | начать сразу; адаптер `PaymentProvider` |
| Письма в спам | покупатель без файла | SPF/DKIM/DMARC, «Не пришло письмо?» |
| Контент 80+ товаров не готов | срыв запуска | CSV-шаблон в первую неделю |
| Шаринг PDF | потеря выручки | водяной знак, лимиты |
| Ошибки цены в акциях | финансовые потери | одна функция цены + тесты по таблице §3 |
| Сложность админки для автора | постоянные обращения | тема, подсказки, видео-инструкция |
| Юр.требования (152-ФЗ, Instagram) | штрафы, блокировки | тексты от юриста, [проверить] |

Открытые вопросы — `docs/client-questions.md`.

