# СНД «АТЛАС»
## Автоматизированная Траектория Локализации Академических Сведений

Централизованная система управления научной деятельностью.

---

## Стек технологий

| Слой       | Технология              |
|------------|-------------------------|
| Frontend   | Vue 3 + Vite            |
| Backend    | FastAPI (Python 3.12)   |
| База данных| PostgreSQL 16           |
| Хранилище  | Локальный сервер (gzip) |
| Контейнеры | Docker + Docker Compose |

---

## Быстрый старт

### 1. Клонировать / распаковать проект

```bash
cd atlas/
```

### 2. Создать файл переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env — смените пароли и SECRET_KEY
```

### 3. Запустить систему

```bash
docker compose up --build -d
```

### 4. Открыть в браузере

| Сервис         | URL                      |
|----------------|--------------------------|
| Веб-интерфейс  | http://localhost          |
| API Swagger UI | http://localhost:8000/docs|
| API ReDoc      | http://localhost:8000/redoc|
| PgAdmin        | http://localhost:5050 (с флагом --profile tools) |

---

## Запуск с PgAdmin (опционально)

```bash
docker compose --profile tools up -d
```

---

## Разработка (без Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
# Создайте БД PostgreSQL и настройте DATABASE_URL в .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

---

## Структура проекта

```
atlas/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── migrations/
│   │   └── init.sql           # Схема БД (выполняется при старте)
│   └── app/
│       ├── main.py
│       ├── core/config.py
│       ├── db/
│       │   ├── base.py
│       │   └── session.py
│       ├── models/models.py   # Все SQLAlchemy модели
│       ├── schemas/schemas.py # Pydantic схемы
│       ├── services/
│       │   └── file_service.py  # Сжатие / распаковка файлов
│       └── api/v1/endpoints/
│           ├── articles.py
│           ├── proposals.py
│           ├── software.py
│           ├── collections.py
│           ├── authors.py
│           ├── conferences.py
│           ├── documents.py
│           ├── templates.py
│           └── reports.py
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue            # Layout с сайдбаром
        ├── router/
        ├── assets/main.css    # Design system
        ├── utils/api.js       # Axios + все API методы
        ├── components/common/
        │   ├── FileUpload.vue   # Drag&drop + просмотр сжатия
        │   ├── AuthorPicker.vue # Поиск + создание авторов
        │   ├── FileTree.vue     # Дерево файлов ZIP
        │   └── TreeNode.vue
        └── views/
            ├── DashboardView.vue
            ├── ArticlesView.vue    # + Заключения
            ├── ProposalsView.vue
            ├── SoftwareView.vue    # + 7 документов + ZIP viewer
            ├── CollectionsView.vue
            ├── AuthorsView.vue     # + Оценочная ведомость
            ├── ConferencesView.vue # + Фильтр по датам
            ├── ReportsView.vue     # + План публикаций
            └── TemplatesView.vue
```

---

## Сжатие файлов

Система автоматически сжимает загружаемые файлы:

- **PDF, DOCX, TXT, XML** → gzip (уровень 6)
- **ZIP** → gzip-обёртка поверх архива
- **Изображения** → хранятся без сжатия (уже оптимизированы)

При скачивании сервер автоматически распаковывает файл.  
Степень сжатия отображается в интерфейсе (например, `-42%`).

---

## Управление

```bash
# Остановить
docker compose down

# Остановить и удалить данные (ОСТОРОЖНО)
docker compose down -v

# Просмотр логов
docker compose logs -f backend
docker compose logs -f frontend

# Перезапустить один сервис
docker compose restart backend
```

---

## Модули системы

| Модуль               | Функциональность                                          |
|----------------------|-----------------------------------------------------------|
| Научные статьи       | Загрузка, авторы, сборники, заключения, скачивание        |
| Рац. предложения     | Загрузка, типы, авторы, каталоги                          |
| ПО                   | ZIP-архивы, просмотр структуры, 7 комплектных документов  |
| Авторы               | Справочник + оценочная ведомость (рейтинг)                |
| Сборники             | Карточки с датами, статусом, фото                         |
| Конференции          | Календарь, фильтр по датам                                |
| Отчётность           | План публикаций + список сборников                        |
| Шаблоны              | DOCX-шаблоны для заключений и документов ПО               |
