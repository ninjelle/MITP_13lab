import asyncio
import json
import nats

async def main():
    nc = await nats.connect("nats://localhost:4222")

    results = []
    async def handler(msg):
        data = json.loads(msg.data.decode())
        print("ОТВЕТ:", json.dumps(data, ensure_ascii=False, indent=2))

    await nc.subscribe("hotel.search.result", cb=handler)
    await nc.subscribe("hotel.search.error", cb=handler)

    # Тест 1: успешный поиск
    await nc.publish("hotel.search.request", json.dumps({
        "task_id": "task-001",
        "city": "moscow",
        "check_in": "2025-09-01",
        "check_out": "2025-09-05",
        "guests": 2
    }).encode())

    await asyncio.sleep(1)
    await nc.close()

asyncio.run(main())