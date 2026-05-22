import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from api import app, orchestrator


# ── Фикстуры ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_orchestrator_nc():
    orchestrator.nc = AsyncMock()


# ── Тест health ───────────────────────────────────────────

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ── Тест успешного поиска ─────────────────────────────────

@pytest.mark.asyncio
async def test_search_success():
    fake_result = {
        "task_id": "test-001",
        "success": True,
        "rooms": [
            {
                "room_id": "room-102",
                "hotel_name": "Grand Hotel",
                "room_type": "double",
                "capacity": 2,
                "price_per_night": 5500.0,
                "total_price": 22000.0,
                "available": True
            }
        ],
        "count": 1
    }

    async def fake_publish(topic, data):
        import json
        task = json.loads(data.decode())
        task_id = task["task_id"]
        if task_id in orchestrator.pending:
            orchestrator.pending[task_id].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={
            "city": "moscow",
            "check_in": "2025-09-01",
            "check_out": "2025-09-05",
            "guests": 2
        })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 1
    assert data["rooms"][0]["room_type"] == "double"


# ── Тест ошибки валидации от агента ──────────────────────

@pytest.mark.asyncio
async def test_search_agent_error():
    fake_result = {
        "task_id": "test-002",
        "success": False,
        "error": "check_out должен быть позже check_in"
    }

    async def fake_publish(topic, data):
        import json
        task = json.loads(data.decode())
        task_id = task["task_id"]
        if task_id in orchestrator.pending:
            orchestrator.pending[task_id].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={
            "city": "moscow",
            "check_in": "2025-09-10",
            "check_out": "2025-09-05",
            "guests": 1
        })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "check_out" in data["error"]


# ── Тест таймаута ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_timeout():
    from fastapi import HTTPException

    with patch.object(orchestrator, "search_rooms", side_effect=HTTPException(status_code=504, detail="Таймаут")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/search", json={
                "city": "moscow",
                "check_in": "2025-09-01",
                "check_out": "2025-09-05",
                "guests": 1
            })

    assert response.status_code == 504


# ── Тест невалидного тела запроса ─────────────────────────

@pytest.mark.asyncio
async def test_search_invalid_body():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={
            "city": "moscow"
            # нет обязательных полей
        })

    assert response.status_code == 422