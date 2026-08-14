# LLM Service

API сервис для работы с LLM (Large Language Models).

## Требования

- Python 3.11+
- pip
- Docker (для запуска Redis)

## Установка Redis

```bash
# Запуск Redis через Docker
docker run -d --name redis-test -p 6379:6379 redis:7-alpine
```

Redis будет доступен по адресу `localhost:6379`.

Проверка работы Redis:

```bash
docker exec redis-test redis-cli ping
```

## Установка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
python3 main.py
```

## Структура проекта

```
my_llm_service/
├── api/          # API endpoints
├── services/     # Business logic
├── llm/          # LLM integration
├── cache/        # Cache management
├── config/       # Configuration
├── tests/        # Tests
├── main.py       # Entry point (backend)
├── app.py        # UI frontend
├── requirements.txt
└── README.md
```

## Использование

### Запуск FastAPI (backend)

```bash
# Запуск в фоне (production)
nohup .venv/bin/python main.py > main.log 2>&1 &

# Проверка работы
curl http://localhost:8000/health
```

Сервер будет доступен по адресу `http://localhost:8000`

### Запуск Streamlit UI (frontend)

```bash
# Установка Streamlit
pip install streamlit

# Запуск в фоне (production)
nohup .venv/bin/python -m streamlit run app.py --server.headless=true --server.port=8501 > streamlit.log 2>&1 &

# Проверка работы
curl http://localhost:8501
```

Веб-интерфейс будет доступен по адресу `http://localhost:8501`

> Streamlit UI обращается к FastAPI на `http://localhost:8000/chat`, поэтому сначала нужно запустить backend.

## Запуск через Docker Compose

Проект содержит `docker-compose.yml`, который поднимает три сервиса:

- **fastapi** — бэкенд (FastAPI) на порту `8000`
- **streamlit** — веб-интерфейс (Streamlit) на порту `8501`
- **redis** — кэш на порту `6379`

### Требования

- Docker
- Docker Compose (v2)

### Запуск

```bash
# Собрать образы и запустить все сервисы в фоне
docker compose up --build -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f
```

### Остановка

```bash
# Остановить и удалить контейнеры
docker compose down

# С удалением томов и образов
docker compose down -v
```

### Доступ

| Сервис | Адрес | Описание |
|--------|-------|----------|
| FastAPI | `http://localhost:8000` | API (Swagger: `http://localhost:8000/docs`) |
| Streamlit UI | `http://localhost:8501` | Веб-интерфейс |
| Redis | `localhost:6379` | Кэш |

## Примеры API-запросов через curl

Отправка запроса к роуту `/chat`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"dish": "Борщ","people":2,"use_steps":true}'
```

Ожидаемый ответ:

```json
{
  "products": ["Мясо","Картофель"],
  "steps": ["Почистить картофель","Сварить бульон"]
}
```

Повторный запрос с тем же сообщением будет обработан из кеша Redis без повторного вызова LLM.

### Примеры запросов

#### 1. Запрос с указанием шагов приготовления

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"dish": "Паста Карбонара", "people": 3, "use_steps": true}'
```

Ответ:

```json
{
  "products": [
    "Спагетти",
    "Бекон",
    "Яйца",
    "Пармезан",
    "Чёрный перец"
  ],
  "steps": [
    "Отварить спагетти до состояния аль денте","Обжарить бекон до хрустящей корочки",
    "Смешать яйца с тёртым пармезаном",
    "Соединить пасту с беконом и яичной смесью",
    "Посыпать чёрным перцем перед подачей"
  ]
}
```

#### 2. Запрос без шагов (только продукты)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"dish": "Цезарь с курицей", "people": 2, "use_steps": false}'
```

Ответ:

```json
{
  "products": [
    "Куриное филе",
    "Салат Романо",
    "Сухарики",
    "Пармезан",
    "Яйца",
    "Соус Цезарь"
  ],
  "steps": null
}
```

#### 3. Запрос по умолчанию (use_steps не указан)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
    -d '{"dish": "Салат Оливье", "people": 4}'
```

Ответ:

```json
{
  "products": [
    "Картофель",
    "Морковь",
    "Яйца",
    "Колбаса докторская",
    "Огурцы солёные",
    "Горошек",
    "Майонез"
  ],
  "steps": null
}
```

#### 4. Запрос на большую компанию

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
    -d '{"dish": "Пирог с яблоками", "people": 10, "use_steps": true}'
```

Ответ:

```json
{
  "products": [
    "Мука",
    "Сахар",
    "Сливочное масло",
    "Яйца",
    "Яблоки",
    "Корица",
    "Разрыхлитель"
  ],
  "steps": [
    "Подготовить форму для выпечки",
    "Смешать сухие ингредиенты",
    "Добавить яйца и сливочное масло",
    "Нарезать яблоки и посыпать корицей",
    "Выпекать при 180°C около 40 минут"
  ]
}
```

### Возможные ответы об ошибках

#### Ошибка валидации (пустое блюдо)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
    -d '{"dish": "", "people": 2}'
```

Ответ (422 Unprocessable Entity):

```json
{
  "detail": "Validation error"
}
```

#### Ошибка авторизации (неверный API-ключ)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
    -d '{"dish": "Борщ", "people": 2, "use_steps": true}'
```

Ответ (401 Unauthorized):

```json
{
  "detail": "Ошибка авторизации: недействительный или истёкший API-ключ. Пожалуйста, проверьте настройки."
}
```

#### Превышен лимит частоты обращений

Ответ (429 Too Many Requests):

```json
{
  "detail": "Превышена частота обращения к сервису. Пожалуйста, попробуйте позже."
}
```

#### Ошибка LLM

Ответ (502 Bad Gateway):

```json
{
  "detail": "Не удалось обработать ответ от LLM. Попробуйте позже."
}
```
