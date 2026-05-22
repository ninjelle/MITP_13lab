#!/bin/bash
# Ручное тестирование SearchAgent через nats CLI
# Требует: nats CLI (https://github.com/nats-io/natscli)
# Установка: brew install nats-io/nats-tools/nats

NATS_URL="nats://localhost:4222"

echo "=== Тест 1: Успешный поиск в Москве ==="
nats pub hotel.search.request '{
  "task_id": "task-001",
  "city": "moscow",
  "check_in": "2025-09-01",
  "check_out": "2025-09-05",
  "guests": 2
}' --server $NATS_URL

sleep 1

echo ""
echo "=== Тест 2: Поиск с фильтром по цене ==="
nats pub hotel.search.request '{
  "task_id": "task-002",
  "city": "moscow",
  "check_in": "2025-09-01",
  "check_out": "2025-09-03",
  "guests": 1,
  "max_price": 3000
}' --server $NATS_URL

sleep 1

echo ""
echo "=== Тест 3: Невалидный запрос (check_out < check_in) ==="
nats pub hotel.search.request '{
  "task_id": "task-003",
  "city": "moscow",
  "check_in": "2025-09-10",
  "check_out": "2025-09-05",
  "guests": 1
}' --server $NATS_URL

echo ""
echo "Для просмотра результатов подпишитесь на топики:"
echo "  nats sub hotel.search.result --server $NATS_URL"
echo "  nats sub hotel.search.error  --server $NATS_URL"
