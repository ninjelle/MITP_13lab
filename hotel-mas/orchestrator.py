import asyncio
import json
import uuid
import nats
from typing import Dict

class HotelOrchestrator:
    def __init__(self):
        self.nc = None
        self.pending: Dict[str, asyncio.Future] = {}

    async def connect(self):
        self.nc = await nats.connect("nats://localhost:4222")
        await self.nc.subscribe("hotel.search.result", cb=self._on_result)
        await self.nc.subscribe("hotel.search.error", cb=self._on_result)
        print("[Оркестратор] Подключён к NATS")

    async def disconnect(self):
        await self.nc.close()
        print("[Оркестратор] Отключён")

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
        print(f"[Оркестратор] Отправлена задача {task_id}: поиск в {city}")

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            del self.pending[task_id]
            raise TimeoutError(f"Агент не ответил за {timeout} сек")


async def main():
    orchestrator = HotelOrchestrator()
    await orchestrator.connect()

    print("\n=== Сценарий 1: Поиск номеров в Москве ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-01",
            check_out="2025-09-05",
            guests=2
        )
        print(f"Найдено номеров: {result['count']}")
        for room in result['rooms']:
            print(f"  {room['hotel_name']} | {room['room_type']} | {room['price_per_night']}₽/ночь | итого {room['total_price']}₽")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 2: Поиск с фильтром по цене ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-01",
            check_out="2025-09-03",
            guests=1,
            max_price=3000
        )
        print(f"Найдено номеров: {result['count']}")
        for room in result['rooms']:
            print(f"  {room['hotel_name']} | {room['room_type']} | {room['price_per_night']}₽/ночь")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 3: Невалидный запрос ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-10",
            check_out="2025-09-05",
            guests=1
        )
        print(f"Статус: {result['success']}, Ошибка: {result.get('error')}")
    except TimeoutError as e:
        print(f"Ошибка: {e}")

    print("\n=== Сценарий 4: Таймаут (несуществующий агент) ===")
    try:
        result = await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-01",
            check_out="2025-09-05",
            guests=1,
            timeout=2
        )
    except TimeoutError as e:
        print(f"Таймаут сработал: {e}")

    await orchestrator.disconnect()

asyncio.run(main())