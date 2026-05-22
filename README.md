# Лабораторная работа №13

**Студент:** Зверева Екатерина Константиновна  
**Группа:** 220032-11  
**Вариант:** 6  
**Сложность:** средняя

## Содержание репозитория

```
МИТП_лр13/
├── hotel-mas/
│   ├── search-agent/
│   │   ├── main.go              # SearchAgent — агент поиска номеров (Go)
│   │   ├── main_test.go         # Юнит-тесты агента (Go)
│   │   ├── Dockerfile           # Образ для сборки агента
│   │   ├── go.mod               # Go-модуль
│   │   └── go.sum               # Хэши зависимостей
│   ├── orchestrator.py          # Оркестратор задач (Python, asyncio)
│   ├── api.py                   # REST API (FastAPI)
│   ├── test_orchestrator.py     # Тесты оркестратора (pytest + моки)
│   ├── test_api.py              # Тесты REST API (pytest)
│   ├── test.py                  # Ручное тестирование через NATS
│   ├── docker-compose.yml       # NATS + 3 экземпляра SearchAgent
│   ├── pytest.ini               # Настройки pytest
│   └── requirements.txt         # Python-зависимости
├── ARCHITECTURE.md              # Диаграммы и описание архитектуры
├── PROMPT_LOG.md                # История промптов ИИ
├── README.md                    # Этот файл
└── .gitignore
```

## Предметная область: Бронирование гостиниц

Реализована мультиагентная система (MAS) для поиска и бронирования гостиничных номеров.

### Агенты системы

| Агент | Язык | Роль |
|---|---|---|
| SearchAgent | Go | Поиск свободных номеров по параметрам |
| BookingAgent | — | Создание брони (описан в задании 1) |
| PaymentAgent | — | Обработка оплаты (описан в задании 1) |
| CancellationAgent | — | Управление отменами (описан в задании 1) |

### Реализованный функционал

- Поиск номеров по городу, датам, количеству гостей, типу и цене
- Валидация входных данных по бизнес-правилам
- Проверка доступности номеров (алгоритм пересечения интервалов)
- Балансировка нагрузки между 3 экземплярами агента (NATS queue groups)
- Retry-механизм в оркестраторе (до 3 попыток с задержкой)
- REST API для внешних клиентов
- Структурированное логирование в файл и консоль
- Метрики обработанных задач

---

## Запуск системы

### 1. Запустить NATS и агентов через Docker

```bash
docker-compose up --build
```

Поднимает: NATS-брокер + 3 экземпляра SearchAgent.

### 2. Запустить REST API

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

### 3. Проверить работу

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d "{\"city\":\"moscow\",\"check_in\":\"2025-09-01\",\"check_out\":\"2025-09-05\",\"guests\":2}"
```

Или открыть интерактивную документацию API:

```
http://localhost:8000/docs
```

### 4. Мониторинг NATS

```
http://localhost:8222
http://localhost:8222/subscriptions
```

---

## Тестирование

### Go (юнит-тесты агента)

```bash
cd search-agent
go test ./... -v
```

### Python (тесты оркестратора и API)

```bash
pytest test_orchestrator.py test_api.py -v
```

---

## Топики NATS

| Топик | Направление | Описание |
|---|---|---|
| `hotel.search.request` | Оркестратор → Агент | Запрос на поиск номеров |
| `hotel.search.result` | Агент → Оркестратор | Успешный результат поиска |
| `hotel.search.error` | Агент → Оркестратор | Ошибка валидации |

---

## Бизнес-правила SearchAgent

- `check_out` должен быть позже `check_in`
- Минимальный срок — 1 ночь
- Максимум — 365 дней вперёд
- `capacity >= guests`
- Номер недоступен при пересечении с существующей бронью

---

## Используемые технологии

| Компонент | Технология |
|---|---|
| Агент | Go 1.23, nats.go |
| Оркестратор | Python 3.11, asyncio, nats-py |
| REST API | FastAPI, uvicorn |
| Брокер сообщений | NATS 2.10 |
| Контейнеризация | Docker, Docker Compose |
| Тестирование (Go) | testing (stdlib) |
| Тестирование (Python) | pytest, pytest-asyncio, httpx |
