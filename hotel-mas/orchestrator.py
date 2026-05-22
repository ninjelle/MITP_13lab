import asyncio
import json
import uuid
import logging
import nats
from typing import Dict
from datetime import datetime

# ── Настройка логгера ──────────────────────────────────────
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(levelname)-5s %(asctime)s [Оркестратор] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # В консоль
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # В файл
    file_handler = logging.FileHandler("orchestrator.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


class HotelOrchestrator:
    def __init__(self):
        self.nc = None
        self.pending: Dict[str, asyncio.Future] = {}
        self.logger = setup_logger()

        # Счётчики метрик
        self.total_sent     = 0
        self.total_success  = 0
        self.total_errors   = 0
        self.total_timeouts = 0

    async def connect(self):
        self.nc = await nats.connect("nats://localhost:4222")
        await self.nc.subscribe("hotel.search.result", cb=self._on_result)
        await self.nc.subscribe("hotel.search.error",  cb=self._on_result)
        self.logger.info("Подключён к NATS")

    async def disconnect(self):
        await self.nc.close()
        self.logger.info(
            f"Отключён. Метрики: отправлено={self.total_sent}, "
            f"успешно={self.total_success}, ошибок={self.total_errors}, "
            f"таймаутов={self.total_timeouts}"
        )

    async def _on_result(self, msg):
        data = json.loads(msg.data.decode())
        task_id = data.get("task_id")
        if task_id in self.pending:
            self.pending[task_id].set_result(data)
            del self.pending[task_id]

    async def search_rooms(self, city: str, check_in: str, check_out: str,
                           guests: int, room_type: str = "", max_price: float = 0,
                           timeout: int = 10) -> dict:
        task_id = str(uuid.uuid4())
        self.total_sent += 1

        task = {
            "task_id": task_id,
            "city": city,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "room_type": room_type,
            "max_price": max_price
        }

        future = asyncio.get_event_loop().create_future()
        self.pending[task_id] = future

        await self.nc.publish("hotel.search.request", json.dumps(task).encode())
        self.logger.info(f"Задача отправлена {task_id}: поиск в {city} [{check_in} — {check_out}]")

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            if result.get("success"):
                self.total_success += 1
                self.logger.info(f"Задача {task_id} выполнена: найдено {result['count']} номеров")
            else:
                self.total_errors += 1
                self.logger.error(f"Задача {task_id} вернула ошибку: {result.get('error')}")
            return result
        except asyncio.TimeoutError:
            self.total_timeouts += 1
            del self.pending[task_id]
            self.logger.error(f"Задача {task_id} не выполнена за {timeout} сек (таймаут)")
            raise TimeoutError(f"Агент не ответил за {timeout} сек")


async def main():
    orchestrator = HotelOrchestrator()
    await orchestrator.connect()

    print("\n=== Сценарий 1: Поиск номеров в Москве ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow", check_in="2025-09-01", check_out="2025-09-05", guests=2
        )
        for room in result['rooms']:
            print(f"  {room['hotel_name']} | {room['room_type']} | {room['price_per_night']}₽/ночь | итого {room['total_price']}₽")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 2: Поиск с фильтром по цене ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow", check_in="2025-09-01", check_out="2025-09-03", guests=1, max_price=3000
        )
        for room in result['rooms']:
            print(f"  {room['hotel_name']} | {room['room_type']} | {room['price_per_night']}₽/ночь")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 3: Невалидный запрос ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow", check_in="2025-09-10", check_out="2025-09-05", guests=1
        )
        print(f"  Ошибка от агента: {result.get('error')}")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 4: Таймаут ===")
    try:
        await orchestrator.search_rooms(
            city="moscow", check_in="2025-09-01", check_out="2025-09-05", guests=1, timeout=2
        )
    except TimeoutError as e:
        print(f"  Таймаут сработал: {e}")

    await orchestrator.disconnect()

asyncio.run(main())