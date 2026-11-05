# Brifly — менеджер проектов и задач

Django-приложение: проекты, Kanban-доска с drag-and-drop, приоритеты и дедлайны,
вложения к задачам, фильтры, экспорт/импорт JSON, аналитика, светлая и тёмная темы.

## Запуск за одну команду

| Система | Команда |
|---|---|
| Windows | дважды щёлкнуть `start.bat` |
| macOS / Linux | `./start.sh` |

Скрипт сам создаст виртуальное окружение, установит Django, применит миграции,
создаст демо-данные и запустит сервер на http://127.0.0.1:8000.
**Демо-вход:** `demo` / `demo12345` (или зарегистрируйте своего пользователя).

Интернет не нужен: Bootstrap, SortableJS и шрифт Manrope лежат в `static/vendor/`.

## Запуск вручную

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate           # создаёт БД и справочники статусов/приоритетов
python manage.py seed_demo         # (необязательно) демо-пользователь и задачи
python manage.py createsuperuser   # (необязательно) доступ в /admin/
python manage.py runserver
```

## Тесты

```bash
python manage.py test
```

35 тестов: авторизация, CRUD проектов и задач, AJAX, вложения, фильтры,
экспорт/импорт, изоляция данных между пользователями, CSRF.

## Структура

```
config/                  настройки, корневые urls
tasks/
  models.py              TaskStatus, Priority, Project, Task, TaskAttachment, Comment
  views.py               CBV для CRUD + AJAX-эндпоинты для канбана
  forms.py, urls.py, admin.py, tests.py
  migrations/0002_*.py   заполняет справочники (Новая / В работе / Готова; Низкий / Средний / Высокий)
  management/commands/seed_demo.py
  templates/tasks/       страницы приложения, partials/task_cards.html — карточки доски
templates/               base.html, registration/login.html, register.html
static/vendor/           Bootstrap 5.3, SortableJS 1.15, Manrope (локально)
docs/presentation.html   презентация проекта (стрелки / пробел — слайды, F — полный экран)
```

## Настройки для продакшена

Через переменные окружения: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS=example.com`. При `DEBUG=0` нужно отдавать `/media/` и
`/static/` веб-сервером (`python manage.py collectstatic`).
