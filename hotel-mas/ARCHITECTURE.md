# Архитектура системы бронирования гостиниц

## Диаграмма взаимодействия компонентов

```mermaid
graph TD
    Client["HTTP Client\ncurl / browser"]
    API["FastAPI\napi.py\n:8000"]
    Orch["Orchestrator\norchestrator.py"]
    NATS["NATS Broker\n:4222"]
    A1["SearchAgent-1\nGo"]
    A2["SearchAgent-2\nGo"]
    A3["SearchAgent-3\nGo"]
    DB["In-Memory DB\nroomDatabase"]

    Client -->|"POST /search"| API
    API -->|"search_rooms()"| Orch
    Orch -->|"hotel.search.request"| NATS
    NATS -->|"queue group search-agents"| A1
    NATS -->|"queue group search-agents"| A2
    NATS -->|"queue group search-agents"| A3
    A1 -->|"hotel.search.result"| NATS
    A2 -->|"hotel.search.result"| NATS
    A3 -->|"hotel.search.result"| NATS
    NATS -->|"результат"| Orch
    Orch -->|"SearchResponse"| API
    API -->|"JSON"| Client
    A1 --- DB
    A2 --- DB
    A3 --- DB
```

## Диаграмма последовательности

```mermaid
sequenceDiagram
    participant C as HTTP Client
    participant A as FastAPI
    participant O as Orchestrator
    participant N as NATS
    participant G as SearchAgent

    C->>A: POST /search {city, dates, guests}
    A->>O: search_rooms(request)
    O->>N: publish hotel.search.request
    N->>G: доставка (queue group)
    G->>G: validateRequest()
    G->>G: searchRooms()
    G->>N: publish hotel.search.result
    N->>O: deliver result
    O->>A: return result
    A->>C: JSON response

    Note over O,N: При таймауте — retry до 3 раз
    Note over N,G: Балансировка между 3 агентами
```

## Описание компонентов

### 1. FastAPI (api.py)

- **Роль**: точка входа, REST API
- **Порт**: 8000
- **Эндпоинты**: GET /health, POST /search
- **Технологии**: Python, FastAPI, uvicorn

### 2. Orchestrator (orchestrator.py)

- **Роль**: управляет задачами, отправляет в NATS, ждёт результаты
- **Функции**: retry до 3 раз, таймаут, метрики
- **Технологии**: Python, asyncio, nats-py

### 3. NATS Broker

- **Роль**: брокер сообщений, маршрутизация между компонентами
- **Порты**: 4222 (клиенты), 8222 (мониторинг)
- **Топики**:
  - hotel.search.request — запросы от оркестратора
  - hotel.search.result — успешные результаты
  - hotel.search.error — ошибки валидации
- **Queue group**: search-agents — балансировка между агентами

### 4. SearchAgent (Go)

- **Роль**: обрабатывает поисковые запросы
- **Количество**: 3 экземпляра
- **Функции**: валидация, поиск по базе, проверка доступности по датам
- **Бизнес-правила**:
  - check_out > check_in
  - capacity >= guests
  - максимум 365 дней вперёд
  - алгоритм пересечения интервалов для броней

### 5. In-Memory Database

- **Роль**: хранит номера и существующие брони
- **Данные**: 6 номеров в 3 гостиницах (Москва, Сочи)

## Структура проекта

```
hotel-mas/
├── search-agent/
│   ├── main.go           # SearchAgent (Go)
│   ├── main_test.go      # юнит-тесты Go
│   ├── Dockerfile
│   ├── go.mod
│   └── go.sum
├── orchestrator.py       # оркестратор
├── api.py                # REST API
├── test_orchestrator.py  # тесты оркестратора
├── test_api.py           # тесты API
├── test.py               # ручное тестирование
├── docker-compose.yml    # NATS + 3 агента
├── pytest.ini
├── requirements.txt
└── .gitignore
```

## Паттерны взаимодействия

| Паттерн | Где используется |
|---------|-----------------|
| Pipeline | Client → API → Orchestrator → Agent |
| Queue Group | балансировка между 3 агентами |
| Request-Reply | оркестратор ждёт ответ через Future |
| Retry | повтор до 3 раз при таймауте |
