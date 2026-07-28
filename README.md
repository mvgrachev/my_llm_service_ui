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

## Примеры API-запросов через curl

Отправка запроса к роуту `/chat`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"dish": "Борщ","people":2,use_steps:true}'
```

Ожидаемый ответ:

```json
{
  "products": ["Мясо","Картофель"],
  "steps": ["Почистить картофель","Сварить бульон"]
}
```

Повторный запрос с тем же сообщением будет обработан из кеша Redis без повторного вызова LLM.