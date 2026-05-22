import asyncio
import json
import uuid
import logging
import nats
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Hotel Booking API")

# ── Модели запросов/ответов ────────────────────────────────

class SearchRequest(BaseModel):
    city: str
    check_in: str
    check_out: str
    guests: int
    room_type: Optional[str] = ""
    max_price: Optional[float] = 0

class RoomOffer(BaseModel):
    room_id: str
    hotel_name: str
    room_type: str
    capacity: int
    price_per_night: float
    total_price: float
    available: bool

class SearchResponse(BaseModel):
    task_id: str
    success: bool
    rooms: list[RoomOffer] = []
    count: int = 0
    error: Optional[str] = None

# ── Оркестратор ────────────────────────────────────────────

class HotelOrchestrator:
    def __init__(self):
        self.nc = None
        self.pending: Dict[str, asyncio.Future] = {}
        self.logger = logging.getLogger("api")

    async def connect(self):
        self.nc = await nats.connect("nats://localhost:4222")
        await self.nc.subscribe("hotel.search.result", cb=self._on_result)
        await self.nc.subscribe("hotel.search.error",  cb=self._on_result)
        self.logger.info("Подключён к NATS")

    async def disconnect(self):
        await self.nc.close()

    async def _on_result(self, msg):
        data = json.loads(msg.data.decode())
        task_id = data.get("task_id")
        if task_id in self.pending:
            self.pending[task_id].set_result(data)
            del self.pending[task_id]

    async def search_rooms(self, req: SearchRequest, timeout: int = 10) -> dict:
        task_id = str(uuid.uuid4())

        task = {
            "task_id": task_id,
            "city": req.city,
            "check_in": req.check_in,
            "check_out": req.check_out,
            "guests": req.guests,
            "room_type": req.room_type,
            "max_price": req.max_price
        }

        future = asyncio.get_event_loop().create_future()
        self.pending[task_id] = future

        await self.nc.publish("hotel.search.request", json.dumps(task).encode())
        self.logger.info(f"Задача отправлена {task_id}: поиск в {req.city}")

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            del self.pending[task_id]
            raise HTTPException(status_code=504, detail="Агент не ответил вовремя")


orchestrator = HotelOrchestrator()

# ── События FastAPI ────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    await orchestrator.connect()

@app.on_event("shutdown")
async def shutdown():
    await orchestrator.disconnect()

# ── Эндпоинты ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    result = await orchestrator.search_rooms(req)
    return SearchResponse(
        task_id=result["task_id"],
        success=result["success"],
        rooms=result.get("rooms", []),
        count=result.get("count", 0),
        error=result.get("error")
    )